"""Step 3 of the offline pipeline: place every word in 3D for the galaxy.

Usage:  python pipeline/layout.py [--model mpnet] [--use umap]

Runs three layout methods (UMAP, t-SNE, PCA) on one model's embeddings with a
fixed random seed, scores each by neighbour preservation, and saves:
  pipeline/output/layout_<method>.npy   raw 3D positions for every method
  pipeline/output/positions.json        scaled x, y, z for the method chosen with --use
  pipeline/output/layout_comparison.json  the scores

Neighbour preservation: for each word, take its 10 nearest neighbours in the
full embedding space and in 3D, and count how many are the same. 1.0 means the
3D map keeps every neighbourhood; the random baseline is about 0.03.

A 3D map always distorts distances, which is why synonym search elsewhere uses
the full vectors, not these positions. Run pipeline/embed.py first.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "pipeline" / "output"
SEED = 42
NEIGHBOURS = 10
METHODS = ("umap", "tsne", "pca")


def cosine_similarity_matrix(vectors: np.ndarray) -> np.ndarray:
    """Similarity of every pair of unit vectors. Uses einsum, not `@` (see compare_models.py)."""
    return np.einsum("ik,jk->ij", vectors, vectors)


def neighbour_sets(distances: np.ndarray, k: int) -> list[set[int]]:
    """For each row, the indices of its k smallest distances, excluding itself."""
    distances = distances.copy()
    np.fill_diagonal(distances, np.inf)
    nearest = np.argsort(distances, axis=1, kind="stable")[:, :k]
    return [set(row.tolist()) for row in nearest]


def neighbour_preservation(vectors: np.ndarray, positions: np.ndarray, k: int = NEIGHBOURS) -> float:
    """Average share of each word's k nearest neighbours that survive in the 3D layout."""
    full = neighbour_sets(1.0 - cosine_similarity_matrix(vectors), k)
    gaps = positions[:, None, :] - positions[None, :, :]
    low = neighbour_sets(np.sqrt((gaps**2).sum(axis=2)), k)
    return float(np.mean([len(a & b) / k for a, b in zip(full, low)]))


def layout_pca(vectors: np.ndarray, seed: int = SEED) -> np.ndarray:
    from sklearn.decomposition import PCA

    return PCA(n_components=3, random_state=seed).fit_transform(vectors)


def layout_tsne(vectors: np.ndarray, seed: int = SEED) -> np.ndarray:
    from sklearn.manifold import TSNE

    perplexity = min(30, (len(vectors) - 1) / 3)
    return TSNE(
        n_components=3, metric="cosine", init="pca", perplexity=perplexity, random_state=seed
    ).fit_transform(vectors)


def layout_umap(vectors: np.ndarray, seed: int = SEED) -> np.ndarray:
    import umap

    # compatibility_layout=True keeps the long-standing UMAP pipeline, so results
    # stay the same when umap-learn changes its default in a later release.
    return umap.UMAP(
        n_components=3,
        metric="cosine",
        n_neighbors=15,
        min_dist=0.1,
        random_state=seed,
        n_jobs=1,
        compatibility_layout=True,
    ).fit_transform(vectors)


LAYOUTS = {"umap": layout_umap, "tsne": layout_tsne, "pca": layout_pca}


def scale(positions: np.ndarray) -> np.ndarray:
    """Centre the layout on the origin and fit it inside the cube from -1 to 1."""
    centred = positions - positions.mean(axis=0)
    return centred / np.abs(centred).max()


def run_all(vectors: np.ndarray, seed: int = SEED) -> dict[str, dict]:
    """Lay out the vectors with every method and score each one."""
    results = {}
    for name in METHODS:
        # On some Macs numpy's matrix product (Apple's Accelerate library) raises
        # spurious divide-by-zero / overflow / invalid-value flags inside
        # scikit-learn, which we cannot change (see compare_models.py). Hiding
        # them is safe only because the output is checked below: the positions
        # must be finite, and the preservation score is computed independently
        # from the original vectors, so a broken layout would score near the
        # random baseline.
        with np.errstate(divide="ignore", over="ignore", invalid="ignore"):
            positions = np.asarray(LAYOUTS[name](vectors, seed), dtype=np.float64)
        if not np.isfinite(positions).all():
            raise ValueError(f"the {name} layout contains NaN or infinite values")
        results[name] = {
            "positions": positions,
            "preservation": neighbour_preservation(vectors, positions),
        }
    return results


def positions_json(order: list[str], positions: np.ndarray) -> list[dict]:
    return [
        {"word": word, "x": round(float(x), 5), "y": round(float(y), 5), "z": round(float(z), 5)}
        for word, (x, y, z) in zip(order, scale(positions))
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Lay out the words in 3D.")
    parser.add_argument("--model", default="mpnet", help="which model's embeddings to use")
    parser.add_argument("--use", choices=METHODS, default="umap", help="method saved to positions.json")
    args = parser.parse_args()

    vectors_path = OUTPUT_DIR / f"embeddings_{args.model}.npy"
    order_path = OUTPUT_DIR / "word_order.json"
    if not vectors_path.exists() or not order_path.exists():
        print(f"Missing {vectors_path.name} or word_order.json. Run: python pipeline/embed.py")
        return 1

    vectors = np.load(vectors_path).astype(np.float64)
    order = json.loads(order_path.read_text(encoding="utf-8"))
    results = run_all(vectors)

    print(f"{'method':<8}{'neighbour preservation':>24}")
    for name, result in sorted(results.items(), key=lambda item: -item[1]["preservation"]):
        print(f"{name:<8}{result['preservation']:>24.3f}")
        np.save(OUTPUT_DIR / f"layout_{name}.npy", result["positions"])
    random_baseline = NEIGHBOURS / (len(order) - 1)
    print(f"random baseline: {random_baseline:.3f}   (k={NEIGHBOURS}, seed={SEED})")

    (OUTPUT_DIR / "positions.json").write_text(
        json.dumps(positions_json(order, results[args.use]["positions"])) + "\n", encoding="utf-8"
    )
    summary = {
        "model": args.model,
        "seed": SEED,
        "neighbours": NEIGHBOURS,
        "random_baseline": random_baseline,
        "used_for_positions": args.use,
        "preservation": {name: result["preservation"] for name, result in results.items()},
    }
    (OUTPUT_DIR / "layout_comparison.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"Saved positions for '{args.use}' to pipeline/output/positions.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
