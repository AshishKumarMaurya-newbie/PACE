"use client";

import Link from "next/link";
import {
  Activity as ActivityIcon,
  ArrowUpRight,
  Clock3,
  Footprints,
  Plus,
} from "lucide-react";
import { useEffect, useState } from "react";
import { api, type DashboardSummary } from "@/lib/api";

function formatDuration(seconds: number) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return hours ? `${hours}h ${minutes}m` : `${minutes}m`;
}

function formatDistance(meters: number) {
  return `${(meters / 1000).toFixed(meters >= 10000 ? 0 : 1)}`;
}

function formatActivityDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    weekday: "short",
    month: "short",
    day: "numeric",
  }).format(new Date(value));
}

export default function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<DashboardSummary>("/dashboard/summary")
      .then(setSummary)
      .catch((cause: Error) => setError(cause.message));
  }, []);

  return (
    <div className="page-content">
      <div className="page-heading-row">
        <div>
          <div className="page-kicker">Overview</div>
          <h1 className="page-heading">Your training, in focus.</h1>
          <p className="page-subtitle">
            A clear view of the work you have put in.
          </p>
        </div>
        <Link className="button-primary" href="/activities/new">
          <Plus size={16} />
          Log activity
        </Link>
      </div>
      {error && (
        <div className="error-message" role="alert">
          {error}
        </div>
      )}
      {!summary ? (
        <div className="loading">Loading your activity...</div>
      ) : (
        <>
          <div className="metrics-grid">
            <Metric
              label="Total distance"
              value={formatDistance(summary.total_distance_m)}
              unit="km"
              foot="Across all activities"
              icon={<Footprints size={15} />}
            />
            <Metric
              label="Training time"
              value={formatDuration(summary.total_duration_seconds)}
              foot="Across all activities"
              icon={<Clock3 size={15} />}
            />
            <Metric
              label="Activities logged"
              value={String(summary.total_activities)}
              foot={`${summary.month_activities} this month`}
              icon={<ActivityIcon size={15} />}
            />
            <Metric
              label="This week"
              value={formatDistance(summary.week_distance_m)}
              unit="km"
              foot={`${summary.week_activities} sessions`}
              icon={<ArrowUpRight size={15} />}
            />
          </div>
          <div className="section-heading">
            <h2>Recent activity</h2>
            <Link className="text-link" href="/activities">
              View history{" "}
              <ArrowUpRight size={13} style={{ verticalAlign: "middle" }} />
            </Link>
          </div>
          <div className="activity-table">
            {summary.recent_activities.length ||
            summary.recent_strength_workouts.length ? (
              [
                ...summary.recent_activities.map((item) => ({
                  id: item.id,
                  title: item.title,
                  started_at: item.started_at,
                  duration_seconds: item.duration_seconds,
                  activity_type: item.activity_type,
                  distance_m: item.distance_m,
                  heart_rate: item.average_heart_rate,
                  href: `/activities/${item.id}`,
                })),
                ...summary.recent_strength_workouts.map((item) => ({
                  id: item.id,
                  title: item.title,
                  started_at: item.started_at,
                  duration_seconds: item.duration_seconds ?? 0,
                  activity_type: "strength",
                  distance_m: null,
                  heart_rate: null,
                  href: "/strength",
                })),
              ]
                .sort((a, b) => b.started_at.localeCompare(a.started_at))
                .slice(0, 5)
                .map((activity) => (
                  <Link
                    className="activity-row"
                    href={activity.href}
                    key={activity.id}
                  >
                    <span className="activity-name">
                      <span className="activity-symbol">
                        <ActivityIcon size={16} />
                      </span>
                      <span style={{ minWidth: 0 }}>
                        <span
                          className="activity-title"
                          style={{ display: "block" }}
                        >
                          {activity.title}
                        </span>
                        <span
                          className="activity-date"
                          style={{ display: "block" }}
                        >
                          {formatActivityDate(activity.started_at)} ·{" "}
                          {activity.activity_type}
                        </span>
                      </span>
                    </span>
                    <span>
                      <span
                        className="table-caption"
                        style={{ display: "block" }}
                      >
                        Distance
                      </span>
                      <span className="table-value">
                        {activity.distance_m
                          ? `${(activity.distance_m / 1000).toFixed(2)} km`
                          : "—"}
                      </span>
                    </span>
                    <span>
                      <span
                        className="table-caption"
                        style={{ display: "block" }}
                      >
                        Duration
                      </span>
                      <span className="table-value">
                        {formatDuration(activity.duration_seconds)}
                      </span>
                    </span>
                    <span>
                      <span
                        className="table-caption"
                        style={{ display: "block" }}
                      >
                        Effort
                      </span>
                      <span className="table-value">
                        {activity.heart_rate
                          ? `${activity.heart_rate} bpm`
                          : "—"}
                      </span>
                    </span>
                  </Link>
                ))
            ) : (
              <div className="empty-state">
                <span className="empty-icon">
                  <ActivityIcon size={21} />
                </span>
                <h3>Your next session starts here</h3>
                <p>
                  Log an activity to begin building a training history. Your
                  totals and trends will grow from what you record.
                </p>
                <Link className="button-secondary" href="/activities/new">
                  <Plus size={15} />
                  Add first activity
                </Link>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function Metric({
  label,
  value,
  unit,
  foot,
  icon,
}: {
  label: string;
  value: string;
  unit?: string;
  foot: string;
  icon: React.ReactNode;
}) {
  return (
    <section className="metric">
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <span className="metric-label">{label}</span>
        <span style={{ color: "var(--lime)" }}>{icon}</span>
      </div>
      <div className="metric-value">
        {value}
        {unit && <span className="metric-unit">{unit}</span>}
      </div>
      <div className="metric-foot">{foot}</div>
    </section>
  );
}
