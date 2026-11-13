"""Tests for pipeline/embed.py. They use a fake encoder, so no model is downloaded.

Run with:  python -m pytest pipeline/tests
"""

import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import embed  # noqa: E402

WORDS = [
    {"word": "venal", "definition": "Open to bribery.", "examples": ["A venal official.", "Venal judges."]},
    {"word": "venial", "definition": "Easily forgiven.", "examples": ["A venial fault.", "Venial sins."]},
    {"word": "lucid", "definition": "Easy to understand.", "examples": ["A lucid talk.", "Lucid prose."]},
]


def fake_encoder(texts):
    """Deterministic stand-in for a model: 4 numbers derived from each text."""
    return [[len(t), t.count("a") + 1, t.count("e") + 1, 1.0] for t in texts]


def test_build_text_contains_word_definition_and_examples():
    text = embed.build_text(WORDS[0])
    assert text == "venal: Open to bribery. A venal official. Venal judges."


def test_embed_words_returns_one_unit_vector_per_word():
    vectors = embed.embed_words(WORDS, fake_encoder)
    assert vectors.shape == (3, 4)
    assert vectors.dtype == np.float32
    assert np.allclose(np.linalg.norm(vectors, axis=1), 1.0, atol=1e-6)


def test_embed_words_rejects_wrong_number_of_vectors():
    with pytest.raises(ValueError):
        embed.embed_words(WORDS, lambda texts: [[1.0, 2.0]])


def test_normalize_rejects_zero_vector():
    with pytest.raises(ValueError):
        embed.normalize(np.zeros((1, 3)))


def test_save_writes_vectors_and_word_order(tmp_path):
    vectors = embed.embed_words(WORDS, fake_encoder)
    path = embed.save("fake", WORDS, vectors, output_dir=tmp_path)
    assert np.array_equal(np.load(path), vectors)
    assert json.loads((tmp_path / "word_order.json").read_text()) == ["venal", "venial", "lucid"]


def test_real_word_list_builds_a_text_for_every_word():
    words = embed.load_words()
    texts = [embed.build_text(w) for w in words]
    assert len(texts) == len(words) == 300
    assert all(w["word"] in t for w, t in zip(words, texts))


def test_normalize_rejects_nan_and_infinite_values():
    for bad_value in (np.nan, np.inf):
        with pytest.raises(ValueError, match="NaN"):
            embed.normalize(np.array([[1.0, bad_value, 0.0]]))
