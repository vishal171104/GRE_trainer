import Link from "next/link";
import { Suspense } from "react";
import { SignInButton } from "./sign-in-button";

type Props = { searchParams: Promise<{ error?: string }> };

// Reads ?error= from the request, so it streams in behind Suspense
// while the rest of the page is served from the static shell.
async function SignInError({ searchParams }: Props) {
  const { error } = await searchParams;
  return error ? <p className="text-sm text-red-600">Sign-in did not finish. Please try again.</p> : null;
}

export default function LoginPage({ searchParams }: Props) {
  return (
    <main className="mx-auto flex min-h-screen max-w-sm flex-col justify-center gap-6 px-4">
      <h1 className="text-3xl font-semibold">Sign in to WordOrbit</h1>
      <Suspense fallback={null}>
        <SignInError searchParams={searchParams} />
      </Suspense>
      <SignInButton />
      <Link href="/" className="text-sm text-gray-500 underline">Back to the home page</Link>
    </main>
  );
}
