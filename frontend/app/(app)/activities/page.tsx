"use client";

import Link from "next/link";
import { Activity as ActivityIcon, Plus, Search } from "lucide-react";
import { useEffect, useState } from "react";
import { api, type Activity } from "@/lib/api";

export default function ActivitiesPage() {
  const [activities, setActivities] = useState<Activity[]>([]);
  const [search, setSearch] = useState("");
  const [kind, setKind] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const params = new URLSearchParams();
    if (search.trim()) params.set("search", search.trim());
    if (kind) params.set("activity_type", kind);
    api<Activity[]>(`/activities?${params}`)
      .then(setActivities)
      .catch((cause: Error) => setError(cause.message));
  }, [search, kind]);

  return (
    <div className="page-content">
      <div className="page-heading-row">
        <div>
          <div className="page-kicker">Training log</div>
          <h1 className="page-heading">Activities</h1>
          <p className="page-subtitle">Every session, kept in one place.</p>
        </div>
        <Link className="button-primary" href="/activities/new">
          <Plus size={16} />
          Log activity
        </Link>
      </div>
      <div
        style={{ display: "flex", gap: 10, marginBottom: 16, flexWrap: "wrap" }}
      >
        <label style={{ position: "relative", flex: "1 1 220px" }}>
          <Search
            size={16}
            style={{
              position: "absolute",
              left: 12,
              top: 13,
              color: "var(--muted)",
            }}
          />
          <input
            aria-label="Search activities"
            placeholder="Search activities"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            style={{
              width: "100%",
              minHeight: 42,
              padding: "0 12px 0 38px",
              color: "var(--ink)",
              background: "var(--surface)",
              border: "1px solid var(--line)",
              borderRadius: 4,
            }}
          />
        </label>
        <select
          aria-label="Filter by activity type"
          value={kind}
          onChange={(event) => setKind(event.target.value)}
          style={{
            minWidth: 155,
            padding: "0 12px",
            color: "var(--ink)",
            background: "var(--surface)",
            border: "1px solid var(--line)",
            borderRadius: 4,
          }}
        >
          <option value="">All activities</option>
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
      {error && (
        <div className="error-message" role="alert">
          {error}
        </div>
      )}
      <div className="activity-table">
        {activities.length ? (
          activities.map((activity) => (
            <Link
              className="activity-row"
              href={`/activities/${activity.id}`}
              key={activity.id}
            >
              <span className="activity-name">
                <span className="activity-symbol">
                  <ActivityIcon size={16} />
                </span>
                <span style={{ minWidth: 0 }}>
                  <span className="activity-title" style={{ display: "block" }}>
                    {activity.title}
                  </span>
                  <span className="activity-date" style={{ display: "block" }}>
                    {new Date(activity.started_at).toLocaleDateString()} ·{" "}
                    {activity.activity_type}
                  </span>
                </span>
              </span>
              <span>
                <span className="table-caption" style={{ display: "block" }}>
                  Distance
                </span>
                <span className="table-value">
                  {activity.distance_m
                    ? `${(activity.distance_m / 1000).toFixed(2)} km`
                    : "—"}
                </span>
              </span>
              <span>
                <span className="table-caption" style={{ display: "block" }}>
                  Duration
                </span>
                <span className="table-value">
                  {Math.floor(activity.duration_seconds / 60)} min
                </span>
              </span>
              <span>
                <span className="table-caption" style={{ display: "block" }}>
                  Heart rate
                </span>
                <span className="table-value">
                  {activity.average_heart_rate
                    ? `${activity.average_heart_rate} bpm`
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
            <h3>No matching sessions</h3>
            <p>Try changing your search or log your first activity.</p>
            <Link className="button-secondary" href="/activities/new">
              <Plus size={15} />
              Log activity
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
