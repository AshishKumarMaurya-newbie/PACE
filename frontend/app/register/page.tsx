"use client";

import Link from "next/link";
import { Activity as ActivityIcon } from "lucide-react";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setBusy(true);
    const data = new FormData(event.currentTarget);
    try {
      await api("/auth/register", {
        method: "POST",
        body: JSON.stringify({
          email: data.get("email"),
          full_name: data.get("full_name"),
          password: data.get("password"),
        }),
      });
      router.replace("/dashboard");
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Unable to create account.",
      );
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
          <div className="page-kicker">A record of your work</div>
          <h1>Start where you are. Build from there.</h1>
          <p>
            Your first session is the beginning of a clearer picture of your
            training.
          </p>
        </div>
        <div className="auth-aside-foot">Your data belongs to you.</div>
      </aside>
      <section className="auth-main">
        <form className="auth-form" onSubmit={submit}>
          <div className="page-kicker">Create your space</div>
          <h2>Join PACE</h2>
          <p>Set up your personal training log.</p>
          {error && (
            <div className="error-message" role="alert">
              {error}
            </div>
          )}
          <div className="field">
            <label htmlFor="full_name">Name</label>
            <input
              id="full_name"
              name="full_name"
              autoComplete="name"
              maxLength={120}
              required
            />
          </div>
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
              autoComplete="new-password"
              minLength={10}
              required
            />
            <span className="field-hint">Use at least 10 characters.</span>
          </div>
          <button className="button-primary" type="submit" disabled={busy}>
            {busy ? "Creating account..." : "Create account"}
          </button>
          <div className="auth-foot">
            Already have an account? <Link href="/login">Sign in</Link>
          </div>
        </form>
      </section>
    </main>
  );
}
