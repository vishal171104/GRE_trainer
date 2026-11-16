"""Applies the real migration and seed to a throwaway Postgres database and
checks the row-level security rules.

Skipped unless WORDORBIT_TEST_DATABASE_URL points at a Postgres server with the
pgvector extension available, for example:

    WORDORBIT_TEST_DATABASE_URL=postgresql:///postgres python -m pytest pipeline/tests

The test creates its own database, so it never touches the one in the URL, and
drops it afterwards. auth.users and auth.uid() are stubbed the way Supabase
provides them, and the anon / authenticated roles get Supabase's default grants,
so row-level security is the only thing standing between users.
"""

import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from urllib.parse import urlsplit

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import build_seed  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
MIGRATION = ROOT / "supabase" / "migrations" / "0001_initial_schema.sql"
BASE_URL = os.environ.get("WORDORBIT_TEST_DATABASE_URL")
USER_A = "00000000-0000-0000-0000-00000000000a"
USER_B = "00000000-0000-0000-0000-00000000000b"

pytestmark = pytest.mark.skipif(
    not BASE_URL or not shutil.which("psql"), reason="set WORDORBIT_TEST_DATABASE_URL to run database tests"
)

SUPABASE_STUB = """
create schema if not exists auth;
create table auth.users (id uuid primary key);
create function auth.uid() returns uuid language sql stable as
  $$ select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid $$;
do $$ begin
  if not exists (select from pg_roles where rolname = 'anon') then create role anon nologin; end if;
  if not exists (select from pg_roles where rolname = 'authenticated') then create role authenticated nologin; end if;
end $$;
grant usage on schema auth to anon, authenticated;
grant execute on function auth.uid() to anon, authenticated;
"""

SUPABASE_DEFAULT_GRANTS = """
grant usage on schema public to anon, authenticated;
grant all on all tables in schema public to anon, authenticated;
grant all on all sequences in schema public to anon, authenticated;
"""


def psql(url: str, sql: str) -> str:
    result = subprocess.run(
        ["psql", url, "-X", "-q", "-At", "-v", "ON_ERROR_STOP=1"],
        input=sql, capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


def with_url_database(url: str, name: str) -> str:
    """The same connection URL with a different database name.

    Built by hand: urlunsplit turns 'postgresql:///db' (no host, Unix socket)
    into 'postgresql:/db', which psql no longer reads as a URL.
    """
    parts = urlsplit(url)
    query = f"?{parts.query}" if parts.query else ""
    return f"{parts.scheme}://{parts.netloc}/{name}{query}"


@pytest.fixture(scope="module")
def db():
    name = "wordorbit_test_" + uuid.uuid4().hex[:10]
    psql(BASE_URL, f"create database {name};")
    url = with_url_database(BASE_URL, name)
    try:
        psql(url, SUPABASE_STUB)
        psql(url, MIGRATION.read_text(encoding="utf-8"))
        psql(url, SUPABASE_DEFAULT_GRANTS)
        psql(url, f"insert into auth.users values ('{USER_A}'), ('{USER_B}');")
        yield url
    finally:
        psql(BASE_URL, f"drop database if exists {name} with (force);")


def as_user(url: str, user: str | None, sql: str) -> str:
    """Run SQL as a signed-in user, or as a signed-out visitor when user is None."""
    role = "authenticated" if user else "anon"
    return psql(url, f"set role {role}; select set_config('request.jwt.claim.sub', '{user or ''}', false) \\g /dev/null\n{sql}")


def seeded(url: str) -> None:
    words = [
        {"word": w, "pos": "adjective", "definition": f"Meaning of {w}, it's plain.", "examples": [f"One {w} thing.", f"Two {w} things."], "difficulty": 2, "source": "original"}
        for w in ("venal", "venial", "lucid")
    ]
    positions = {w["word"]: {"x": 0.1 * i, "y": 0.0, "z": -0.1 * i} for i, w in enumerate(words)}
    rng = np.random.default_rng(1)
    vectors = rng.normal(size=(3, build_seed.EMBEDDING_DIM)).astype(np.float32)
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    pairs = [{"word_a": "venial", "word_b": "venal", "spelling": "0.833", "sound": "1.0", "meaning": "0.53"}]
    sql = build_seed.build_seed_sql(words, positions, vectors, pairs)
    psql(url, sql)
    return vectors


def word_id(url: str, word: str) -> str:
    return psql(url, f"select id from words where word = '{word}';")


def test_seed_loads_and_can_run_twice(db):
    vectors = seeded(db)
    seeded(db)  # upsert: no duplicate rows, no errors
    assert psql(db, "select count(*) from words;") == "3"
    assert psql(db, "select count(*) from word_pairs;") == "1"
    first = float(psql(db, "select (embedding::real[])[1] from words where word = 'venal';"))
    assert first == pytest.approx(float(vectors[0][0]), rel=1e-6)
    assert psql(db, "select examples[1] from words where word = 'lucid';") == "One lucid thing."


def test_the_same_pair_in_the_other_order_is_rejected(db):
    seeded(db)
    a, b = word_id(db, "venal"), word_id(db, "venial")
    with pytest.raises(RuntimeError, match="duplicate key"):
        psql(db, f"insert into word_pairs (word_a_id, word_b_id, type) values ({a}, {b}, 'look-alike');")


def test_nearest_neighbour_query_works(db):
    seeded(db)
    nearest = psql(db, "select w2.word from words w1, words w2 where w1.word = 'venal' and w2.id <> w1.id "
                       "order by w1.embedding <=> w2.embedding limit 1;")
    assert nearest in {"venial", "lucid"}


def test_visitors_can_read_content_but_not_change_it(db):
    seeded(db)
    assert as_user(db, None, "select count(*) from words;") == "3"
    with pytest.raises(RuntimeError, match="row-level security"):
        as_user(db, None, "insert into words (word, pos, definition, examples, difficulty, source, x, y, z, embedding) "
                          "select 'zany', pos, definition, examples, difficulty, source, x, y, z, embedding from words limit 1;")
    with pytest.raises(RuntimeError, match="row-level security"):
        as_user(db, USER_A, "insert into word_pairs (word_a_id, word_b_id, type) select 1, 3, 'look-alike';")


def test_users_only_see_and_add_their_own_answers(db):
    seeded(db)
    a, b = word_id(db, "venal"), word_id(db, "venial")
    as_user(db, USER_A, f"insert into answers (chosen_word_id, correct_word_id, response_ms) values ({b}, {a}, 2400), ({a}, {a}, 900);")
    assert as_user(db, USER_A, "select count(*) from answers;") == "2"
    assert as_user(db, USER_A, "select count(*) from answers where is_correct;") == "1"
    assert as_user(db, USER_B, "select count(*) from answers;") == "0"
    assert as_user(db, None, "select count(*) from answers;") == "0"
    with pytest.raises(RuntimeError, match="row-level security"):
        as_user(db, USER_B, f"insert into answers (user_id, chosen_word_id, correct_word_id) values ('{USER_A}', {a}, {a});")


def test_answers_cannot_be_changed_or_deleted_by_users(db):
    seeded(db)
    a = word_id(db, "venal")
    as_user(db, USER_A, f"insert into answers (chosen_word_id, correct_word_id) values ({a}, {a});")
    before = psql(db, f"select count(*) from answers where user_id = '{USER_A}';")
    assert as_user(db, USER_A, "with c as (update answers set response_ms = 1 returning 1) select count(*) from c;") == "0"
    assert as_user(db, USER_A, "with c as (delete from answers returning 1) select count(*) from c;") == "0"
    assert psql(db, f"select count(*) from answers where user_id = '{USER_A}';") == before


def test_review_state_and_traps_are_private(db):
    seeded(db)
    a, b = word_id(db, "venal"), word_id(db, "venial")
    as_user(db, USER_A, f"insert into user_word_state (user_id, word_id) values ('{USER_A}', {a});")
    as_user(db, USER_A, f"insert into user_traps (user_id, picked_word_id, correct_word_id, misses) values ('{USER_A}', {b}, {a}, 1);")
    assert as_user(db, USER_A, "select count(*) from user_word_state;") == "1"
    assert as_user(db, USER_B, "select count(*) from user_word_state;") == "0"
    assert as_user(db, USER_B, "select count(*) from user_traps;") == "0"
    with pytest.raises(RuntimeError, match="row-level security"):
        as_user(db, USER_B, f"insert into user_traps (user_id, picked_word_id, correct_word_id) values ('{USER_A}', {a}, {b});")
