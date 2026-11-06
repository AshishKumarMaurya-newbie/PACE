"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  CalendarDays,
  Clock3,
  Footprints,
  Pencil,
  Trash2,
} from "lucide-react";
import { useEffect, useState } from "react";
import { api, type Activity } from "@/lib/api";

function duration(seconds: number) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return hours ? `${hours} hr ${minutes} min` : `${minutes} min`;
}

export default function ActivityDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [activity, setActivity] = useState<Activity | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    api<Activity>(`/activities/${id}`)
      .then(setActivity)
      .catch((cause: Error) => setError(cause.message));
  }, [id]);

  async function remove() {
    if (!window.confirm("Delete this activity? This cannot be undone.")) return;
    try {
      await api<void>(`/activities/${id}`, { method: "DELETE" });
      router.replace("/activities");
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Unable to delete activity.",
      );
    }
  }

  return (
    <div className="page-content">
      <Link className="text-link" href="/activities">
        <ArrowLeft
          size={14}
          style={{ verticalAlign: "middle", marginRight: 6 }}
        />
        Activity history
      </Link>
      {error && (
        <div className="error-message" role="alert" style={{ marginTop: 18 }}>
          {error}
        </div>
      )}
      {!activity ? (
        <div className="loading">Loading activity...</div>
      ) : (
        <>
          <div className="page-heading-row" style={{ marginTop: 22 }}>
            <div>
              <div className="page-kicker">{activity.activity_type}</div>
              <h1 className="page-heading">{activity.title}</h1>
              <p className="page-subtitle">
                {new Date(activity.started_at).toLocaleString()}
              </p>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <Link
                className="button-secondary"
                href={`/activities/${id}/edit`}
              >
                <Pencil size={15} />
                Edit
              </Link>
              <button
                className="button-secondary"
                type="button"
                onClick={remove}
                aria-label="Delete activity"
              >
                <Trash2 size={15} />
              </button>
            </div>
          </div>
          <div className="metrics-grid">
            <DetailMetric
              label="Duration"
              value={duration(activity.duration_seconds)}
              icon={<Clock3 size={16} />}
            />
            <DetailMetric
              label="Distance"
              value={
                activity.distance_m
                  ? `${(activity.distance_m / 1000).toFixed(2)} km`
                  : "Not recorded"
              }
              icon={<Footprints size={16} />}
            />
            <DetailMetric
              label="Elevation gain"
              value={
                activity.elevation_gain_m != null
                  ? `${activity.elevation_gain_m} m`
                  : "Not recorded"
              }
              icon={<ArrowLeft size={16} />}
            />
            <DetailMetric
              label="Average heart rate"
              value={
                activity.average_heart_rate
                  ? `${activity.average_heart_rate} bpm`
                  : "Not recorded"
              }
              icon={<CalendarDays size={16} />}
            />
          </div>
          {activity.notes && (
            <section
              className="content-panel"
              style={{ marginTop: 18, padding: 22 }}
            >
              <h2 style={{ margin: "0 0 10px", fontSize: 15 }}>Notes</h2>
              <p
                style={{
                  margin: 0,
                  color: "var(--muted)",
                  lineHeight: 1.7,
                  whiteSpace: "pre-wrap",
                }}
              >
                {activity.notes}
              </p>
            </section>
          )}
        </>
      )}
    </div>
  );
}

function DetailMetric({
  label,
  value,
  icon,
}: {
  label: string;
  value: string;
  icon: React.ReactNode;
}) {
  return (
    <section className="metric">
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          color: "var(--muted)",
        }}
      >
        <span className="metric-label">{label}</span>
        <span>{icon}</span>
      </div>
      <div className="metric-value" style={{ fontSize: 21 }}>
        {value}
      </div>
    </section>
  );
}
