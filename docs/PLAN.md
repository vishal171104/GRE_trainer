# WordOrbit — Project Report

11 Nov 2026 · @vishal

WordOrbit is an AI GRE vocabulary trainer that maps words by meaning in a 3D galaxy and learns which words each student confuses. This report is the plan to build it: what goes in the first version, how the AI works, the build order, and the decisions that are yours to make.

## Overview

**The problem.** GRE vocabulary is hard because many words look or sound alike (sanguine / sanguinary, venal / venial) and many mean almost the same thing (castigate / excoriate / upbraid). Flashcard apps show every student the same cards in the same order, so they don't target the mix-ups that actually cost marks.

**The product.** WordOrbit places every word in a 3D galaxy by meaning, learns which words each student personally confuses, and builds practice around those confusions. Users see synonym families as clusters and look-alike traps as linked stars.

**Who it's for.** GRE test-takers, starting with Indian students preparing for Master's programs abroad. You are the first user, which makes the product decisions easier and gives you an honest origin story.

**Why build it.**

- For admissions: it shows applied ML with real evaluation (embeddings, a confusion model, a spaced-repetition model) and a clear research angle on how people learn.
- For recruiters: it's a full-stack product with 3D graphics, real users and measurable results.
- For you: building it is GRE practice, since your weakest area is hard vocabulary.

Concept prototype: WordOrbit mock-up shows the galaxy and a sample practice round.

## Features

The first version (v1) is the smallest app that is useful every day. Everything else waits until people are using it.

| Feature | What the user gets | Version |
| --- | --- | --- |
| Word galaxy | Rotate and zoom a 3D map of words by meaning; tap a word for its definition, example, synonyms and look-alike traps | v1 |
| Daily practice | Short sessions of sentence-completion and definition questions | v1 |
| Trap pairs | Each wrong answer is logged as a pair; the riskiest pairs are drilled side by side | v1 |
| Smart review timing | Words come back just before you're likely to forget them | v1 |
| Accounts and progress | Sign in with Google; streaks, words mastered, accuracy over time | v1 |
| AI-written questions | Fresh questions and memory hooks for your weakest words, checked before they're shown | v2 |
| Personal galaxy view | Your mastered, learning and trap words coloured on the map | v2 |
| Paid pass | Unlimited practice and full analytics for a one-time fee | v3 |
| Teacher dashboard | Coaching institutes track their students' progress | Later |

## How the AI works

Five AI pieces make the app personal. The first two run once, offline, when the word list is built; the other three run for every user.

### 1. Meaning map (embeddings, offline)

- For each word, embed a short text made of the word, its definition and 2–3 example sentences, using a sentence-embedding model such as all-MiniLM-L6-v2 (which you already used in your RAG bot).
- Embedding the definition, not the bare word, stops spelling from leaking into meaning: sanguine and sanguinary end up far apart.
- Reduce the vectors to 3D with UMAP (cosine distance) for the galaxy. Keep the full vectors for finding synonyms, since 3D positions distort distances.

### 2. Look-alike trap finder (offline)

- Score every word pair on spelling similarity (edit distance, shared prefix) and sound similarity (a phonetic code such as Double Metaphone).
- A pair is a candidate trap when it scores high on spelling or sound but low on meaning similarity.
- Review the top candidates by hand before launch. This curated list is part of what makes the product better than a free flashcard deck.

### 3. Confusion model (per user)

- Every wrong answer is saved as a pair: the word picked and the correct word.
- v1: a simple risk score per pair: misses weighted toward recent ones, boosted when the pair is also a known look-alike.
- v2: once there are enough answers from all users, train a logistic regression that predicts the chance of a wrong answer from pair features (spelling similarity, meaning similarity, word frequency, the user's history). Compare it with the v1 formula on held-out answers. This comparison is your strongest ML talking point.

### 4. Review timing (spaced repetition)

- Use FSRS, the open-source scheduling algorithm behind Anki's modern scheduler, available as a TypeScript library (ts-fsrs).
- It estimates how likely you are to recall each word right now and schedules the next review for when that drops to a target, such as 90%.
- When you miss a trap pair, both words are pulled forward, and the next question uses the confused word as a wrong option.

### 5. Question writer (language model, v2)

- An LLM (for example Llama 3.3 70B via Groq, which you used in your Ludo game) writes new sentence-completion questions and memory hooks for weak words.
- Every generated question passes three checks before anyone sees it: a second model answers it blind and must pick the intended word; no wrong option may also fit the sentence; the sentence must match the word's stored definition.
- Questions are generated in batches and stored, not written live per user. That keeps costs near zero and every question reviewed.

**Choosing wrong options.** Wrong options are picked from the user's own trap words and the target word's meaning-neighbours. That makes every quiz harder in exactly the places this user is weak.

## Architecture

The heavy AI work (embeddings, 3D layout, trap finding) runs once in Python and seeds the database, so the live app stays fast and cheap. The app reads words and questions, logs every answer, and updates review timing and trap scores. The dashed box is v2: the AI question writer only adds questions that pass all three checks.

_(The architecture diagram from the original report is not reproduced in this Markdown export.)_

## Data model

Six tables in Postgres (Supabase) cover v1. The first three are shared content; the last three belong to each user and are protected with row-level security.

| Table | One row per | Main columns |
| --- | --- | --- |
| `words` | word | word, part of speech, definition, examples, difficulty band, 3D position (x, y, z), embedding (pgvector) |
| `word_pairs` | curated pair | word A, word B, type (look-alike or near-synonym), spelling score, sound score, meaning score, explanation |
| `questions` | approved question | target word, sentence with blank, options, explanation, source (hand-written or AI), check results |
| `user_word_state` | user × word | FSRS fields (stability, difficulty, due date, reps, lapses), status (new, learning, mastered) |
| `answers` | answer | user, question, chosen word, correct word, correct or not, response time, timestamp |
| `user_traps` | user × confused pair | picked word, correct word, misses, last missed, risk score |

The `answers` table is the most valuable thing you'll own: it's the training data for the v2 confusion model and the source of every metric on your resume. Log every answer from day one.

## Build plan

The GRE comes first, so the plan assumes 30–45 minutes a day. Each milestone ends with something that works; the rough durations are guides, not deadlines. Build the practice loop before the galaxy: a pretty map with no learning behind it won't keep anyone.

1. **Word list (about 1 week).** Start with 300 high-frequency GRE words. Take definitions from an openly licensed source such as WordNet, rewrite them in plain English, and add 2–3 example sentences each. Never copy a commercial app's flashcards.
2. **Offline pipeline (about 1 week).** A Python script that embeds each word, computes 3D positions with UMAP, scores look-alike pairs and writes everything to the database. You review the top trap candidates by hand.
3. **App skeleton (2–3 days).** Next.js app with Google sign-in through Supabase, deployed to Vercel from the first day so every change is live.
4. **Practice loop (about 2 weeks).** A starter set of one checked question per word, answer logging, and FSRS review timing. This is the point where you start using it for your own GRE prep.
5. **Trap pairs (about 1 week).** Log confused pairs, compute risk scores, and build each quiz's wrong options from the user's traps and meaning-neighbours.
6. **Word galaxy (about 1–2 weeks).** The 3D map in React Three Fiber, reusing what you learned building your portfolio: tap to open a word, trap links, your own words coloured by status.
7. **Private beta (2–3 weeks of use).** 10–20 friends and classmates preparing for the GRE. Fix what confuses them and watch whether they come back.
8. **v2 AI (after the beta).** The LLM question writer with its three checks, and the learned confusion model evaluated against the v1 formula.
9. **Public launch.** Grow the list to about 1,200 words and post in GRE communities.

Milestones 1–4 give you a tool you use daily; 1–7 give you real users. That's enough for a strong resume line, even before v2.

## Decisions you make

These choices are what make WordOrbit your project rather than Claude's. For each one, ask Claude Code to lay out the trade-offs, then decide and write down why in a `DECISIONS.md` file in the repo. That file becomes your interview preparation.

| Decision | Options | Suggested starting point |
| --- | --- | --- |
| Word list size at launch | 300 focused words, or the full 1,000–1,500 | 300, then grow |
| Tech stack | Next.js + Supabase; React + Express + MongoDB; React + FastAPI + Postgres | Next.js + Supabase (realtime, auth and pgvector built in; you've used it before) |
| Embedding model | all-MiniLM-L6-v2, a larger open model, or a paid API | Start with MiniLM; test one larger model and compare synonym quality |
| 3D layout method | UMAP, t-SNE or PCA | UMAP, after comparing all three on how well clusters hold together |
| Question types in v1 | Sentence completion, definition match, text completion with two blanks | Sentence completion + definition match |
| Trap risk formula | Recency-weighted misses, add a look-alike boost, or learn it | Recency-weighted misses + look-alike boost, learned version in v2 |
| FSRS target retention | 85%, 90% or 95% | 90%; weigh review load against forgetting |
| Mobile approach | Responsive web app, installable web app, or native | Responsive web app first |
| App name and look | WordOrbit or your own name; theme and colours | Your call |

## Measuring success

Decide what to measure before launch, so the numbers you quote later are real and you can explain how you got them.

### Product metrics (for recruiters)

| Metric | How it's measured | Why it matters |
| --- | --- | --- |
| Active users | People who answered at least one question in a week | Shows people actually use it |
| Week-1 and week-4 retention | Share of new users still practising after 1 and 4 weeks | The clearest sign the product is useful |
| Questions answered | Count of rows in `answers` | Scale of usage |
| Trap pairs fixed | Pairs missed earlier, then answered correctly 3 times in a row | Direct evidence that the confusion feature works |

### Model evaluation (for admissions)

- **Synonym quality:** for 50 hand-checked words, how many of the 5 nearest neighbours are real synonyms. Compare embedding models with this.
- **Trap finder precision:** of the top 100 candidate pairs, how many you'd accept as real traps.
- **Confusion model:** on held-out answers, compare how well the v1 formula and the v2 model predict a wrong answer (AUC), against a simple baseline such as overall miss rate.
- **Generated questions:** share of LLM questions that pass all three checks, and how many errors a human review still finds in a sample.
- **Learning effect:** accuracy on trap pairs before and after drilling, compared with similar words that weren't drilled. Treat this as an observation, not proof, unless you randomise who gets drilling.

## Launch and monetisation

Launch order: use it yourself, then a private beta, then a free public launch. Turn on payments only once people keep coming back.

- **Where users are:** GRE subreddits, Telegram and WhatsApp prep groups, university seniors who've applied abroad, and your own LinkedIn. A short screen recording of the galaxy will do more than any description.
- **Freemium:** the word galaxy and a daily practice limit are free. Unlimited practice, the full trap-pair engine and progress analytics are paid.
- **Exam pass:** GRE students need the app for 2–3 months, so offer a one-time pass (for example 3 months) instead of a monthly subscription. Test a few price points in rupees.
- **Institutes (later):** a teacher dashboard sold to coaching centres. One deal can be worth hundreds of individual users.
- **Payments:** a gateway such as Razorpay needs KYC and bank details. Set it up only when you're ready to charge.

Running costs for v1 should stay close to zero on free tiers (Vercel, Supabase, Groq), because embeddings are computed once offline and questions are generated in batches.

## Risks and legal basics

| Risk | What to do |
| --- | --- |
| GRE prep eats all your time | Keep to 30–45 minutes a day; skip a day before you skip GRE study |
| Free competitors already exist | Compete on what they lack: personal trap pairs and the meaning map. If those aren't clearly better, don't charge |
| AI-written questions contain mistakes | The three automatic checks, plus a human review of every question in the beta |
| Copyright on word content | Write your own definitions and sentences, or use openly licensed sources and follow their attribution terms. Don't copy commercial flashcard decks |
| "GRE" is a trademark of ETS | Say "for GRE preparation"; don't use their logo or imply you're affiliated |
| User data and privacy | Store only what's needed (email, answers), protect user tables with row-level security, and publish a short privacy policy before launch |
| Low retention after launch | Daily goal, streaks and a reminder; talk to the users who stop and fix what they say |

## Using it on your resume and in interviews

Only put numbers on your resume that come from your own `answers` table and analytics. A template to fill in once the beta has run:

> **WordOrbit, AI GRE Vocabulary Trainer** · Next.js, Supabase, React Three Fiber, sentence embeddings, FSRS · [live link]
>
> - Built an adaptive vocabulary app that maps [N] GRE words in 3D by meaning and drills each user's personal confusions; [N] users answered [N] questions in [N] weeks, with [N]% week-4 retention.
> - Designed a confusion model predicting wrong answers from spelling, meaning and user history (AUC [X] vs [Y] baseline), and an LLM question pipeline whose three automatic checks rejected [N]% of drafts.

**In your statement of purpose:** the story is a real one. You struggled with GRE vocabulary, noticed your mistakes were mostly specific mix-ups rather than unknown words, and built a system to measure and target them. Pair it with the learning-effect results.

**Questions to be ready for:**

- Why embed definitions instead of the words themselves?
- Why UMAP for the galaxy, and what does it distort?
- How does FSRS decide when to show a word again?
- How do you know an AI-written question is correct?
- What would you change with ten times the users?

Your `DECISIONS.md` file should already answer most of these.

## Starting in Claude Code

### Before the first session

- [ ] Create an empty GitHub repo called wordorbit and open it in Claude Code.
- [ ] Create free accounts on Supabase, Vercel and Groq (Groq is only needed from v2).
- [ ] Export this report as Markdown and save it in the repo as `docs/PLAN.md`, so Claude Code can read it.
- [ ] Add an empty `DECISIONS.md` at the repo root.

### First prompt to paste

```text
I'm building WordOrbit, an AI GRE vocabulary trainer. The full plan is in docs/PLAN.md: read it first.

We're starting with milestone 1 (word list) and 2 (offline pipeline). Before writing any code:
1. Propose a folder structure for the repo (Next.js app + a Python pipeline folder).
2. For each decision in the "Decisions you make" table that affects milestones 1-2, give me 2-3 options with trade-offs. I'll choose, and you'll record my choice and my reasoning in DECISIONS.md.
3. Then write a CLAUDE.md for this repo with the stack, conventions and how to run things.

Explain each file you create in 2-3 sentences so I understand it. Don't move to the next milestone until I say so.
```

### Working style that keeps it your project

- Start each session with "plan first, no code yet" and approve the plan before Claude Code writes anything.
- Make the decisions yourself and record why. Ask "what are the alternatives?" whenever a choice is made for you.
- After each milestone, ask Claude Code to quiz you on how the new code works, and explain one part back in your own words.
- Commit after every working step with a clear message, so your GitHub history shows steady progress.
- Run the app yourself every day and use it for your own GRE practice. Your bugs and annoyances are the best product feedback you'll get.
