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

## 5. Word entry style

- **Date:** 2026-11-11
- **Chosen:**
  - Definition: one line of about 6–14 words, in plain English, never using the word itself or a harder word. Good: "Castigate: to scold someone severely." Bad: "Castigate: to subject to castigation."
  - Example sentences: about 10–20 words each, written so the meaning can be guessed from context. A sentence where any adjective would fit teaches nothing.
  - Every definition is checked by me against a real dictionary (Merriam-Webster or Oxford Learner's) before launch.
- **Enforced by:** `pipeline/validate_words.py` checks the word counts and that a definition doesn't use its own word. "No harder word" and "guessable from context" can only be checked by reading.
- **My reasoning:** Accuracy is the biggest risk. The entries are drafted by an AI, and a wrong definition teaches every user the wrong meaning. Checking them is also GRE study for me.

## 6. Difficulty bands

- **Date:** 2026-11-11
- **Chosen:**
  - **1** — you'd see it in a newspaper (terse, lethargic).
  - **2** — educated but uncommon (castigate, laconic).
  - **3** — rare or easily confused (enervate, venial, sanguinary).
- **How "easily confused" is applied:** both words of a look-alike pair with different meanings get band 3, even when one of them is common on its own (ingenious / ingenuous, aesthetic / ascetic).
- **Later:** once real users answer questions, replace these guessed bands with measured error rates from the `answers` table.
- **My reasoning:** Bands are only consistent if they follow a written rule.

## 7. Mix of the remaining 250 words

- **Date:** 2026-11-11
- **Chosen:** roughly 60% words that appear often across GRE prep materials, 25% synonym families (the galaxy's clusters), 15% trap pairs (the app's special feature).
- **Alternatives:** keep choosing only trap pairs and synonym families, as in the first 50.
- **Word selection:** my own judgment, words met in official ETS practice questions, and comparing several published high-frequency lists to decide which words to include. Definitions and example sentences are never copied from those lists.
- **My reasoning:** The GRE tests a broad mix, so the list shouldn't be only traps and families.

## 8. Where the embedding models run — on my laptop

- **Date:** 2026-11-13
- **Chosen:** Claude writes the pipeline scripts and tests them in its cloud session with small fake vectors; I run the real models on my laptop and commit the output.
- **Alternatives:** allow `huggingface.co` in the cloud environment's network settings so Claude runs the models there and commits the results.
- **Trade-off accepted:** one extra manual step for me each time the pipeline changes, in exchange for seeing the results first-hand and matching the plan ("the pipeline runs on a laptop").
- **My reasoning:** _TODO (Vishal) — chosen on Claude's recommendation_

## 9. Where pipeline output goes — files in the repo first

- **Date:** 2026-11-13
- **Chosen:** vectors, 3D positions, trap candidates and a SQL seed file are written to `pipeline/output/` and committed. Nothing is written to Supabase until milestone 3.
- **Alternatives:** write straight into Supabase from the pipeline, which needs the project and keys set up now.
- **Trade-off accepted:** a few binary files of about 1 MB each in git, and a separate seeding step later.
- **My reasoning:** _TODO (Vishal) — chosen on Claude's recommendation_

## 10. Pipeline plan for milestone 2

- **Date:** 2026-11-13
- **Chosen:** five steps, one script and one pull request each: (1) embed, (2) compare models against the synonym key, (3) 3D layout comparison, (4) trap finder, (5) database schema and seed file.
