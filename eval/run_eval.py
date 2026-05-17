"""
RAGAS evaluation pipeline for StarkBot.

Usage:
  python eval/run_eval.py --mode baseline   # original simple prompt
  python eval/run_eval.py --mode refined    # chain-of-thought grounded prompt (default)
  python eval/run_eval.py --mode compare    # run both and print delta
  python eval/run_eval.py --limit 10        # quick test with fewer cases
"""
import argparse
import json
import os
import sys
import warnings
import datetime
import numpy as np

warnings.filterwarnings("ignore", category=DeprecationWarning)

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dotenv import load_dotenv
load_dotenv()

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    _faithfulness as faithfulness,
    _answer_relevancy as answer_relevancy,
    _context_precision as context_precision,
    _context_recall as context_recall,
)
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_openai import ChatOpenAI, OpenAIEmbeddings as LCOpenAIEmbeddings

from query_rag import RAGQuerySystem

BASELINE_PROMPT = (
    "You are an expert Iron Man chatbot named StarkBot. "
    "Answer the user's question based on the provided context about Iron Man.\n\n"
    "Context about Iron Man:\n{context}\n\n"
    "User Question: {query}\n\n"
    "Provide a helpful, accurate answer based on the context. "
    "If the context doesn't contain enough information to answer the question, say so politely. "
    "Avoid statements like 'according to the context provided'."
)


def setup_metrics():
    """Wire up LLM and embeddings to RAGAS metrics (required for RAGAS 0.4.x)."""
    api_key = os.getenv("OPENAI_API_KEY")
    llm = LangchainLLMWrapper(ChatOpenAI(model="gpt-4o-mini", api_key=api_key))
    emb = LangchainEmbeddingsWrapper(
        LCOpenAIEmbeddings(model="text-embedding-3-small", api_key=api_key)
    )
    faithfulness.llm = llm
    answer_relevancy.llm = llm
    answer_relevancy.embeddings = emb
    context_precision.llm = llm
    context_recall.llm = llm


def mean_score(val) -> float:
    """Normalize RAGAS score values (may be list, np.float, or float)."""
    if isinstance(val, (list, np.ndarray)):
        arr = [float(v) for v in val if v is not None and not (isinstance(v, float) and np.isnan(v))]
        return float(np.mean(arr)) if arr else float("nan")
    return float(val) if val is not None else float("nan")


def run_baseline_query(openai_client, query: str, contexts: list[str]) -> str:
    context_str = "\n\n".join(contexts)
    msg = BASELINE_PROMPT.format(context=context_str, query=query)
    resp = openai_client.chat.completions.create(
        model=os.getenv("CHAT_MODEL", "gpt-4o-mini"),
        messages=[{"role": "user", "content": msg}],
        max_tokens=500,
        temperature=0.7,
    )
    return resp.choices[0].message.content


def build_dataset(rag: RAGQuerySystem, test_cases: list, mode: str) -> Dataset:
    from openai import OpenAI
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    questions, answers, contexts, ground_truths = [], [], [], []
    for i, tc in enumerate(test_cases):
        q = tc["question"]
        print(f"  [{i+1}/{len(test_cases)}] {q[:65]}...")
        chunks = rag.retrieve(q)
        ctx_texts = [c["content"] for c in chunks]

        if mode == "baseline":
            answer = run_baseline_query(openai_client, q, ctx_texts)
        else:
            result = rag.query(q)
            answer = result["response"]

        questions.append(q)
        answers.append(answer)
        contexts.append(ctx_texts)
        ground_truths.append(tc["ground_truth"])

    return Dataset.from_dict({
        "question": questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": ground_truths,
    })


def run_eval(mode: str, test_cases: list) -> dict:
    print(f"\n{'='*60}\nRunning RAGAS evaluation — mode: {mode}\n{'='*60}")
    rag = RAGQuerySystem()
    dataset = build_dataset(rag, test_cases, mode)
    rag.close()

    print("\nRunning RAGAS metrics...")
    setup_metrics()
    result = evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
    )

    scores = {
        "mode": mode,
        "faithfulness": mean_score(result["faithfulness"]),
        "answer_relevancy": mean_score(result["answer_relevancy"]),
        "context_precision": mean_score(result["context_precision"]),
        "context_recall": mean_score(result["context_recall"]),
        "n_samples": len(test_cases),
        "timestamp": datetime.datetime.now().isoformat(),
    }

    out_path = os.path.join(
        os.path.dirname(__file__),
        f"results_{mode}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
    )
    with open(out_path, "w") as f:
        json.dump(scores, f, indent=2)

    print(f"\nResults ({mode}):")
    for k, v in scores.items():
        if isinstance(v, float):
            print(f"  {k:<22}: {v:.4f}")
    print(f"Saved → {out_path}")
    return scores


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["baseline", "refined", "compare"], default="refined")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    test_path = os.path.join(os.path.dirname(__file__), "test_cases.json")
    with open(test_path) as f:
        test_cases = json.load(f)
    if args.limit:
        test_cases = test_cases[:args.limit]
    print(f"Loaded {len(test_cases)} test cases")

    if args.mode == "compare":
        baseline = run_eval("baseline", test_cases)
        refined = run_eval("refined", test_cases)

        print("\n" + "="*60)
        print("COMPARISON SUMMARY")
        print("="*60)
        metrics = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
        for m in metrics:
            b, r = baseline[m], refined[m]
            if not (np.isnan(b) or np.isnan(r)) and b > 0:
                delta = (r - b) / b * 100
                arrow = "▲" if delta > 0 else "▼"
                print(f"  {m:<22} baseline={b:.4f}  refined={r:.4f}  {arrow} {abs(delta):.1f}%")
            else:
                print(f"  {m:<22} baseline={b:.4f}  refined={r:.4f}  (n/a)")
    else:
        run_eval(args.mode, test_cases)


if __name__ == "__main__":
    main()
