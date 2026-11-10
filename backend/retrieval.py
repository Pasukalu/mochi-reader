"""Dependency-free lexical RAG: English words + CJK bigrams, ranked with BM25.

This is deliberately not embedding/vector search. Source IDs are paragraph IDs,
not ranks, so a citation stays stable when the question changes.
"""

import math
import re
from collections import Counter

STOPWORDS = set("a an and are as at be by can do does for from how i in is it of on or that the this to was what when where which why with you your explain please tell about".split())
CJK_STOP = {"什么", "怎么", "如何", "为何", "为什么", "哪些", "是否", "一下", "可以", "我们", "一个", "这个", "那个", "中的", "的是", "以及", "关于", "文章", "原文", "内容", "请问", "解释", "告诉"}


def tokenize(text: str) -> list[str]:
    tokens = []
    for term in re.findall(r"[a-zA-Z0-9_]+|[\u3400-\u9fff]+", text.lower()):
        if re.fullmatch(r"[\u3400-\u9fff]+", term):
            tokens.extend(term[i:i + 2] for i in range(len(term) - 1) if term[i:i + 2] not in CJK_STOP)
        elif term not in STOPWORDS and len(term) > 1:
            tokens.append(term)
    return tokens


def chunk_text(text: str, max_chars: int = 650) -> list[str]:
    """Preserve text verbatim except surrounding whitespace, with bounded chunks."""
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text.replace("\r\n", "\n")) if part.strip()]
    chunks = []
    for paragraph in paragraphs:
        while len(paragraph) > max_chars:
            window = paragraph[:max_chars]
            boundaries = [m.end() for m in re.finditer(r"[。！？.!?]\s*|\n", window)]
            cut = boundaries[-1] if boundaries and boundaries[-1] > max_chars // 3 else max_chars
            chunks.append(paragraph[:cut].strip())
            paragraph = paragraph[cut:].strip()
        if paragraph:
            chunks.append(paragraph)
    return chunks


def retrieve(chunks: list[dict], query: str, limit: int = 4) -> list[dict]:
    query_terms = set(tokenize(query))
    if not chunks or not query_terms:
        return []
    corpus = [Counter(tokenize(chunk["text"])) for chunk in chunks]
    lengths = [sum(tokens.values()) for tokens in corpus]
    avg_length = sum(lengths) / len(lengths) or 1
    scored = []
    for index, counts in enumerate(corpus):
        score = 0.0
        for token in query_terms:
            frequency = counts[token]
            if not frequency:
                continue
            df = sum(token in other for other in corpus)
            idf = math.log(1 + (len(chunks) - df + 0.5) / (df + 0.5))
            score += idf * frequency * 2.5 / (
                frequency + 1.5 * (0.25 + 0.75 * lengths[index] / avg_length)
            )
        if score > 0:
            scored.append({**chunks[index], "score": round(score, 5)})
    return sorted(scored, key=lambda item: (-item["score"], item["ordinal"]))[:limit]
