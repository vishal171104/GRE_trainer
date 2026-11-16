"""Unit tests for pipeline/build_seed.py. No database needed."""

import csv
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import build_seed  # noqa: E402

WORDS = [
    {"word": "venal", "pos": "adjective", "definition": "Open to bribery.", "examples": ["A venal clerk.", "Venal judges."], "difficulty": 3, "source": "original"},
    {"word": "venial", "pos": "adjective", "definition": "Easily forgiven.", "examples": ["A venial fault.", "Venial sins."], "difficulty": 3, "source": "original"},
]
POSITIONS = {"venal": {"x": 0.1, "y": -0.2, "z": 0.3}, "venial": {"x": -1.0, "y": 1.0, "z": 0.0}}


def vectors(n=2):
    rng = np.random.default_rng(0)
    v = rng.normal(size=(n, build_seed.EMBEDDING_DIM)).astype(np.float32)
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def write_csv(path, marks):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["rank", "word_a", "word_b", "spelling", "sound", "meaning", "trap_score", "accept"])
        for i, mark in enumerate(marks, start=1):
            writer.writerow([i, "venal", "venial", "0.833", "1.000", "0.530", "1.000", mark])
    return path


def test_sql_text_doubles_single_quotes():
    assert build_seed.sql_text("the company's future") == "'the company''s future'"


def test_sql_vector_keeps_float32_values_exact():
    v = vectors(1)[0]
    literal = build_seed.sql_vector(v)
    parsed = np.array([float(x) for x in literal.strip("'[]").split(",")], dtype=np.float32)
    assert np.array_equal(parsed, v)


def test_sql_vector_rejects_nan():
    with pytest.raises(ValueError):
        build_seed.sql_vector(np.array([0.1, np.nan]))


def test_accepted_pairs_keeps_yes_and_skips_no_and_blank(tmp_path):
    rows = build_seed.accepted_pairs(write_csv(tmp_path / "t.csv", ["y", "n", "", "YES", " Yes ", "no"]))
    assert [r["rank"] for r in rows] == ["1", "4", "5"]


def test_accepted_pairs_rejects_a_typo(tmp_path):
    with pytest.raises(ValueError, match="line 3"):
        build_seed.accepted_pairs(write_csv(tmp_path / "t.csv", ["y", "maybe"]))


def test_accepted_pairs_with_no_csv_is_empty(tmp_path):
    assert build_seed.accepted_pairs(tmp_path / "missing.csv") == []


def test_seed_sql_upserts_words_and_pairs():
    pairs = [{"word_a": "venal", "word_b": "venial", "spelling": "0.833", "sound": "1.000", "meaning": "0.530"}]
    sql = build_seed.build_seed_sql(WORDS, POSITIONS, vectors(), pairs)
    assert sql.startswith("-- Generated") and sql.rstrip().endswith("COMMIT;")
    assert "ON CONFLICT (word) DO UPDATE" in sql
    assert "ON CONFLICT (least(word_a_id, word_b_id), greatest(word_a_id, word_b_id), type)" in sql
    statements = "\n".join(line for line in sql.upper().splitlines() if not line.startswith("--"))
    assert "DELETE FROM" not in statements and "TRUNCATE" not in statements


def test_seed_sql_without_pairs_has_no_pair_insert():
    sql = build_seed.build_seed_sql(WORDS, POSITIONS, vectors(), [])
    assert "word_pairs" not in sql


@pytest.mark.parametrize(
    "positions, vecs, pairs, message",
    [
        (POSITIONS, np.zeros((2, 5), dtype=np.float32), [], "shape"),
        ({"venal": POSITIONS["venal"]}, None, [], "no 3D position"),
        (POSITIONS, None, [{"word_a": "venal", "word_b": "ghost"}], "unknown word"),
    ],
)
def test_seed_sql_refuses_inconsistent_inputs(positions, vecs, pairs, message):
    with pytest.raises(ValueError, match=message):
        build_seed.build_seed_sql(WORDS, positions, vectors() if vecs is None else vecs, pairs)
