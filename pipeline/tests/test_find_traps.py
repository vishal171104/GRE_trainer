"""Tests for pipeline/find_traps.py. The look-alike tests need only the word list."""

import csv
import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import embed  # noqa: E402
import find_traps  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent


def test_edit_similarity_known_values():
    assert find_traps.edit_similarity("venal", "venial") == pytest.approx(5 / 6)
    assert find_traps.edit_similarity("same", "same") == 1.0
    assert find_traps.edit_similarity("abc", "xyz") == 0.0


def test_prefix_similarity_is_the_shared_prefix_over_the_longer_word():
    assert find_traps.prefix_similarity("sanguine", "sanguinary") == pytest.approx(0.7)
    assert find_traps.prefix_similarity("abc", "xyz") == 0.0


def test_homophones_get_a_perfect_sound_score():
    pairs = [("discreet", "discrete"), ("venal", "venial"), ("exalt", "exult")]
    for a, b in pairs:
        assert find_traps.sound_score(find_traps.phonetic_code(a), find_traps.phonetic_code(b)) == 1.0


def test_trap_score_prefers_look_alikes_that_mean_different_things():
    unrelated = find_traps.trap_score(lookalike=0.9, meaning=0.1)
    related = find_traps.trap_score(lookalike=0.9, meaning=0.8)
    assert unrelated > related
    assert find_traps.trap_score(0.9, -0.3) == 0.9  # negative similarity is not a bonus


def test_select_candidates_filters_sorts_and_limits():
    rows = [
        {"word_a": "a", "word_b": "b", "lookalike": 0.9, "trap_score": 0.5},
        {"word_a": "c", "word_b": "d", "lookalike": 0.5, "trap_score": 0.9},  # below the floor
        {"word_a": "e", "word_b": "f", "lookalike": 0.7, "trap_score": 0.6},
        {"word_a": "g", "word_b": "h", "lookalike": 0.8, "trap_score": 0.4},
    ]
    picked = find_traps.select_candidates(rows, top=2, min_lookalike=0.6)
    assert [(r["word_a"], r["word_b"]) for r in picked] == [("e", "f"), ("a", "b")]


def test_score_pairs_uses_meaning_from_vectors():
    words = ["venal", "venial", "lucid"]
    vectors = embed.normalize(np.array([[1.0, 0, 0], [0.0, 1, 0], [1.0, 0.1, 0]], dtype=np.float32))
    rows = {(r["word_a"], r["word_b"]): r for r in find_traps.score_pairs(words, vectors)}
    assert len(rows) == 3
    venal_venial = rows[("venal", "venial")]
    assert venal_venial["lookalike"] > 0.8 and venal_venial["meaning"] == pytest.approx(0.0, abs=1e-6)
    assert venal_venial["trap_score"] == pytest.approx(venal_venial["lookalike"])


def test_write_outputs_gives_a_csv_with_an_empty_accept_column(tmp_path):
    candidates = find_traps.select_candidates(
        find_traps.score_pairs(["venal", "venial", "discreet", "discrete"]), top=10, min_lookalike=0.6
    )
    csv_path, json_path = find_traps.write_outputs(candidates, tmp_path)
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    # Only the two real look-alike pairs pass the 0.6 floor.
    assert [r["rank"] for r in rows] == ["1", "2"]
    assert {frozenset((r["word_a"], r["word_b"])) for r in rows} == {
        frozenset(("venal", "venial")),
        frozenset(("discreet", "discrete")),
    }
    assert all(r["accept"] == "" and r["meaning"] == "" for r in rows)
    assert len(json.loads(json_path.read_text())) == 2


def test_expected_traps_file_is_well_formed():
    words = {e["word"] for e in embed.load_words()}
    pairs = json.loads(find_traps.EXPECTED_PATH.read_text(encoding="utf-8"))["pairs"]
    assert len(pairs) == len({frozenset(p) for p in pairs})
    for a, b in pairs:
        assert a != b and a in words and b in words


def test_spelling_and_sound_alone_find_most_of_the_expected_traps():
    """Smoke test on the real word list. Measured at write time: 26 of 34 in the top 100."""
    words = [e["word"] for e in embed.load_words()]
    expected = json.loads(find_traps.EXPECTED_PATH.read_text(encoding="utf-8"))["pairs"]
    candidates = find_traps.select_candidates(find_traps.score_pairs(words), top=100)
    found, missing = find_traps.expected_coverage(candidates, expected)
    assert len(found) >= 24, f"missing: {missing}"
