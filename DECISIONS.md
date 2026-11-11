# Decisions

A running log of the choices made while building WordOrbit and the reasoning behind each. See `docs/PLAN.md` ("Decisions you make") for the open list.

Each entry: what was chosen, what the alternatives were, and why. "My reasoning" is written by Vishal, in his own words.

## 1. Word list size at launch — 300 focused words

- **Date:** 2026-11-11
- **Chosen:** 300 high-frequency GRE words, grown later (target about 1,200 at public launch).
- **Alternatives:** ~600 words (denser galaxy, double the content work); the full 1,000–1,500 (complete coverage, but weeks of writing before the practice loop exists and no realistic hand-review).
- **Trade-off accepted:** a sparser galaxy and fewer look-alike pairs at first, in exchange for every definition, example and trap pair being hand-checked.
- **My reasoning:** _TODO (Vishal)_

## 2. Tech stack — Next.js + Supabase

- **Date:** 2026-11-11
- **Chosen:** Next.js app on Vercel; Supabase for Postgres (with pgvector), Google sign-in and row-level security. The offline pipeline is Python and writes to the same database.
- **Alternatives:** React + FastAPI + Postgres (one language for pipeline and API, but auth and two services to build and host); React + Express + MongoDB (familiar, but a poor fit for relational pair/answer data and no built-in vector search).
- **Trade-off accepted:** some vendor lock-in, and RLS policies need care.
- **My reasoning:** _TODO (Vishal)_

## 3. Embedding model — a larger open model

- **Date:** 2026-11-11
- **Chosen:** a larger open sentence-embedding model (768-dimension class, e.g. `all-mpnet-base-v2` or `bge-base-en-v1.5`) rather than starting from all-MiniLM-L6-v2.
- **Alternatives:** all-MiniLM-L6-v2 first, then compare (smaller, faster, familiar); a paid embedding API (top quality, but a key, an external dependency and less reproducible).
- **Trade-off accepted:** slower and larger than MiniLM (still fine for 300 words on a laptop), and vectors are 768 dimensions in pgvector instead of 384.
- **Still open:** which specific model; and whether to also run MiniLM once as a baseline for the 50-word synonym-quality check in the plan.
- **My reasoning:** _TODO (Vishal)_

## 4. 3D layout method — compare UMAP, t-SNE and PCA; default to UMAP

- **Date:** 2026-11-11
- **Chosen:** run all three once, score how well synonym clusters hold together, then pick. UMAP (cosine distance) is the expected winner and the default.
- **Alternatives:** UMAP only (less work, no evidence for the choice); PCA only (deterministic and simple, but clusters smear together in 3 linear components).
- **Trade-off accepted:** a bit more pipeline work in milestone 2 for a measured answer to "why UMAP?".
- **Still open:** the cluster-quality metric used for the comparison.
- **My reasoning:** _TODO (Vishal)_
