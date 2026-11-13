# WordOrbit

AI vocabulary trainer for GRE preparation: maps words by meaning in a 3D galaxy and drills each user's personal confusions. The full plan is in `docs/PLAN.md`; choices and their reasons are in `DECISIONS.md`.

## Status

Milestone 1 (word list): `data/words.json` holds all 300 words, AI-drafted. Still open: Vishal's dictionary check of every definition. Milestone 2 (offline pipeline) is in progress, in five steps (see `DECISIONS.md`, entry 10). Steps 1 (`embed.py`) and 2 (`compare_models.py`) are done and the model is chosen: mpnet (`DECISIONS.md`, entry 11). Step 3 (`layout.py`) has been run: neighbour preservation UMAP 0.449, t-SNE 0.460, PCA 0.185, and UMAP is kept (`DECISIONS.md`, entry 4). Step 4 (`find_traps.py`) is written and tested, but not yet run on the real embeddings: it needs `pipeline/output` committed to the repo. The synonym answer key in `data/eval/synonym_key.json` is frozen. Do not start a later milestone until Vishal says so.

## Stack

- **Web app** (`web/`, from milestone 3): Next.js + TypeScript, deployed on Vercel. React Three Fiber for the galaxy, `ts-fsrs` for review timing.
- **Database and auth**: Supabase — Postgres with pgvector, Google sign-in, row-level security on per-user tables.
- **Offline pipeline** (`pipeline/`): Python. Embeds words, computes 3D positions, scores look-alike pairs, seeds the database. Runs on a laptop, not in production.
- **Embeddings**: `all-mpnet-base-v2` (chosen: 76.5% recall@5 on the synonym key, ahead of `bge-base-en-v1.5` 51.5% and `all-MiniLM-L6-v2` 39.6%).
- **3D layout**: UMAP, t-SNE and PCA are compared by neighbour preservation with a fixed seed; UMAP with cosine distance is the default.

## Planned layout

```
docs/PLAN.md          project plan (source of truth for scope)
DECISIONS.md          decision log
data/                 word list source files (words, definitions, examples)
data/eval/            hand-checked evaluation keys (50-word synonym answer key)
pipeline/             Python offline pipeline + its tests and outputs
supabase/migrations/  SQL schema and RLS policies
web/                  Next.js app (milestone 3 onward)
```

Folders are created when the milestone that needs them starts. Run commands are added here as each piece lands.

## Word list

`data/words.json` is a JSON list with one word per line. Each entry has:

- `word`: a single lowercase word.
- `pos`: noun, verb, adjective or adverb.
- `definition`: one line of 6–14 words in plain English, never using the word itself or a harder word.
- `examples`: 2–3 sentences of 10–20 words that contain the word and make its meaning guessable from context.
- `difficulty`: 1 newspaper-level, 2 educated but uncommon, 3 rare or easily confused. Both words of a look-alike pair get 3.
- `source`: `original`, or the openly licensed source it was adapted from.

New words follow the mix in `DECISIONS.md`: about 60% high-frequency words, 25% synonym families, 15% trap pairs. Definitions are AI-drafted; Vishal checks each against a real dictionary before launch.

Check it after every edit (standard library only, no install needed):

```bash
python pipeline/validate_words.py
```

## Offline pipeline

The cloud session cannot reach Hugging Face, so Claude tests with fake vectors and Vishal runs the real models on his laptop, then commits `pipeline/output/`.

```bash
pip install -r pipeline/requirements.txt
python -m pytest pipeline/tests      # fast, downloads nothing
python pipeline/embed.py             # downloads three models, writes pipeline/output/
python pipeline/compare_models.py    # scores each model against the synonym answer key
python pipeline/layout.py            # UMAP / t-SNE / PCA comparison, writes positions.json
python pipeline/find_traps.py        # ranks look-alike trap candidates into trap_candidates.csv
```

## Working conventions

- Plan first: propose the approach and wait for approval before writing code.
- Decisions belong to Vishal. Lay out 2–3 options with trade-offs, let him choose, then record the choice in `DECISIONS.md`. Never fill in the "My reasoning" lines for him.
- Explain each new file in 2–3 sentences when creating it.
- Commit after every working step with a clear message.
- Every push goes with a pull request: Claude pushes to its feature branch, opens (or updates) a PR into `main` and requests review from `vishal171104`. Vishal reviews and merges; Claude never merges or pushes to `main`. After opening a PR, Claude subscribes to its activity without asking, to respond to review comments and fix CI failures.
- After a milestone, offer to quiz Vishal on how the new code works.

## Content and legal rules

- Definitions and example sentences are original or from openly licensed sources (e.g. WordNet) with attribution. Never copy commercial flashcard decks.
- Say "for GRE preparation"; no ETS logo and no implied affiliation.
- The synonym answer key is written and committed before any embedding model is run. Never edit it after seeing model output.
- No secrets in the repo: Supabase keys go in `.env` files, which are listed in `.gitignore`.
- Log every answer to the `answers` table from day one; only quote metrics that come from real data.
