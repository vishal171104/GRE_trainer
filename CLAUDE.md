# WordOrbit

AI vocabulary trainer for GRE preparation: maps words by meaning in a 3D galaxy and drills each user's personal confusions. The full plan is in `docs/PLAN.md`; choices and their reasons are in `DECISIONS.md`.

## Status

Milestone 1 (word list) is in progress: `data/words.json` holds the first 50 of 300 words. Milestone 2 (offline pipeline) has not started. Do not start a later milestone until Vishal says so.

## Stack

- **Web app** (`web/`, from milestone 3): Next.js + TypeScript, deployed on Vercel. React Three Fiber for the galaxy, `ts-fsrs` for review timing.
- **Database and auth**: Supabase — Postgres with pgvector, Google sign-in, row-level security on per-user tables.
- **Offline pipeline** (`pipeline/`): Python. Embeds words, computes 3D positions, scores look-alike pairs, seeds the database. Runs on a laptop, not in production.
- **Embeddings**: `bge-base-en-v1.5` (main candidate, no query prefix), `all-mpnet-base-v2` and `all-MiniLM-L6-v2` (baseline) are compared on the 50-word synonym check; the winner is used.
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

`data/words.json` is a JSON list with one word per line. Each entry has `word`, `pos` (noun, verb, adjective, adverb), `definition` (plain English, must not use the word itself), `examples` (2–3 sentences that contain the word), `difficulty` (1 common, 2 medium, 3 hard) and `source` (`original`, or the openly licensed source it was adapted from).

Check it after every edit (standard library only, no install needed):

```bash
python pipeline/validate_words.py
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
