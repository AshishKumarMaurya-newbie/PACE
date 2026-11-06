"use client";

import Link from "next/link";
import { Activity as ActivityIcon } from "lucide-react";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setBusy(true);
    const data = new FormData(event.currentTarget);
    try {
      await api("/auth/login", {
        method: "POST",
        body: JSON.stringify({
          email: data.get("email"),
          password: data.get("password"),
        }),
      });
      router.replace("/dashboard");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to sign in.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-page">
      <aside className="auth-aside">
        <Link className="brand" href="/">
          <span className="brand-mark">
            <ActivityIcon size={17} />
          </span>
          <span className="brand-name">PACE</span>
        </Link>
        <div className="auth-aside-copy">
          <div className="page-kicker">Keep your own pace</div>
          <h1>Consistency is built one session at a time.</h1>
          <p>
            Make room for the work, keep a record of it, and notice how far you
            have come.
          </p>
        </div>
        <div className="auth-aside-foot">
          A considered home for your training.
        </div>
      </aside>
      <section className="auth-main">
        <form className="auth-form" onSubmit={submit}>
          <div className="page-kicker">Welcome back</div>
          <h2>Sign in to PACE</h2>
          <p>Your training log is right where you left it.</p>
          {error && (
            <div className="error-message" role="alert">
              {error}
            </div>
          )}
          <div className="field">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              required
            />
          </div>
          <div className="field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              required
            />
          </div>
          <button className="button-primary" type="submit" disabled={busy}>
            {busy ? "Signing in..." : "Sign in"}
          </button>
          <div className="auth-foot">
            New to PACE? <Link href="/register">Create an account</Link>
          </div>
        </form>
      </section>
    </main>
  );
}
