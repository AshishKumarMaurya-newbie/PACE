"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";

export default function NewActivityPage() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSaving(true);
    const form = new FormData(event.currentTarget);
    const distance = String(form.get("distance_km") || "");
    const optionalNumber = (name: string) => {
      const value = String(form.get(name) || "");
      return value ? Number(value) : null;
    };
    try {
      const activity = await api<{ id: string }>("/activities", {
        method: "POST",
        body: JSON.stringify({
          activity_type: form.get("activity_type"),
          title: form.get("title"),
          started_at: new Date(String(form.get("started_at"))).toISOString(),
          duration_seconds: Number(form.get("duration_minutes")) * 60,
          distance_m: distance ? Number(distance) * 1000 : null,
          elevation_gain_m: optionalNumber("elevation_gain_m"),
          average_heart_rate: optionalNumber("average_heart_rate"),
          perceived_effort: optionalNumber("perceived_effort"),
          notes: form.get("notes") || null,
        }),
      });
      router.push(`/activities/${activity.id}`);
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Unable to save activity.",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="page-content">
      <div className="page-heading-row">
        <div>
          <div className="page-kicker">Training log</div>
          <h1 className="page-heading">Log an activity</h1>
          <p className="page-subtitle">
            Add the details you want to keep. You can edit them later.
          </p>
        </div>
      </div>
      <form className="content-panel form-panel" onSubmit={submit}>
        {error && (
          <div className="error-message" role="alert">
            {error}
          </div>
        )}
        <div className="form-grid">
          <div className="field">
            <label htmlFor="activity_type">Activity type</label>
            <select
              id="activity_type"
              name="activity_type"
              required
              defaultValue="run"
            >
              <option value="run">Running</option>
              <option value="walk">Walking</option>
              <option value="ride">Cycling</option>
              <option value="hike">Hiking</option>
              <option value="swim">Swimming</option>
              <option value="strength">Strength</option>
              <option value="yoga">Yoga</option>
              <option value="sport">Sport</option>
              <option value="other">Other</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="title">Title</label>
            <input
              id="title"
              name="title"
              required
              maxLength={160}
              placeholder="Easy morning run"
            />
          </div>
          <div className="field">
            <label htmlFor="started_at">Date and start time</label>
            <input
              id="started_at"
              name="started_at"
              type="datetime-local"
              required
              defaultValue={new Date(
                Date.now() - new Date().getTimezoneOffset() * 60000,
              )
                .toISOString()
                .slice(0, 16)}
            />
          </div>
          <div className="field">
            <label htmlFor="duration_minutes">Duration (minutes)</label>
            <input
              id="duration_minutes"
              name="duration_minutes"
              type="number"
              min="1"
              max="2880"
              step="1"
              required
              placeholder="45"
            />
          </div>
          <div className="field">
            <label htmlFor="distance_km">Distance (km)</label>
            <input
              id="distance_km"
              name="distance_km"
              type="number"
              min="0.01"
              max="2000"
              step="0.01"
              placeholder="Optional"
            />
          </div>
          <div className="field">
            <label htmlFor="elevation_gain_m">Elevation gain (m)</label>
            <input
              id="elevation_gain_m"
              name="elevation_gain_m"
              type="number"
              min="0"
              step="1"
              placeholder="Optional"
            />
          </div>
          <div className="field">
            <label htmlFor="average_heart_rate">Average heart rate (bpm)</label>
            <input
              id="average_heart_rate"
              name="average_heart_rate"
              type="number"
              min="30"
              max="250"
              step="1"
              placeholder="Optional"
            />
          </div>
          <div className="field">
            <label htmlFor="perceived_effort">Perceived effort (1-10)</label>
            <input
              id="perceived_effort"
              name="perceived_effort"
              type="number"
              min="1"
              max="10"
              step="1"
              placeholder="Optional"
            />
          </div>
          <div className="field wide">
            <label htmlFor="notes">Notes</label>
            <textarea
              id="notes"
              name="notes"
              maxLength={4000}
              placeholder="How did it feel? Anything you want to remember?"
            />
          </div>
        </div>
        <div className="form-actions">
          <Link className="button-secondary" href="/activities">
            Cancel
          </Link>
          <button className="button-primary" type="submit" disabled={saving}>
            {saving ? "Saving..." : "Save activity"}
          </button>
        </div>
      </form>
    </div>
  );
}
