"use client";

import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, type DashboardSummary } from "@/lib/api";

type Trend = {
  period: string;
  distance_m: number;
  duration_seconds: number;
  activities: number;
  elevation_gain_m: number;
  average_elapsed_pace_seconds_per_km: number | null;
};
type Overview = {
  activity_count: number;
  distance_m: number;
  duration_seconds: number;
  strength_workouts: number;
  activity_distribution: { type: string; count: number }[];
  running: {
    distance_m: number;
    duration_seconds: number;
    average_elapsed_pace_seconds_per_km: number | null;
  };
};

export default function AnalyticsPage() {
  const [period, setPeriod] = useState("week");
  const [activityType, setActivityType] = useState("all");
  const [chartMetric, setChartMetric] = useState("distance");
  const [trends, setTrends] = useState<Trend[]>([]);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    api<Overview>("/analytics/overview")
      .then(setOverview)
      .catch((cause: Error) => setError(cause.message));
  }, []);
  useEffect(() => {
    const params = new URLSearchParams({ period });
    if (activityType !== "all") params.set("activity_type", activityType);
    api<{ data: Trend[] }>(`/analytics/trends?${params}`)
      .then((result) => setTrends(result.data))
      .catch((cause: Error) => setError(cause.message));
  }, [period, activityType]);
  const chartData = trends.map((item) => ({
    ...item,
    distance_km: Math.round(item.distance_m / 10) / 100,
    elapsed_pace_minutes_per_km:
      item.average_elapsed_pace_seconds_per_km === null
        ? null
        : item.average_elapsed_pace_seconds_per_km / 60,
  }));
  const chartKey =
    chartMetric === "pace"
      ? "elapsed_pace_minutes_per_km"
      : chartMetric === "elevation"
        ? "elevation_gain_m"
        : "distance_km";
  const chartLabel =
    chartMetric === "pace"
      ? "Elapsed pace (min/km)"
      : chartMetric === "elevation"
        ? "Elevation (m)"
        : "Distance (km)";
  const hasChartData = chartData.some(
    (item) => item[chartKey] !== null && item[chartKey] !== 0,
  );

  return (
    <div className="page-content">
      <div className="page-heading-row">
        <div>
          <div className="page-kicker">Training analysis</div>
          <h1 className="page-heading">The shape of your work.</h1>
          <p className="page-subtitle">
            Pace uses elapsed activity duration; moving pace requires movement
            samples.
          </p>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <select
            aria-label="Activity type"
            value={activityType}
            onChange={(event) => setActivityType(event.target.value)}
            style={{
              minHeight: 40,
              padding: "0 12px",
              color: "var(--ink)",
              background: "var(--surface)",
              border: "1px solid var(--line)",
              borderRadius: 4,
            }}
          >
            <option value="all">All activities</option>
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
          <select
            aria-label="Trend period"
            value={period}
            onChange={(event) => setPeriod(event.target.value)}
            style={{
              minHeight: 40,
              padding: "0 12px",
              color: "var(--ink)",
              background: "var(--surface)",
              border: "1px solid var(--line)",
              borderRadius: 4,
            }}
          >
            <option value="week">Last 12 weeks</option>
            <option value="month">Last 12 months</option>
            <option value="year">Last 5 years</option>
          </select>
          <select
            aria-label="Chart metric"
            value={chartMetric}
            onChange={(event) => setChartMetric(event.target.value)}
            style={{
              minHeight: 40,
              padding: "0 12px",
              color: "var(--ink)",
              background: "var(--surface)",
              border: "1px solid var(--line)",
              borderRadius: 4,
            }}
          >
            <option value="distance">Distance</option>
            <option value="pace">Elapsed run pace</option>
            <option value="elevation">Elevation gain</option>
          </select>
        </div>
      </div>
      {error && (
        <div className="error-message" role="alert">
          {error}
        </div>
      )}
      {overview && (
        <div className="metrics-grid">
          <Metric
            label="Activities"
            value={overview.activity_count.toString()}
          />
          <Metric
            label="Distance"
            value={`${(overview.distance_m / 1000).toFixed(1)} km`}
          />
          <Metric
            label="Training time"
            value={`${Math.floor(overview.duration_seconds / 3600)}h ${Math.floor((overview.duration_seconds % 3600) / 60)}m`}
          />
          <Metric
            label="Avg elapsed run pace"
            value={formatPace(
              overview.running.average_elapsed_pace_seconds_per_km,
            )}
          />
        </div>
      )}
      <section
        className="content-panel"
        style={{ marginTop: 18, padding: "20px 20px 12px" }}
      >
        <div className="section-heading" style={{ margin: "0 0 15px" }}>
          <h2>
            {chartMetric === "pace"
              ? "Elapsed running pace"
              : chartMetric === "elevation"
                ? "Elevation progression"
                : "Distance trend"}
          </h2>
          <span className="table-caption">{chartLabel}</span>
        </div>
        {hasChartData ? (
          <div style={{ width: "100%", height: 280 }}>
            <ResponsiveContainer>
              <BarChart
                data={chartData}
                margin={{ top: 8, right: 8, left: -18, bottom: 4 }}
              >
                <CartesianGrid stroke="#2b352d" vertical={false} />
                <XAxis
                  dataKey="period"
                  tick={{ fill: "#9da69b", fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: "#9da69b", fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  contentStyle={{
                    background: "#202820",
                    border: "1px solid #39443a",
                    borderRadius: 4,
                  }}
                />
                <Bar
                  dataKey={chartKey}
                  name={chartLabel}
                  fill="#c6f36b"
                  radius={[3, 3, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="empty-state">
            <h3>
              {chartMetric === "pace"
                ? "No run distance and duration to calculate pace"
                : "Not enough activity to chart yet"}
            </h3>
            <p>
              {chartMetric === "pace"
                ? "Pace is not estimated without suitable run data."
                : "Your trend will appear as soon as sessions are logged."}
            </p>
          </div>
        )}
      </section>
      <div className="section-heading">
        <h2>Activity mix</h2>
      </div>
      <div className="activity-table">
        {overview?.activity_distribution.length ? (
          overview.activity_distribution.map((item) => (
            <div className="activity-row" key={item.type}>
              <span className="activity-title">{item.type}</span>
              <span>
                <span className="table-caption" style={{ display: "block" }}>
                  Sessions
                </span>
                <span className="table-value">{item.count}</span>
              </span>
            </div>
          ))
        ) : (
          <div className="empty-state">
            <h3>No activities to compare</h3>
            <p>Activity distribution will be based on your saved log.</p>
          </div>
        )}
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <section className="metric">
      <div className="metric-label">{label}</div>
      <div className="metric-value" style={{ fontSize: 24 }}>
        {value}
      </div>
    </section>
  );
}

function formatPace(secondsPerKm: number | null) {
  if (secondsPerKm === null) return "No run data";
  const minutes = Math.floor(secondsPerKm / 60);
  const seconds = Math.round(secondsPerKm % 60)
    .toString()
    .padStart(2, "0");
  return `${minutes}:${seconds} /km`;
}
