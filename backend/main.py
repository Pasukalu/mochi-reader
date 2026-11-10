"""Run: python -m uvicorn backend.app:app --host 127.0.0.1 --port 8765."""

import asyncio
import json
import re
import time
from contextlib import aclosing

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .config import ROOT, Settings, settings_from_env
from .provider import DeepSeek, ProviderError
from .retrieval import retrieve, tokenize
from .schemas import ChatInput, DocumentInput, StudyInput, StudyOutput
from .storage import Store


def public_source(source: dict) -> dict:
    return {key: source[key] for key in ("id", "title", "url", "text")} | {"score": source.get("score", 0)}


def event(name: str, data: dict) -> str:
    return f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def overview_sources(chunks: list[dict], limit: int) -> list[dict]:
    """Prefer substantive paragraphs over isolated headings, preserving IDs."""
    paragraphs = [source for source in chunks if len(source["text"]) >= 40]
    return (paragraphs or chunks)[:limit]


def demo_study(sources: list[dict]) -> StudyOutput:
    """Extractive exercises are generated from actual paragraphs, never faux LLMs."""
    cards, quiz = [], []
    all_terms = list(dict.fromkeys(
        term for source in sources for term in tokenize(source["text"])
        if 2 <= len(term) <= 50
    ))
    for source in sources[:3]:
        text = source["text"]
        cards.append({"title": "原文摘录 · " + source["id"], "body": text, "source_id": source["id"]})
        prompt = text[:180]
        candidates = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,49}|[\u3400-\u9fff]{2,6}", prompt)
        term = next((word for word in candidates if len(word) >= 3), candidates[0] if candidates else prompt[:2])
        options = [term]
        for alternative in all_terms + ["文中未说明", "无法从原文判断", "以上均不符合"]:
            if alternative.lower() != term.lower() and alternative not in options:
                options.append(alternative)
            if len(options) == 4:
                break
        position = (len(quiz) + 1) % 4
        options[0], options[position] = options[position], options[0]
        quiz.append({
            "question": "原文填空：" + prompt.replace(term, "____", 1),
            "options": options, "answer": position,
            "explanation": "原文摘录：" + prompt, "source_id": source["id"],
        })
    return StudyOutput.model_validate({"cards": cards, "quiz": quiz})


def create_app(settings: Settings | None = None, provider: DeepSeek | None = None) -> FastAPI:
    settings = settings or settings_from_env()
    store = Store(settings.database)
    provider = provider or DeepSeek(settings)
    app = FastAPI(title="Mochi Reader", version="0.1.0", description="Local-first lexical RAG with traceable paragraph citations")
    app.state.store = store
    app.state.settings = settings

    @app.exception_handler(RequestValidationError)
    async def input_validation_error(request: Request, exc: RequestValidationError):
        # Do not reflect arbitrary imported text (or malformed Unicode) into an
        # error response. Field locations and messages are sufficient to fix input.
        return JSONResponse(status_code=422, content={"detail": [
            {key: error[key] for key in ("loc", "msg", "type")}
            for error in exc.errors()
        ]})

    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "[::1]", "testserver"])
    extension_origin = r"chrome-extension://[a-p]{32}"
    app.add_middleware(
        CORSMiddleware, allow_origins=list(settings.cors_origins),
        allow_origin_regex=extension_origin,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type"], allow_credentials=False,
    )

    @app.middleware("http")
    async def local_boundary(request: Request, call_next):
        origin = request.headers.get("origin")
        if origin and origin not in settings.cors_origins and not re.fullmatch(extension_origin, origin):
            return JSONResponse({"detail": "This origin is not allowed to access Mochi."}, status_code=403)
        # Guard oversized input even before JSON/Pydantic parsing. JSON escaping can
        # expand 80k characters; the streamed body is bounded independently of headers.
        if request.url.path.startswith("/api/") and request.method == "POST":
            received = bytearray()
            async for block in request.stream():
                received.extend(block)
                if len(received) > 600000:
                    return JSONResponse({"detail": "Request body is too large."}, status_code=413)
            request._body = bytes(received)
        return await call_next(request)

    def get_doc(document_id: str):
        doc = store.get(document_id)
        if doc is None:
            raise HTTPException(404, "文章不存在，请重新导入。")
        return doc

    @app.get("/api/health")
    def health():
        return {"status": "ok", "mode": settings.mode, "model": settings.model if settings.mode == "live" else "extractive-demo"}

    @app.get("/api/documents")
    def documents():
        return {"documents": store.list()}

    @app.post("/api/documents", status_code=201)
    def add_document(body: DocumentInput):
        return store.create(body.title, body.url, body.text)

    @app.get("/api/documents/{document_id}")
    def document(document_id: str):
        return {**get_doc(document_id), "chunks": store.chunks(document_id)}

    @app.delete("/api/documents/{document_id}")
    def delete_document(document_id: str):
        if not store.delete(document_id):
            raise HTTPException(404, "文章不存在。")
        return {"deleted": True}

    @app.post("/api/chat")
    async def chat(body: ChatInput, request: Request):
        get_doc(body.document_id)
        chunks = store.chunks(body.document_id)
        found = retrieve(chunks, body.question)
        general_overview = re.search(
            r"(?:这篇|整篇|全文|本文|文章).{0,8}(?:重点|总结|摘要|概览|概括)|"
            r"(?:总结|摘要|概览|概括).{0,8}(?:文章|全文|这篇|本文)|"
            r"\b(?:summari[sz]e|summary|overview)\b", body.question, re.I
        )
        if general_overview or (not found and body.question in {"总结", "摘要", "重点", "概览", "概括"}):
            found = [{**s, "score": 0.0} for s in overview_sources(chunks, 4)]
        sources = [public_source(s) for s in found]

        async def generate():
            start = time.perf_counter()
            yield event("sources", {"sources": sources, "mode": settings.mode})
            answer = ""
            try:
                if not sources:
                    answer = "当前文章没有提供足够依据。请换一个与原文关键词相关的问题，或导入另一篇文章。"
                    yield event("token", {"text": answer})
                elif settings.mode == "demo":
                    greeting = {
                        "whale": "鲸鱼娘把相关原文捞上来啦～",
                        "mochi": "糯米帮你找到这些原文啦～",
                        "senpai": "以下是与问题最相关的原文段落。",
                    }[body.persona]
                    answer = greeting + "\n\n【离线摘录模式：未调用大模型，以下为检索结果，不是推理生成的答案。】\n\n"
                    answer += "\n\n".join(f"{s['text']} [{s['id']}]" for s in sources[:3])
                    for index in range(0, len(answer), 28):
                        if await request.is_disconnected():
                            return
                        yield event("token", {"text": answer[index:index + 28]})
                        await asyncio.sleep(0)
                else:
                    async with aclosing(provider.stream(body.question, sources, body.persona, body.history)) as stream:
                        async for token in stream:
                            if await request.is_disconnected():
                                return
                            answer += token
                            yield event("token", {"text": token})
                valid_ids = {s["id"] for s in sources}
                references = set(re.findall(r"\[(S\d+)\]", answer))
                invalid = references - valid_ids
                citations = sorted(references & valid_ids, key=lambda s: int(s[1:]))
                yield event("done", {
                    "citations": citations, "elapsed_ms": round((time.perf_counter() - start) * 1000),
                    "mode": settings.mode, "grounded": bool(citations) and not invalid,
                    "invalid_citations": sorted(invalid),
                })
            except ProviderError as exc:
                yield event("error", {"message": str(exc)})

        return StreamingResponse(generate(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @app.post("/api/study")
    async def study(body: StudyInput):
        get_doc(body.document_id)
        sources = [public_source(s) for s in overview_sources(store.chunks(body.document_id), 6)]
        if not sources:
            raise HTTPException(404, "文章已被删除，请重新导入。")
        try:
            output = demo_study(sources) if settings.mode == "demo" else await provider.study(sources, body.persona)
        except ProviderError as exc:
            raise HTTPException(502, str(exc)) from exc
        return {"mode": settings.mode, **output.model_dump(), "sources": sources}

    web = ROOT / "web"
    if web.exists():
        app.mount("/", StaticFiles(directory=web, html=True), name="web")
    return app


app = create_app()
