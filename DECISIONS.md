# Decisions

A running log of the choices made while building WordOrbit and the reasoning behind each. See `docs/PLAN.md` ("Decisions you make") for the open list.

Each entry: what was chosen, what the alternatives were, and why. "My reasoning" is written by Vishal, in his own words.

## 1. Word list size at launch — 300 focused words

- **Date:** 2026-11-11
- **Chosen:** 300 high-frequency GRE words, grown later (target about 1,200 at public launch).
- **Alternatives:** ~600 words (denser galaxy, double the content work); the full 1,000–1,500 (complete coverage, but weeks of writing before the practice loop exists and no realistic hand-review).
- **Trade-off accepted:** a sparser galaxy and fewer look-alike pairs at first, in exchange for every definition, example and trap pair being hand-checked.
- **My reasoning:** Starting with 300 high-frequency words lets me finish the whole loop (pipeline, practice, review timing) and use it for my own GRE prep quickly. I'll grow to about 1,200 once the core works and users find it useful.

## 2. Tech stack — Next.js + Supabase

- **Date:** 2026-11-11
- **Chosen:** Next.js app on Vercel; Supabase for Postgres (with pgvector), Google sign-in and row-level security. The offline pipeline is Python and writes to the same database.
- **Alternatives:** React + FastAPI + Postgres (one language for pipeline and API, but auth and two services to build and host); React + Express + MongoDB (familiar, but a poor fit for relational pair/answer data and no built-in vector search).
- **Trade-off accepted:** some vendor lock-in, and RLS policies need care.
- **My reasoning:** Supabase gives me Postgres with pgvector, Google sign-in and row-level security on a free tier, and I've used it before, so I spend time on the product instead of setup. It's relational, which suits word pairs and answer logs. Vercel's free plan is non-commercial, so I'll move hosting when I start charging.

## 3. Embedding model — a larger open model

- **Date:** 2026-11-11
- **Chosen:** a larger open sentence-embedding model (768-dimension class, e.g. `all-mpnet-base-v2` or `bge-base-en-v1.5`) rather than starting from all-MiniLM-L6-v2.
- **Alternatives:** all-MiniLM-L6-v2 first, then compare (smaller, faster, familiar); a paid embedding API (top quality, but a key, an external dependency and less reproducible).
- **Trade-off accepted:** slower and larger than MiniLM (still fine for 300 words on a laptop), and vectors are 768 dimensions in pgvector instead of 384.
- **Candidates (decided 2026-11-11):** `bge-base-en-v1.5` is the main candidate; `all-mpnet-base-v2` is a second candidate; `all-MiniLM-L6-v2` is the baseline. All three are run and compared on the 50-word synonym-quality check, and the winner is recorded here. No query prefix for bge, because definitions are compared with definitions, not searched.
- **Evaluation rule:** the 50-word synonym answer key is built and committed *before* any model is run (by hand, or from WordNet synonym sets checked by me), so the key can't be biased toward one model's output.
- **My reasoning:** Synonym families depend on fine shades of meaning, so a larger model should help. Embeddings are computed once offline, so model size doesn't affect the app. I'll choose by measured synonym quality, not by assumption.

## 4. 3D layout method — compare UMAP, t-SNE and PCA; default to UMAP

- **Date:** 2026-11-11
- **Chosen:** run all three once, score how well synonym clusters hold together, then pick. UMAP (cosine distance) is the expected winner and the default.
- **Alternatives:** UMAP only (less work, no evidence for the choice); PCA only (deterministic and simple, but clusters smear together in 3 linear components).
- **Trade-off accepted:** a bit more pipeline work in milestone 2 for a measured answer to "why UMAP?".
- **Metric:** a neighbour-preservation score (how many of a word's nearest neighbours in the full embedding stay its neighbours in 3D), computed with a fixed random seed.
- **My reasoning:** UMAP keeps synonym clusters almost as tight as t-SNE and can place new words into an existing map, so the galaxy stays stable when the list grows from 300 to 1,200. PCA blurs clusters together. I'll confirm with a neighbour-preservation score and a fixed seed.
