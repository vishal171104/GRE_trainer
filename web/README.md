# WordOrbit web app

Next.js 16 (App Router, TypeScript, Tailwind) with Google sign-in through Supabase. For GRE preparation; not affiliated with ETS.

## Run it locally

```bash
cd web
npm install
cp .env.example .env.local   # then fill in the two values (step 1 below)
npm run dev                  # http://localhost:3000
```

Checks: `npm run lint`, `npx tsc --noEmit`, `npm run build`.

## One-time setup (Vishal)

Dashboard labels change now and then; if one differs, look for the nearest match.

### 1. Supabase project

1. Create a project at supabase.com (free tier). Pick a region near you, such as Mumbai.
2. **SQL Editor**: paste and run `supabase/migrations/0001_initial_schema.sql`.
3. **Project Settings → API Keys**: copy the *publishable* key. **Project Settings → Data API** (or the project's Connect dialog): copy the project URL. Put both in `web/.env.local`.
4. Later, once the trap review is done: run `supabase/seed.sql` in the SQL Editor to load the words.

### 2. Google sign-in

1. In Google Cloud Console, create a project, then **APIs & Services → OAuth consent screen**: set it up as *External*, app name WordOrbit, your email.
2. **Credentials → Create credentials → OAuth client ID → Web application**. Under *Authorized redirect URIs* add `https://<your-project-ref>.supabase.co/auth/v1/callback` (Supabase shows this exact URL on its Google provider page).
3. In Supabase, **Authentication → Sign In / Providers → Google**: turn it on and paste the client ID and secret.
4. In Supabase, **Authentication → URL Configuration**: set *Site URL* to your Vercel address (step 3) and add these *Redirect URLs*: `http://localhost:3000/auth/callback` and `https://<your-vercel-domain>/auth/callback`.

### 3. Vercel

1. **Add New → Project**, import `vishal171104/GRE_trainer`, and set **Root Directory** to `web`.
2. Add the two environment variables from `.env.example` with your real values, then deploy.
3. Add the Vercel URL to Supabase's URL Configuration (step 2.4). Every merge to `main` then redeploys automatically.

The client secret from Google goes only into Supabase. Nothing secret goes in the repo or in Vercel: the two `NEXT_PUBLIC_` values are public by design, and row-level security protects the data.
