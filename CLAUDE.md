# WordOrbit

AI vocabulary trainer for GRE preparation: maps words by meaning in a 3D galaxy and drills each user's personal confusions. The full plan is in `docs/PLAN.md`; choices and their reasons are in `DECISIONS.md`.

## Status

Milestones 1 (word list) and 2 (offline pipeline) are in progress. No application code exists yet. Do not start a later milestone until Vishal says so.

## Stack

- **Web app** (`web/`, from milestone 3): Next.js + TypeScript, deployed on Vercel. React Three Fiber for the galaxy, `ts-fsrs` for review timing.
- **Database and auth**: Supabase — Postgres with pgvector, Google sign-in, row-level security on per-user tables.
- **Offline pipeline** (`pipeline/`): Python. Embeds words, computes 3D positions, scores look-alike pairs, seeds the database. Runs on a laptop, not in production.
- **Embeddings**: a larger open sentence-embedding model (768-dimension class); exact model still to be chosen.
- **3D layout**: UMAP, t-SNE and PCA are compared; UMAP with cosine distance is the default.

## Planned layout

```
docs/PLAN.md          project plan (source of truth for scope)
DECISIONS.md          decision log
data/                 word list source files (words, definitions, examples)
pipeline/             Python offline pipeline + its tests and outputs
supabase/migrations/  SQL schema and RLS policies
web/                  Next.js app (milestone 3 onward)
```

Folders are created when the milestone that needs them starts. Run commands are added here as each piece lands.

## Working conventions

- Plan first: propose the approach and wait for approval before writing code.
- Decisions belong to Vishal. Lay out 2–3 options with trade-offs, let him choose, then record the choice in `DECISIONS.md`. Never fill in the "My reasoning" lines for him.
- Explain each new file in 2–3 sentences when creating it.
- Commit after every working step with a clear message.
- After a milestone, offer to quiz Vishal on how the new code works.

## Content and legal rules

- Definitions and example sentences are original or from openly licensed sources (e.g. WordNet) with attribution. Never copy commercial flashcard decks.
- Say "for GRE preparation"; no ETS logo and no implied affiliation.
- No secrets in the repo: Supabase keys go in untracked `.env` files.
- Log every answer to the `answers` table from day one; only quote metrics that come from real data.
