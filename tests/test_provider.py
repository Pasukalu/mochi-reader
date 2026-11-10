import asyncio
import json

import httpx
import pytest

from backend.config import Settings
from backend.provider import DeepSeek, ProviderError

SOURCES = [{"id": "S1", "text": "BM25 ranks paragraphs.", "url": "", "title": "note"}]


class FragmentedStream(httpx.AsyncByteStream):
    def __init__(self, data):
        self.data = data

    async def __aiter__(self):
        for index in range(0, len(self.data), 3):
            yield self.data[index:index + 3]


def provider(handler):
    config = Settings("unused.sqlite3", "test-key-never-log", "https://api.deepseek.com", "deepseek-flash", ())
    return DeepSeek(config, httpx.MockTransport(handler))


def collect(adapter):
    async def run():
        return "".join([token async for token in adapter.stream("BM25?", SOURCES, "mochi", [])])
    return asyncio.run(run())


def test_stream_handles_fragmented_multibyte_utf8_and_heartbeats():
    def handler(request):
        body = json.loads(request.content)
        assert body["thinking"] == {"type": "disabled"} and body["stream"] is True
        wire = ": keep-alive\n\ndata: " + json.dumps({"choices": [{"delta": {"content": "词法检索 [S1]"}, "finish_reason": "stop"}]}, ensure_ascii=False) + "\n\ndata: [DONE]\n\n"
        return httpx.Response(200, stream=FragmentedStream(wire.encode()))
    assert collect(provider(handler)) == "词法检索 [S1]"


@pytest.mark.parametrize("wire", [
    b'data: {invalid}\n\ndata: [DONE]\n\n',
    b'data: []\n\ndata: [DONE]\n\n',
    b'data: {"choices":["invalid"]}\n\ndata: [DONE]\n\n',
    b'data: {"choices":[{"delta":{"content":"partial"}}]}\n\n',
    b'data: [DONE]\n\n',
    b'data: {"choices":[{"delta":{},"finish_reason":"length"}]}\n\ndata: [DONE]\n\n',
    b'data: {"choices":[{"delta":{"content":"partial"},"finish_reason":"insufficient_system_resource"}]}\n\ndata: [DONE]\n\n',
    b'data: {"choices":[{"delta":{"content":"partial"},"finish_reason":"aborted"}]}\n\ndata: [DONE]\n\n',
    b'data: {"choices":[{"delta":{"content":"partial"}}]}\n\ndata: [DONE]\n\n',
])
def test_bad_or_truncated_stream_is_reported(wire):
    with pytest.raises(ProviderError):
        collect(provider(lambda request: httpx.Response(200, stream=FragmentedStream(wire))))


def test_auth_error_does_not_expose_server_secret_or_raw_response():
    with pytest.raises(ProviderError) as error:
        collect(provider(lambda request: httpx.Response(401, text="test-key-never-log")))
    assert "test-key-never-log" not in str(error.value) and "鉴权" in str(error.value)


def test_json_study_validates_source_ids():
    content = {"cards": [{"title": "BM25", "body": "Ranks paragraphs", "source_id": "S999"}], "quiz": [{"question": "Which?", "options": ["a", "b", "c", "d"], "answer": 0, "explanation": "source", "source_id": "S1"}]}
    adapter = provider(lambda request: httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(content)}}]}))
    with pytest.raises(ProviderError, match="引用无效"):
        asyncio.run(adapter.study(SOURCES, "mochi"))


@pytest.mark.parametrize("content", ["", "    ", "{broken json}", '{"cards":[],"quiz":[]}'])
def test_empty_or_malformed_json_study_is_reported(content):
    adapter = provider(lambda request: httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": content}}]}))
    with pytest.raises(ProviderError):
        asyncio.run(adapter.study(SOURCES, "mochi"))
