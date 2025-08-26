/**
 * File: extras/nextjs_auth_page/app/auth/page.tsx
 * Minimal Supabase Auth page (App Router). Copy into your Next.js app.
 */
"use client";

import { createClientComponentClient } from "@supabase/auth-helpers-nextjs";
import { useEffect, useState } from "react";
import { Auth } from "@supabase/auth-ui-react";
import { ThemeSupa } from "@supabase/auth-ui-shared";

export default function AuthPage() {
  const supabase = createClientComponentClient();
  const [ready, setReady] = useState(false);

  useEffect(() => { setReady(true); }, []);
  if (!ready) return null;

  const redirect =
    typeof window !== "undefined"
      ? `https://app.${process.env.NEXT_PUBLIC_DOMAIN ?? window.location.hostname}/app`
      : undefined;

  return (
    <main className="min-h-screen flex items-center justify-center p-6">
      <div className="w-full max-w-md rounded-2xl p-6 shadow">
        <h1 className="text-xl mb-4">Sign in</h1>
        <Auth
          supabaseClient={supabase}
          providers={["github", "google"]}
          appearance={{ theme: ThemeSupa }}
          redirectTo={redirect}
        />
      </div>
    </main>
  );
}
