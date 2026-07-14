from pathlib import Path
import csv
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from taura.intent_classifier import classify
from taura.rag_retriever import RagRetriever
from taura.entity_extractor import extract


DATA = ROOT / "evaluation" / "multilingual_100_queries.json"
OUT = ROOT / "evaluation" / "results"


# ---------------------------------------------------------------------------
# Evaluation contract
# ---------------------------------------------------------------------------
#
# The production classifier uses internal routing labels:
#
#   price_query
#   climate_query
#
# The evaluation dataset uses externally documented task labels:
#
#   market_price
#   climate_alert
#
# We preserve the raw classifier output for auditability and map it to the
# canonical evaluation label before scoring.
#
# This avoids changing production classifier behaviour merely to satisfy the
# benchmark label vocabulary.
#

CANONICAL_INTENT_MAP = {
    "greeting": "greeting",
    "price_query": "market_price",
    "market_price": "market_price",
    "climate_query": "climate_alert",
    "climate_alert": "climate_alert",
    "financial_query": "financial_query",
    "human_handoff": "human_handoff",
    "consent_yes": "consent_yes",
    "consent_no": "consent_no",
    "unknown": "unknown",
}


def get_raw_intent(classification_result) -> str:
    """
    Return the classifier's raw intent label as a string.
    """

    intent = classification_result.intent

    if hasattr(intent, "value"):
        return intent.value

    return str(intent)


def canonicalize_intent(raw_intent: str) -> str:
    """
    Map the production classifier label to the canonical evaluation label.

    Unknown/unmapped labels remain unchanged so evaluation results expose
    unexpected classifier outputs rather than silently hiding them.
    """

    return CANONICAL_INTENT_MAP.get(raw_intent, raw_intent)


def retrieve_source_type(
    retriever,
    canonical_intent: str,
    entities: dict,
):
    """
    Execute retrieval using the canonical evaluation intent.

    Returns the retrieved source type or None when the query does not require
    retrieval.
    """

    if canonical_intent == "market_price":
        record = retriever.find_price(entities)

    elif canonical_intent == "climate_alert":
        record = retriever.find_climate_alert(entities)

    elif canonical_intent == "financial_query":
        products = retriever.find_financial_products()
        record = products[0] if products else None

    else:
        record = None

    if record is None:
        return None

    return getattr(record, "source_type", None)


def main():
    rows = json.loads(DATA.read_text(encoding="utf-8"))

    retriever = RagRetriever()

    results = []

    for row in rows:
        query = row["query"]

        classification = classify(query)

        raw_intent = get_raw_intent(classification)
        canonical_intent = canonicalize_intent(raw_intent)

        entities = extract(query)

        retrieved_source_type = retrieve_source_type(
            retriever,
            canonical_intent,
            entities,
        )

        expected_intent = row["expected_intent"]
        expected_source_type = row.get("expected_source_type")

        intent_correct = canonical_intent == expected_intent

        if expected_source_type is None:
            source_correct = retrieved_source_type is None
        else:
            source_correct = retrieved_source_type == expected_source_type

        results.append(
            {
                **row,
                "raw_predicted_intent": raw_intent,
                "canonical_predicted_intent": canonical_intent,
                # Retain the original field for compatibility with existing
                # reports and PowerShell analysis commands.
                "predicted_intent": canonical_intent,
                "retrieved_source_type": retrieved_source_type,
                "intent_correct": intent_correct,
                "source_correct": source_correct,
            }
        )

    query_count = len(results)

    intent_accuracy = (
        sum(result["intent_correct"] for result in results) / query_count
        if query_count
        else 0.0
    )

    retrieval_cases = [
        result
        for result in results
        if result.get("expected_source_type") is not None
    ]

    retrieval_accuracy = (
        sum(result["source_correct"] for result in retrieval_cases)
        / len(retrieval_cases)
        if retrieval_cases
        else 0.0
    )

    languages = sorted({result["language"] for result in results})

    language_intent_accuracy = {}

    for language in languages:
        language_results = [
            result for result in results if result["language"] == language
        ]

        language_intent_accuracy[language] = (
            sum(result["intent_correct"] for result in language_results)
            / len(language_results)
            if language_results
            else 0.0
        )

    max_language_gap = (
        max(language_intent_accuracy.values())
        - min(language_intent_accuracy.values())
        if language_intent_accuracy
        else 0.0
    )

    summary = {
        "queries": query_count,
        "intent_accuracy": intent_accuracy,
        "retrieval_accuracy": retrieval_accuracy,
        "language_intent_accuracy": language_intent_accuracy,
        "max_language_gap": max_language_gap,
    }

    OUT.mkdir(parents=True, exist_ok=True)

    json_output = {
        "summary": summary,
        "results": results,
    }

    (OUT / "evaluation_results.json").write_text(
        json.dumps(json_output, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    csv_fields = list(results[0].keys()) if results else []

    with (OUT / "evaluation_results.csv").open(
        "w",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=csv_fields,
        )

        writer.writeheader()
        writer.writerows(results)

    markdown_lines = [
        "# Taura AI 100-Query Evaluation Results",
        "",
        f"- Queries: **{query_count}**",
        f"- Intent accuracy: **{intent_accuracy:.1%}**",
        f"- Retrieval accuracy: **{retrieval_accuracy:.1%}**",
        f"- Maximum language gap: **{max_language_gap:.1%}**",
        "",
        "## Intent Accuracy by Language",
        "",
    ]

    for language, accuracy in language_intent_accuracy.items():
        markdown_lines.append(
            f"- {language} intent accuracy: **{accuracy:.1%}**"
        )

    markdown_lines.extend(
        [
            "",
            "## Evaluation Contract",
            "",
            "Production classifier labels are preserved in "
            "`raw_predicted_intent`.",
            "",
            "Canonical benchmark labels are recorded in "
            "`canonical_predicted_intent` and used for intent scoring and "
            "retrieval routing.",
            "",
            "Canonical mappings applied:",
            "",
            "- `price_query` → `market_price`",
            "- `climate_query` → `climate_alert`",
            "",
            "Unmapped labels are preserved unchanged for auditability.",
            "",
        ]
    )

    (OUT / "EVALUATION_RESULTS.md").write_text(
        "\n".join(markdown_lines),
        encoding="utf-8",
    )

    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()