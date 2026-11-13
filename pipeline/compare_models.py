"""Step 2 of the offline pipeline: score each embedding model on synonym quality.

Usage:  python pipeline/compare_models.py

For each of the 50 target words in data/eval/synonym_key.json, find the
word's 5 nearest neighbours in a model's embedding space and count how many
are accepted synonyms. Run pipeline/embed.py first.

Two scores are reported per model:
  hits@5    average number of the 5 nearest neighbours that are real synonyms
  recall@5  average share of a word's accepted synonyms found in its 5 nearest

Most targets have fewer than 5 accepted synonyms, so hits@5 can never reach 5;
recall@5 is the fairer number and decides the winner.
"""

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
KEY_PATH = ROOT / "data" / "eval" / "synonym_key.json"
OUTPUT_DIR = ROOT / "pipeline" / "output"
TOP_K = 5


def nearest_neighbours(vectors: np.ndarray, order: list[str], word: str, k: int = TOP_K) -> list[str]:
    """The k words most similar to `word`, most similar first, excluding itself.

    Vectors are unit length, so the dot product is the cosine similarity.
    """
    index = order.index(word)
    similarity = vectors @ vectors[index]
    similarity[index] = -np.inf  # a word is not its own neighbour
    best = np.argsort(-similarity, kind="stable")[:k]
    return [order[i] for i in best]


def check_vectors(vectors: np.ndarray, name: str = "embeddings") -> np.ndarray:
    """Return the vectors as float64, or raise if they are not valid unit vectors.

    float64 is used for the similarity maths because float32 matrix products
    on some Macs raise spurious warnings. A real problem (NaN or infinite
    values, vectors that are not length 1) must stop the run, not be scored.
    """
    vectors = np.asarray(vectors, dtype=np.float64)
    if not np.isfinite(vectors).all():
        raise ValueError(f"{name} contains NaN or infinite values")
    norms = np.linalg.norm(vectors, axis=1)
    if not np.allclose(norms, 1.0, atol=1e-3):
        raise ValueError(f"{name} has vectors that are not length 1 (range {norms.min():.4f} to {norms.max():.4f})")
    return vectors


def score_model(vectors: np.ndarray, order: list[str], key: dict[str, list[str]], k: int = TOP_K) -> dict:
    """Score one model against the answer key."""
    vectors = check_vectors(vectors)
    per_word = {}
    for target, synonyms in key.items():
        neighbours = nearest_neighbours(vectors, order, target, k)
        found = [w for w in neighbours if w in synonyms]
        per_word[target] = {
            "neighbours": neighbours,
            "found": found,
            "hits": len(found),
            "recall": len(found) / min(len(synonyms), k),
        }
    return {
        "hits_at_5": float(np.mean([r["hits"] for r in per_word.values()])),
        "recall_at_5": float(np.mean([r["recall"] for r in per_word.values()])),
        "per_word": per_word,
    }


def pick_winner(results: dict[str, dict]) -> str:
    """Highest recall@5 wins; hits@5 breaks a tie."""
    return max(results, key=lambda name: (results[name]["recall_at_5"], results[name]["hits_at_5"]))


def load_key(path: Path = KEY_PATH) -> dict[str, list[str]]:
    return json.loads(path.read_text(encoding="utf-8"))["key"]


def main() -> int:
    order_path = OUTPUT_DIR / "word_order.json"
    embedding_paths = sorted(OUTPUT_DIR.glob("embeddings_*.npy"))
    if not order_path.exists() or not embedding_paths:
        print("No embeddings found. Run: python pipeline/embed.py")
        return 1

    order = json.loads(order_path.read_text(encoding="utf-8"))
    key = load_key()
    results = {}
    for path in embedding_paths:
        name = path.stem.removeprefix("embeddings_")
        vectors = np.load(path)
        if vectors.shape[0] != len(order):
            print(f"{path.name} has {vectors.shape[0]} rows but word_order.json has {len(order)} words.")
            return 1
        try:
            results[name] = score_model(vectors, order, key)
        except ValueError as error:
            print(f"{path.name}: {error}. Re-run pipeline/embed.py for this model.")
            return 1

    winner = pick_winner(results)
    print(f"{'model':<12}{'hits@5':>8}{'recall@5':>10}")
    for name, result in sorted(results.items(), key=lambda item: -item[1]["recall_at_5"]):
        print(f"{name:<12}{result['hits_at_5']:>8.2f}{result['recall_at_5']:>10.1%}")
    print(f"\nWinner: {winner}")

    report = {"top_k": TOP_K, "targets": len(key), "winner": winner, "models": results}
    report_path = OUTPUT_DIR / "model_comparison.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Full per-word results saved to {report_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
