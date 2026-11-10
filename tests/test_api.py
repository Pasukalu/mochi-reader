import json

import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app
from backend.provider import ProviderError

ARTICLE = "BM25 根据词频与逆文档频率排列段落，是一种词法检索方法。\n\n向量检索通过嵌入表示语义，相似含义的文本在空间中距离较近。\n\nSQLite 将文章和段落存储在本地，删除文章会级联删除段落。"


@pytest.fixture
def client(tmp_path):
    settings = Settings(str(tmp_path / "test.sqlite3"), "", "https://api.deepseek.com", "deepseek-flash", ("http://127.0.0.1:8765",))
    with TestClient(create_app(settings)) as client:
        yield client


def add(client):
    response = client.post("/api/documents", json={"title": "检索笔记", "url": "https://example.com/note", "text": ARTICLE})
    assert response.status_code == 201
    return response.json()


def events(response):
    result = []
    for block in response.text.strip().split("\n\n"):
        name, data = block.split("\n", 1)
        result.append((name.removeprefix("event: "), json.loads(data.removeprefix("data: "))))
    return result


def test_health_and_persistence(client):
    assert client.get("/api/health").json()["mode"] == "demo"
    doc = add(client)
    assert doc["chunk_count"] == 3
    assert client.get("/api/documents").json()["documents"][0]["id"] == doc["id"]
    detail = client.get("/api/documents/" + doc["id"]).json()
    assert detail["chunks"][0]["id"] == "S1" and detail["chunks"][0]["text"] in ARTICLE
    assert client.delete("/api/documents/" + doc["id"]).status_code == 200
    assert client.app.state.store.chunks(doc["id"]) == []
    assert client.delete("/api/documents/" + doc["id"]).status_code == 404


def test_chat_has_grounded_extractive_answer(client):
    doc = add(client)
    response = client.post("/api/chat", json={"document_id": doc["id"], "question": "BM25 是什么？", "persona": "mochi"})
    assert response.status_code == 200
    stream = events(response)
    assert stream[0][0] == "sources" and stream[0][1]["sources"][0]["id"] == "S1"
    answer = "".join(data["text"] for name, data in stream if name == "token")
    assert "离线摘录模式" in answer and "[S1]" in answer
    assert stream[-1][0] == "done" and stream[-1][1]["grounded"] is True


def test_unknown_question_refuses_without_fabricated_citation(client):
    doc = add(client)
    stream = events(client.post("/api/chat", json={"document_id": doc["id"], "question": "天气预报温度"}))
    assert stream[0][1]["sources"] == []
    assert "没有提供足够依据" in stream[1][1]["text"]
    assert stream[-1][1]["citations"] == [] and not stream[-1][1]["grounded"]


def test_whale_persona_default_and_validation(client):
    doc = add(client)
    for extra in ({}, {"persona": "whale"}):
        stream = events(client.post("/api/chat", json={"document_id": doc["id"], "question": "BM25?", **extra}))
        answer = "".join(data["text"] for name, data in stream if name == "token")
        assert "鲸鱼娘把相关原文捞上来啦～" in answer
    assert client.post("/api/study", json={"document_id": doc["id"], "persona": "whale"}).status_code == 200
    for route, body in (("/api/chat", {"question": "BM25?"}), ("/api/study", {})):
        assert client.post(route, json={"document_id": doc["id"], "persona": "unknown", **body}).status_code == 422


def test_study_is_grounded_and_has_four_distinct_options(client):
    doc = add(client)
    data = client.post("/api/study", json={"document_id": doc["id"], "persona": "senpai"}).json()
    ids = {source["id"] for source in data["sources"]}
    assert data["mode"] == "demo" and len(data["cards"]) == 3
    for card in data["cards"]:
        assert card["source_id"] in ids and card["body"] in ARTICLE
    for question in data["quiz"]:
        assert len(set(question["options"])) == 4
        assert 0 <= question["answer"] <= 3 and question["source_id"] in ids


def test_long_unbroken_text_can_generate_demo_study(client):
    doc = client.post("/api/documents", json={"title": "A long token", "text": "a" * 2000}).json()
    response = client.post("/api/study", json={"document_id": doc["id"]})
    assert response.status_code == 200
    assert all(len(option) <= 400 for item in response.json()["quiz"] for option in item["options"])


def test_overview_and_cards_prefer_body_to_isolated_headings(client):
    text = "Article title\n\n01 / Introduction\n\n" + "BM25 ranks evidence based on term frequency. " * 4 + "\n\n02 / Storage\n\n" + "SQLite stores local documents and stable passages. " * 4
    doc = client.post("/api/documents", json={"title": "Article", "text": text}).json()
    study = client.post("/api/study", json={"document_id": doc["id"]}).json()
    assert [s["id"] for s in study["sources"]] == ["S3", "S5"]
    stream = events(client.post("/api/chat", json={"document_id": doc["id"], "question": "请讲解这篇文章的重点"}))
    assert [s["id"] for s in stream[0][1]["sources"]] == ["S3", "S5"]


def test_missing_document_and_input_boundaries(client):
    assert client.post("/api/chat", json={"document_id": "missing", "question": "BM25"}).status_code == 404
    assert client.post("/api/documents", json={"title": " ", "text": ARTICLE}).status_code == 422
    assert client.post("/api/documents", json={"title": "x", "text": ARTICLE, "url": "javascript:alert(1)"}).status_code == 422
    assert client.post("/api/documents", json={"title": "x", "text": "a" * 80001}).status_code == 422
    assert client.post("/api/documents", content=b"x" * 600001).status_code == 413
    malformed = json.dumps({"title": "bad\ud800", "text": ARTICLE}, ensure_ascii=True)
    response = client.post("/api/documents", content=malformed, headers={"Content-Type": "application/json"})
    assert response.status_code == 422 and "input" not in response.json()["detail"][0]


def test_origin_and_host_boundaries(client):
    assert client.get("/api/health", headers={"Origin": "https://evil.example"}).status_code == 403
    assert client.get("/api/health", headers={"Origin": "null"}).status_code == 403
    response = client.get("/api/health", headers={"Origin": "chrome-extension://" + "a" * 32})
    assert response.status_code == 200 and response.headers["access-control-allow-origin"] == "chrome-extension://" + "a" * 32
    assert client.get("/api/health", headers={"Host": "evil.example"}).status_code == 400


def test_sql_injection_is_treated_as_id(client):
    doc = add(client)
    assert client.delete("/api/documents/x' OR 1=1--").status_code == 404
    assert client.app.state.store.get(doc["id"]) is not None


def test_live_invalid_citation_is_flagged_and_stream_is_closed(tmp_path):
    class FakeProvider:
        closed = False

        async def stream(self, *args):
            try:
                yield "A model claim [S999]"
            finally:
                self.closed = True

    fake = FakeProvider()
    settings = Settings(str(tmp_path / "live.sqlite3"), "mock-key", "https://api.deepseek.com", "deepseek-flash", ())
    with TestClient(create_app(settings, fake)) as client:
        doc = add(client)
        result = events(client.post("/api/chat", json={"document_id": doc["id"], "question": "BM25?"}))
    assert result[-1][1]["invalid_citations"] == ["S999"]
    assert result[-1][1]["grounded"] is False and fake.closed


def test_live_provider_error_is_an_explicit_sse_error(tmp_path):
    class FailingProvider:
        async def stream(self, *args):
            raise ProviderError("模型连接中断")
            yield "unreachable"

    settings = Settings(str(tmp_path / "live.sqlite3"), "mock-key", "https://api.deepseek.com", "deepseek-flash", ())
    with TestClient(create_app(settings, FailingProvider())) as client:
        doc = add(client)
        result = events(client.post("/api/chat", json={"document_id": doc["id"], "question": "BM25?"}))
    assert result[-1] == ("error", {"message": "模型连接中断"})
