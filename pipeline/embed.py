"""Step 1 of the offline pipeline: turn every word into an embedding vector.

Usage:  python pipeline/embed.py                 # all three models
        python pipeline/embed.py --models minilm # just one
        python pipeline/embed.py --models mpnet --text definition masked

--text chooses what is embedded for each word (default: full):
  full        the word, its definition and its examples
  definition  the definition only
  masked      the definition and examples, with the word replaced by ___
The last two never show the model the word's spelling, which tests whether
spelling leaks into the meaning map (DECISIONS.md, entry 13). They are saved
as embeddings_<model>-<text>.npy, so compare_models.py scores them alongside.

For each model this writes pipeline/output/embeddings_<name>.npy, a
(number of words x dimensions) array of unit-length vectors, plus
pipeline/output/word_order.json, which says which row belongs to which word.

The models are downloaded from Hugging Face the first time they are used.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Callable

import numpy as np

from validate_words import stem

ROOT = Path(__file__).resolve().parent.parent
WORDS_PATH = ROOT / "data" / "words.json"
KEY_PATH = ROOT / "data" / "eval" / "synonym_key.json"
OUTPUT_DIR = ROOT / "pipeline" / "output"

# Short name -> Hugging Face model id. See DECISIONS.md, entry 3.
MODELS = {
    "bge-base": "BAAI/bge-base-en-v1.5",  # main candidate, used without a query prefix
    "mpnet": "sentence-transformers/all-mpnet-base-v2",  # second candidate
    "minilm": "sentence-transformers/all-MiniLM-L6-v2",  # baseline
}

TEXT_MODES = ("full", "definition", "masked")

# An encoder takes a list of texts and returns one vector per text.
Encoder = Callable[[list[str]], np.ndarray]


def mask_word(word: str, text: str) -> str:
    """Replace the word and its inflections (castigate, castigated, castigating) with ___."""
    return re.sub(r"\b" + re.escape(stem(word)) + r"\w*", "___", text, flags=re.IGNORECASE)


def build_text(entry: dict, mode: str = "full") -> str:
    """The text that gets embedded for one word.

    We embed the definition and examples, not the bare word, so that words
    are placed by meaning: 'sanguine' and 'sanguinary' look alike but their
    definitions do not. In 'full' mode the word itself is still in the text;
    'definition' and 'masked' leave its spelling out entirely.
    """
    if mode == "full":
        return f"{entry['word']}: {entry['definition']} " + " ".join(entry["examples"])
    if mode == "definition":
        return entry["definition"]
    if mode == "masked":
        return entry["definition"] + " " + " ".join(mask_word(entry["word"], e) for e in entry["examples"])
    raise ValueError(f"unknown text mode {mode!r}; expected one of {TEXT_MODES}")


def output_name(model: str, mode: str) -> str:
    """'mpnet' for the default text, 'mpnet-masked' for the others."""
    return model if mode == "full" else f"{model}-{mode}"


def load_words(path: Path = WORDS_PATH) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize(vectors: np.ndarray) -> np.ndarray:
    """Scale every row to length 1, so a dot product equals cosine similarity."""
    if not np.isfinite(vectors).all():
        raise ValueError("an embedding contains NaN or infinite values")
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    if np.any(norms == 0):
        raise ValueError("an embedding came back as all zeros")
    return vectors / norms


def embed_words(words: list[dict], encoder: Encoder, mode: str = "full") -> np.ndarray:
    """Embed every word with the given encoder and return unit-length float32 vectors."""
    texts = [build_text(entry, mode) for entry in words]
    vectors = np.asarray(encoder(texts), dtype=np.float32)
    if vectors.ndim != 2 or vectors.shape[0] != len(words):
        raise ValueError(f"expected {len(words)} vectors, got array of shape {vectors.shape}")
    return normalize(vectors)


def load_encoder(model_id: str) -> Encoder:
    """Load a sentence-embedding model. Imported here so tests don't need the library."""
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_id)
    return lambda texts: model.encode(texts, show_progress_bar=True)


def save(name: str, words: list[dict], vectors: np.ndarray, output_dir: Path = OUTPUT_DIR) -> Path:
    """Write the vectors for one model, and the word order they are in."""
    output_dir.mkdir(parents=True, exist_ok=True)
    order = [entry["word"] for entry in words]
    (output_dir / "word_order.json").write_text(json.dumps(order, indent=0) + "\n", encoding="utf-8")
    path = output_dir / f"embeddings_{name}.npy"
    np.save(path, vectors)
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Embed the word list with each model.")
    parser.add_argument("--models", nargs="+", choices=sorted(MODELS), default=sorted(MODELS))
    parser.add_argument("--text", nargs="+", choices=TEXT_MODES, default=["full"], help="what to embed for each word")
    args = parser.parse_args()

    # Rule from DECISIONS.md: the answer key must exist before any model is run.
    if not KEY_PATH.exists():
        print(f"Refusing to run: {KEY_PATH} is missing. Commit the answer key first.")
        return 1

    words = load_words()
    for name in args.models:
        encoder = load_encoder(MODELS[name])
        for mode in args.text:
            print(f"Embedding {len(words)} words with {MODELS[name]} (text: {mode}) ...")
            vectors = embed_words(words, encoder, mode)
            path = save(output_name(name, mode), words, vectors)
            print(f"  saved {vectors.shape[0]} x {vectors.shape[1]} vectors to {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
