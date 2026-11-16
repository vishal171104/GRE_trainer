import { createBrowserClient } from "@supabase/ssr";
import { supabaseEnv } from "./env";

// Supabase client for Client Components (code that runs in the browser).
export function createClient() {
  const env = supabaseEnv();
  if (!env) throw new Error("Supabase is not configured: set the variables in web/.env.example.");
  return createBrowserClient(env.url, env.key);
}
