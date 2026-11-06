"use client";

import { Download, FileJson, FileSpreadsheet } from "lucide-react";
import { useState } from "react";
import { API_BASE } from "@/lib/api";

export default function SettingsPage() {
  const [error, setError] = useState("");
  async function download(format: "json" | "csv") {
    setError("");
    try {
      const response = await fetch(
        `${API_BASE}/export/activities?format=${format}`,
        { credentials: "include" },
      );
      if (!response.ok)
        throw new Error("Unable to export activities. Please sign in again.");
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `pace-activities.${format}`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Export failed.");
    }
  }
  return (
    <div className="page-content">
      <div className="page-heading-row">
        <div>
          <div className="page-kicker">Preferences</div>
          <h1 className="page-heading">Your data, yours.</h1>
          <p className="page-subtitle">
            Export the activity records associated with your account.
          </p>
        </div>
      </div>
      {error && (
        <div className="error-message" role="alert">
          {error}
        </div>
      )}
      <section className="content-panel" style={{ padding: 22 }}>
        <h2 style={{ margin: "0 0 7px", fontSize: 16 }}>Activity export</h2>
        <p style={{ margin: "0 0 18px", color: "var(--muted)" }}>
          Download your saved activities in an interoperable format.
        </p>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <button
            className="button-secondary"
            type="button"
            onClick={() => download("csv")}
          >
            <FileSpreadsheet size={16} />
            Export CSV
          </button>
          <button
            className="button-secondary"
            type="button"
            onClick={() => download("json")}
          >
            <FileJson size={16} />
            Export JSON
          </button>
        </div>
        <div className="field-hint" style={{ marginTop: 14 }}>
          Only your own activity data is included.
        </div>
      </section>
      <section className="content-panel" style={{ marginTop: 14, padding: 22 }}>
        <h2 style={{ margin: "0 0 7px", fontSize: 16 }}>Account</h2>
        <p style={{ margin: 0, color: "var(--muted)" }}>
          Your session uses an HTTP-only, SameSite=Lax cookie; HTTPS deployments
          require the Secure cookie flag.
        </p>
      </section>
    </div>
  );
}
