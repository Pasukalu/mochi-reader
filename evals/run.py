"""python -m evals.run [--output evals/report.json]

Measures retrieval on a tiny, hand-written synthetic fixture. It does not measure
LLM correctness, faithfulness, semantic search or real-world generalization.
"""

import argparse
import json
from pathlib import Path

from backend.retrieval import retrieve


def evaluate(dataset: dict, k: int = 3) -> dict:
    details = []
    recalls, reciprocal_ranks, refusals = [], [], []
    for case in dataset["cases"]:
        hits = retrieve(dataset["chunks"], case["query"], k)
        ranked = [hit["id"] for hit in hits]
        relevant = set(case["relevant"])
        detail = {"query": case["query"], "expected": case["relevant"], "retrieved": ranked}
        if relevant:
            recall = len(relevant & set(ranked)) / len(relevant)
            rr = next((1 / (i + 1) for i, source in enumerate(ranked) if source in relevant), 0)
            recalls.append(recall)
            reciprocal_ranks.append(rr)
            detail.update(recall=recall, reciprocal_rank=rr)
        else:
            refusal = not hits
            refusals.append(refusal)
            detail["empty_retrieval"] = refusal
        details.append(detail)
    return {
        "scope": "hand-written synthetic lexical retrieval regression; not LLM quality",
        "k": k, "cases": len(details), "answerable_cases": len(recalls), "unanswerable_cases": len(refusals),
        f"recall_at_{k}": round(sum(recalls) / len(recalls), 4),
        f"mrr_at_{k}": round(sum(reciprocal_ranks) / len(reciprocal_ranks), 4),
        "unanswerable_empty_retrieval_rate": round(sum(refusals) / len(refusals), 4),
        "details": details,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    data = json.loads(Path(__file__).with_name("dataset.json").read_text(encoding="utf-8"))
    report = evaluate(data)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    if report["recall_at_3"] < 0.8 or report["unanswerable_empty_retrieval_rate"] < 1:
        raise SystemExit("Retrieval regression threshold failed.")


if __name__ == "__main__":
    main()
