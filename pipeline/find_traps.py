"""Step 4 of the offline pipeline: find look-alike trap candidates.

Usage:  python pipeline/find_traps.py [--model mpnet] [--top 100] [--min-lookalike 0.6]

A trap is a pair of words that look or sound alike but mean different things
(venal / venial). For every pair of words this script scores:

  spelling  the larger of edit similarity and shared-prefix share
  sound     edit similarity of the two words' Metaphone codes
  meaning   cosine similarity of the embeddings (from step 1)

and ranks pairs by  trap_score = max(spelling, sound) * (1 - meaning),
which is high when a pair looks or sounds alike but means something different.
Pairs below --min-lookalike on both spelling and sound are dropped first.

Output, for hand review (Vishal fills in the `accept` column):
  pipeline/output/trap_candidates.csv
  pipeline/output/trap_candidates.json

Spelling and sound need only the word list; meaning needs pipeline/embed.py
to have been run.
"""

import argparse
import csv
import itertools
import json
import os
import sys
from pathlib import Path

import jellyfish
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
WORDS_PATH = ROOT / "data" / "words.json"
EXPECTED_PATH = ROOT / "data" / "eval" / "expected_traps.json"
OUTPUT_DIR = ROOT / "pipeline" / "output"
DEFAULT_TOP = 100
DEFAULT_MIN_LOOKALIKE = 0.6


def edit_similarity(a: str, b: str) -> float:
    """1 for identical strings, 0 for nothing in common: 1 - edits / length of the longer one."""
    if not a and not b:
        return 1.0
    return 1.0 - jellyfish.levenshtein_distance(a, b) / max(len(a), len(b))


def prefix_similarity(a: str, b: str) -> float:
    """Share of the longer word taken up by the prefix the two words have in common."""
    return len(os.path.commonprefix([a, b])) / max(len(a), len(b))


def spelling_score(a: str, b: str) -> float:
    return max(edit_similarity(a, b), prefix_similarity(a, b))


def sound_score(code_a: str, code_b: str) -> float:
    """Edit similarity of two phonetic codes; 1.0 means the words are coded as sounding the same."""
    return edit_similarity(code_a, code_b)


def phonetic_code(word: str) -> str:
    return jellyfish.metaphone(word)


def trap_score(lookalike: float, meaning: float) -> float:
    """High for pairs that look or sound alike but are not related in meaning."""
    return lookalike * (1.0 - max(meaning, 0.0))


def meaning_matrix(vectors: np.ndarray) -> np.ndarray:
    """Cosine similarity of every pair of unit vectors. einsum, not `@` (see compare_models.py)."""
    return np.einsum("ik,jk->ij", vectors, vectors)


def score_pairs(words: list[str], vectors: np.ndarray | None = None) -> list[dict]:
    """Score every pair of words. Without vectors the meaning is left out (None)."""
    codes = [phonetic_code(w) for w in words]
    meanings = meaning_matrix(vectors) if vectors is not None else None
    rows = []
    for i, j in itertools.combinations(range(len(words)), 2):
        spelling = spelling_score(words[i], words[j])
        sound = sound_score(codes[i], codes[j])
        lookalike = max(spelling, sound)
        meaning = float(meanings[i, j]) if meanings is not None else None
        rows.append(
            {
                "word_a": words[i],
                "word_b": words[j],
                "spelling": spelling,
                "sound": sound,
                "lookalike": lookalike,
                "meaning": meaning,
                "trap_score": trap_score(lookalike, meaning) if meaning is not None else lookalike,
            }
        )
    return rows


def select_candidates(rows: list[dict], top: int = DEFAULT_TOP, min_lookalike: float = DEFAULT_MIN_LOOKALIKE) -> list[dict]:
    """Keep pairs that look or sound alike, rank them by trap score, and return the best `top`."""
    kept = [r for r in rows if r["lookalike"] >= min_lookalike]
    kept.sort(key=lambda r: (-r["trap_score"], r["word_a"], r["word_b"]))
    return kept[:top]


def expected_coverage(candidates: list[dict], expected: list[list[str]]) -> tuple[list, list]:
    """Which of the expected pairs appear among the candidates (found) and which do not (missing)."""
    present = {frozenset((c["word_a"], c["word_b"])) for c in candidates}
    found = [p for p in expected if frozenset(p) in present]
    missing = [p for p in expected if frozenset(p) not in present]
    return found, missing


def write_outputs(candidates: list[dict], output_dir: Path = OUTPUT_DIR) -> tuple[Path, Path]:
    """Write the candidates as a CSV for hand review and as JSON for later use."""
    output_dir.mkdir(parents=True, exist_ok=True)
    columns = ["rank", "word_a", "word_b", "spelling", "sound", "meaning", "trap_score", "accept"]
    csv_path = output_dir / "trap_candidates.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        for rank, row in enumerate(candidates, start=1):
            writer.writerow(
                [rank, row["word_a"], row["word_b"]]
                + ["" if row[k] is None else f"{row[k]:.3f}" for k in ("spelling", "sound", "meaning", "trap_score")]
                + [""]
            )
    json_path = output_dir / "trap_candidates.json"
    json_path.write_text(
        json.dumps(
            [{"rank": i, **{k: (None if v is None else round(v, 4)) if isinstance(v, float) or v is None else v for k, v in r.items()}}
             for i, r in enumerate(candidates, start=1)],
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    return csv_path, json_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Find look-alike trap candidates.")
    parser.add_argument("--model", default="mpnet", help="which model's embeddings give the meaning score")
    parser.add_argument("--top", type=int, default=DEFAULT_TOP)
    parser.add_argument("--min-lookalike", type=float, default=DEFAULT_MIN_LOOKALIKE)
    args = parser.parse_args()

    words = [entry["word"] for entry in json.loads(WORDS_PATH.read_text(encoding="utf-8"))]
    vectors_path = OUTPUT_DIR / f"embeddings_{args.model}.npy"
    order_path = OUTPUT_DIR / "word_order.json"
    if not vectors_path.exists() or not order_path.exists():
        print(f"Missing {vectors_path.name} or word_order.json. Run: python pipeline/embed.py")
        return 1
    if json.loads(order_path.read_text(encoding="utf-8")) != words:
        print("word_order.json does not match data/words.json. Re-run: python pipeline/embed.py")
        return 1

    vectors = np.load(vectors_path).astype(np.float64)
    rows = score_pairs(words, vectors)
    candidates = select_candidates(rows, args.top, args.min_lookalike)
    csv_path, _ = write_outputs(candidates)

    print(f"{len(rows)} pairs scored, {len(candidates)} candidates kept (look-alike >= {args.min_lookalike}).")
    print(f"{'rank':<6}{'pair':<34}{'spell':>7}{'sound':>7}{'mean':>7}{'trap':>7}")
    for rank, row in enumerate(candidates[:20], start=1):
        pair = f"{row['word_a']} / {row['word_b']}"
        print(f"{rank:<6}{pair:<34}{row['spelling']:>7.2f}{row['sound']:>7.2f}{row['meaning']:>7.2f}{row['trap_score']:>7.2f}")
    print(f"... full list in {csv_path.relative_to(ROOT)}; fill in the 'accept' column.")

    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))["pairs"]
    found, missing = expected_coverage(candidates, expected)
    print(f"\nSmoke test: {len(found)} of {len(expected)} pairs from data/eval/expected_traps.json are in the top {args.top}.")
    if missing:
        print("Not found: " + ", ".join(f"{a}/{b}" for a, b in missing))
    return 0


if __name__ == "__main__":
    sys.exit(main())
