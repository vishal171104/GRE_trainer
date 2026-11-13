"""Tests for pipeline/layout.py, using small synthetic vectors (no models needed)."""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import embed  # noqa: E402
import layout  # noqa: E402


def clustered_vectors(clusters=4, per_cluster=15, dims=24, seed=0):
    """Unit vectors in tight, well-separated clusters, like synonym families."""
    rng = np.random.default_rng(seed)
    centres = rng.normal(size=(clusters, dims)) * 3
    rows = [centre + rng.normal(size=(per_cluster, dims)) * 0.3 for centre in centres]
    return embed.normalize(np.vstack(rows))


VECTORS = clustered_vectors()


def test_preservation_is_perfect_when_the_layout_matches_the_space():
    # Using the first 3 coordinates of a genuinely 3D space loses nothing.
    rng = np.random.default_rng(1)
    flat = embed.normalize(rng.normal(size=(40, 3)))
    assert layout.neighbour_preservation(flat, flat, k=5) == 1.0


def test_preservation_of_a_random_layout_is_near_the_random_baseline():
    rng = np.random.default_rng(2)
    random_positions = rng.normal(size=(len(VECTORS), 3))
    score = layout.neighbour_preservation(VECTORS, random_positions, k=10)
    assert score < 0.2  # baseline is 10 / 59 = 0.17 on average for 60 words; allow noise


def test_every_method_returns_one_3d_point_per_word_and_beats_random():
    results = layout.run_all(VECTORS)
    assert set(results) == {"umap", "tsne", "pca"}
    for name, result in results.items():
        assert result["positions"].shape == (len(VECTORS), 3), name
        assert result["preservation"] > 0.5, name  # clusters are easy to preserve


def test_layouts_are_repeatable_with_a_fixed_seed():
    first = layout.layout_umap(VECTORS)
    second = layout.layout_umap(VECTORS)
    assert np.allclose(first, second)
    assert np.allclose(layout.layout_tsne(VECTORS), layout.layout_tsne(VECTORS))


def test_scale_centres_and_fits_the_unit_cube():
    scaled = layout.scale(np.array([[10.0, 0, 0], [20.0, 4, 0], [30.0, -4, 2]]))
    assert np.allclose(scaled.mean(axis=0), 0)
    assert np.abs(scaled).max() == 1.0


def test_positions_json_pairs_each_word_with_its_point():
    rows = layout.positions_json(["a", "b", "c"], np.array([[0.0, 0, 0], [1, 1, 1], [2, 0, -2]]))
    assert [row["word"] for row in rows] == ["a", "b", "c"]
    assert set(rows[0]) == {"word", "x", "y", "z"}
    assert max(abs(row[axis]) for row in rows for axis in "xyz") <= 1.0
