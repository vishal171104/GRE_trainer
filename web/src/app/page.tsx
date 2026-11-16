import Link from "next/link";
import { Suspense } from "react";
import { supabaseEnv } from "@/lib/supabase/env";
import { createClient } from "@/lib/supabase/server";
import { signOut } from "./actions";

// The title and footer are static. The parts that read the session cookie
// stream in behind <Suspense>, as Next.js requires with Cache Components on.

async function Account() {
  const supabase = await createClient();
  const user = supabase ? (await supabase.auth.getUser()).data.user : null;
  if (!user) {
    return (
      <div className="mt-6 flex items-center justify-between gap-4">
        <p>You are not signed in.</p>
        <Link href="/login" className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white">Sign in</Link>
      </div>
    );
  }
  const name = (user.user_metadata?.full_name as string | undefined) ?? user.email;
  return (
    <div className="mt-6 flex items-center justify-between gap-4">
      <p>Signed in as {name}.</p>
      <form action={signOut}>
        <button className="text-sm text-gray-600 underline">Sign out</button>
      </form>
    </div>
  );
}

// Words are public, so this works signed in or not: it proves the app reaches the database.
async function WordSample() {
  const supabase = await createClient();
  if (!supabase) return null;
  const { data: words, error } = await supabase.from("words").select("word, definition").order("word").limit(5);
  if (error) return <p className="mt-2 text-sm text-red-600">Could not read words: {error.message}</p>;
  if (!words.length) return <p className="mt-2 text-sm text-gray-600">The words table is empty: load supabase/seed.sql.</p>;
  return (
    <ul className="mt-3 space-y-2">
      {words.map((w) => (
        <li key={w.word}><span className="font-medium">{w.word}</span> — {w.definition}</li>
      ))}
    </ul>
  );
}

export default function Home() {
  const configured = supabaseEnv() !== null;
  return (
    <main className="mx-auto max-w-xl px-4 py-16">
      <h1 className="text-3xl font-semibold">WordOrbit</h1>
      {configured ? (
        <>
          <Suspense fallback={<p className="mt-6 text-gray-500">Checking sign-in…</p>}>
            <Account />
          </Suspense>
          <section className="mt-10">
            <h2 className="text-lg font-medium">A few words from the galaxy</h2>
            <Suspense fallback={<p className="mt-2 text-gray-500">Loading words…</p>}>
              <WordSample />
            </Suspense>
          </section>
        </>
      ) : (
        <p className="mt-4">
          Supabase is not configured yet. Copy <code>web/.env.example</code> to <code>web/.env.local</code> and fill it
          in (see <code>web/README.md</code>).
        </p>
      )}
      <footer className="mt-16 text-xs text-gray-500">For GRE preparation. Not affiliated with or endorsed by ETS.</footer>
    </main>
  );
}
