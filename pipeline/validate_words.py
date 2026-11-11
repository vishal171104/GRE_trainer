"""Check data/words.json for mistakes before anything else uses it.

Usage:  python pipeline/validate_words.py [path/to/words.json]

Exits with status 1 if any problem is found, so it can run in CI later.
Uses only the Python standard library.
"""

import json
import sys
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "words.json"

REQUIRED_FIELDS = ("word", "pos", "definition", "examples", "difficulty", "source")
ALLOWED_POS = {"noun", "verb", "adjective", "adverb"}
ALLOWED_DIFFICULTY = {1, 2, 3}  # 1 = common, 2 = medium, 3 = hard
MIN_EXAMPLES, MAX_EXAMPLES = 2, 3
DEFINITION_WORDS = (6, 14)  # style rule: one plain-English line
EXAMPLE_WORDS = (10, 20)  # long enough for context to hint at the meaning


def stem(word: str) -> str:
    """Crude stem so 'castigate' matches 'castigated' and 'anomaly' matches 'anomalies'."""
    return word[:-1] if word[-1] in "ey" else word


def check_entry(entry: dict) -> list[str]:
    """Return a list of problems with one word entry (empty if it is fine)."""
    problems = []
    for field in REQUIRED_FIELDS:
        if field not in entry:
            problems.append(f"missing field '{field}'")
    if problems:
        return problems

    word = entry["word"]
    if not isinstance(word, str) or not word.isalpha() or word != word.lower():
        problems.append("word must be a single lowercase word")
        return problems
    if entry["pos"] not in ALLOWED_POS:
        problems.append(f"pos '{entry['pos']}' is not one of {sorted(ALLOWED_POS)}")
    if entry["difficulty"] not in ALLOWED_DIFFICULTY:
        problems.append("difficulty must be 1, 2 or 3")
    if not isinstance(entry["source"], str) or not entry["source"].strip():
        problems.append("source must say where the content came from")

    definition = entry["definition"]
    if not isinstance(definition, str):
        problems.append("definition must be text")
    elif not DEFINITION_WORDS[0] <= len(definition.split()) <= DEFINITION_WORDS[1]:
        problems.append(
            f"definition has {len(definition.split())} words, expected "
            f"{DEFINITION_WORDS[0]}-{DEFINITION_WORDS[1]}"
        )
    elif stem(word) in definition.lower():
        problems.append("definition uses the word it is defining")

    examples = entry["examples"]
    if not isinstance(examples, list) or not MIN_EXAMPLES <= len(examples) <= MAX_EXAMPLES:
        problems.append(f"needs {MIN_EXAMPLES}-{MAX_EXAMPLES} examples")
    else:
        for i, example in enumerate(examples, start=1):
            if not isinstance(example, str) or stem(word) not in example.lower():
                problems.append(f"example {i} does not contain the word")
            elif not EXAMPLE_WORDS[0] <= len(example.split()) <= EXAMPLE_WORDS[1]:
                problems.append(
                    f"example {i} has {len(example.split())} words, expected "
                    f"{EXAMPLE_WORDS[0]}-{EXAMPLE_WORDS[1]}"
                )
    return problems


def validate(path: Path) -> list[str]:
    """Return every problem found in the word list file."""
    entries = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(entries, list):
        return ["file must contain a JSON list of word entries"]

    errors = []
    seen = set()
    for index, entry in enumerate(entries, start=1):
        label = entry.get("word", f"entry {index}") if isinstance(entry, dict) else f"entry {index}"
        if not isinstance(entry, dict):
            errors.append(f"{label}: must be a JSON object")
            continue
        for problem in check_entry(entry):
            errors.append(f"{label}: {problem}")
        if label in seen:
            errors.append(f"{label}: duplicate word")
        seen.add(label)
    return errors


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PATH
    entries = json.loads(path.read_text(encoding="utf-8"))
    errors = validate(path)
    for error in errors:
        print(f"ERROR  {error}")
    print(f"{len(entries)} words checked, {len(errors)} problem(s) found.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
