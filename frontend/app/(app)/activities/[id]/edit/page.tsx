"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, type Activity } from "@/lib/api";

export default function EditActivityPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [activity, setActivity] = useState<Activity | null>(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    api<Activity>(`/activities/${id}`)
      .then(setActivity)
      .catch((cause: Error) => setError(cause.message));
  }, [id]);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    const form = new FormData(event.currentTarget);
    const number = (key: string) => String(form.get(key) || "");
    try {
      await api(`/activities/${id}`, {
        method: "PATCH",
        body: JSON.stringify({
          activity_type: form.get("activity_type"),
          title: form.get("title"),
          started_at: new Date(number("started_at")).toISOString(),
          duration_seconds: Number(number("duration_minutes")) * 60,
          distance_m: number("distance_km")
            ? Number(number("distance_km")) * 1000
            : null,
          elevation_gain_m: number("elevation_gain_m")
            ? Number(number("elevation_gain_m"))
            : null,
          average_heart_rate: number("average_heart_rate")
            ? Number(number("average_heart_rate"))
            : null,
          perceived_effort: number("perceived_effort")
            ? Number(number("perceived_effort"))
            : null,
          notes: form.get("notes") || null,
        }),
      });
      router.push(`/activities/${id}`);
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Unable to update activity.",
      );
    } finally {
      setSaving(false);
    }
  }

  if (!activity)
    return (
      <div className="page-content">
        {error ? (
          <div className="error-message" role="alert">
            {error}
          </div>
        ) : (
          <div className="loading">Loading activity...</div>
        )}
      </div>
    );
  const localStart = new Date(
    new Date(activity.started_at).getTime() -
      new Date(activity.started_at).getTimezoneOffset() * 60000,
  )
    .toISOString()
    .slice(0, 16);
  return (
    <div className="page-content">
      <div className="page-heading-row">
        <div>
          <div className="page-kicker">Training log</div>
          <h1 className="page-heading">Edit activity</h1>
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
              defaultValue={activity.activity_type}
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
              defaultValue={activity.title}
            />
          </div>
          <div className="field">
            <label htmlFor="started_at">Date and start time</label>
            <input
              id="started_at"
              name="started_at"
              type="datetime-local"
              required
              defaultValue={localStart}
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
              defaultValue={activity.duration_seconds / 60}
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
              defaultValue={
                activity.distance_m ? activity.distance_m / 1000 : ""
              }
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
              defaultValue={activity.elevation_gain_m ?? ""}
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
              defaultValue={activity.average_heart_rate ?? ""}
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
              defaultValue=""
            />
          </div>
          <div className="field wide">
            <label htmlFor="notes">Notes</label>
            <textarea
              id="notes"
              name="notes"
              maxLength={4000}
              defaultValue={activity.notes ?? ""}
            />
          </div>
        </div>
        <div className="form-actions">
          <Link className="button-secondary" href={`/activities/${id}`}>
            Cancel
          </Link>
          <button className="button-primary" type="submit" disabled={saving}>
            {saving ? "Saving..." : "Save changes"}
          </button>
        </div>
      </form>
    </div>
  );
}
