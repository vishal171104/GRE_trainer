"""Tests for pipeline/compare_models.py, using tiny hand-made vectors."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import compare_models  # noqa: E402
import embed  # noqa: E402

ORDER = ["happy", "glad", "joyful", "sad", "gloomy", "table"]
KEY = {"happy": ["glad", "joyful"], "sad": ["gloomy"]}


def unit(rows):
    return embed.normalize(np.array(rows, dtype=np.float32))


# Happy words point one way, sad words another, 'table' a third.
GOOD = unit([[1, 0, 0], [0.9, 0.1, 0], [0.8, 0.2, 0], [0, 1, 0], [0, 0.9, 0.1], [0, 0, 1]])
# A bad model that puts 'table' next to 'happy' and scatters the rest.
BAD = unit([[1, 0, 0], [0, 1, 0], [0, 0, 1], [0.5, 0.5, 0], [-1, 0, 0], [0.99, 0.01, 0]])


def test_nearest_neighbours_excludes_the_word_itself_and_sorts_by_similarity():
    assert compare_models.nearest_neighbours(GOOD, ORDER, "happy", k=2) == ["glad", "joyful"]


def test_good_model_finds_all_synonyms():
    result = compare_models.score_model(GOOD, ORDER, KEY, k=2)
    assert result["per_word"]["happy"]["hits"] == 2
    assert result["per_word"]["sad"]["found"] == ["gloomy"]
    assert result["recall_at_5"] == 1.0
    assert result["hits_at_5"] == 1.5


def test_recall_is_capped_by_k_when_a_word_has_more_synonyms_than_k():
    result = compare_models.score_model(GOOD, ORDER, {"happy": ["glad", "joyful"]}, k=1)
    assert result["per_word"]["happy"]["recall"] == 1.0


def test_winner_is_the_model_with_higher_recall():
    results = {
        "good": compare_models.score_model(GOOD, ORDER, KEY, k=2),
        "bad": compare_models.score_model(BAD, ORDER, KEY, k=2),
    }
    assert results["bad"]["recall_at_5"] < results["good"]["recall_at_5"]
    assert compare_models.pick_winner(results) == "good"


def test_real_answer_key_only_uses_words_from_the_word_list():
    words = {w["word"] for w in embed.load_words()}
    key = compare_models.load_key()
    assert len(key) == 50
    for target, synonyms in key.items():
        assert target in words and target not in synonyms
        assert synonyms and set(synonyms) <= words


def test_check_vectors_rejects_nan_and_infinite_values():
    bad = GOOD.copy()
    bad[2, 1] = np.nan
    with pytest.raises(ValueError, match="NaN"):
        compare_models.check_vectors(bad)
    bad[2, 1] = np.inf
    with pytest.raises(ValueError, match="NaN"):
        compare_models.check_vectors(bad)


def test_check_vectors_rejects_vectors_that_are_not_unit_length():
    with pytest.raises(ValueError, match="length 1"):
        compare_models.check_vectors(GOOD * 2)


def test_check_vectors_returns_float64_without_changing_the_values():
    checked = compare_models.check_vectors(GOOD)
    assert checked.dtype == np.float64
    assert np.allclose(checked, GOOD)
