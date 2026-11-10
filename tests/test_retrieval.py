from backend.retrieval import chunk_text, retrieve, tokenize


def corpus():
    return [
        {"id": "S1", "ordinal": 1, "text": "BM25 ranks documents by term frequency and inverse document frequency."},
        {"id": "S2", "ordinal": 2, "text": "向量检索通过嵌入模型将文本映射到语义空间，支持相似度匹配。"},
        {"id": "S3", "ordinal": 3, "text": "The transaction uses a SQLite WAL journal for concurrent readers."},
    ]


def test_bilingual_tokenization_and_stop_words():
    terms = tokenize("What is BM25? 向量检索是什么？")
    assert "bm25" in terms and "向量" in terms and "检索" in terms
    assert "what" not in terms and "什么" not in terms


def test_ranking_and_stable_source_ids():
    assert retrieve(corpus(), "BM25 frequency")[0]["id"] == "S1"
    assert retrieve(corpus(), "嵌入模型的向量检索")[0]["id"] == "S2"
    assert retrieve(corpus(), "SQLite WAL journal")[0]["id"] == "S3"


def test_unanswerable_query_returns_no_evidence():
    assert retrieve(corpus(), "Kubernetes autoscaling") == []
    assert retrieve(corpus(), "天气预报温度") == []


def test_chunks_are_bounded_and_do_not_drop_content():
    text = "向量检索需要嵌入模型。" * 200
    chunks = chunk_text(text)
    assert len(chunks) > 2 and all(len(chunk) <= 650 for chunk in chunks)
    assert "".join(chunks) == text


def test_empty_and_punctuation_queries():
    assert retrieve([], "BM25") == []
    assert retrieve(corpus(), "！？...") == []
