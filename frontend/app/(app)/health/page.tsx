"use client";

import { useEffect, useMemo, useState } from "react";
import { HeartPulse, Plus } from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "@/lib/api";

type Metric = {
  id: string;
  metric_type: string;
  value: string;
  unit: string;
  recorded_at: string;
};
const knownMetrics: Record<string, string> = {
  body_weight: "kg",
  body_fat_percentage: "%",
  resting_heart_rate: "bpm",
  sleep_duration: "hours",
  daily_steps: "steps",
};

export default function HealthPage() {
  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [kind, setKind] = useState("body_weight");
  const [customType, setCustomType] = useState("");
  const [customUnit, setCustomUnit] = useState("");
  const [error, setError] = useState("");
  const selectedKind = kind === "custom" ? customType : kind;
  const selectedUnit = kind === "custom" ? customUnit : knownMetrics[kind];
  async function reload() {
    setMetrics(await api<Metric[]>("/health/metrics"));
  }
  useEffect(() => {
    reload().catch((cause: Error) => setError(cause.message));
  }, []);
  const chartData = useMemo(
    () =>
      metrics
        .filter((metric) => metric.metric_type === selectedKind)
        .slice()
        .reverse()
        .map((metric) => ({
          date: new Date(metric.recorded_at).toLocaleDateString(),
          value: Number(metric.value),
        })),
    [metrics, selectedKind],
  );

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const formElement = event.currentTarget;
    const data = new FormData(formElement);
    try {
      await api("/health/metrics", {
        method: "POST",
        body: JSON.stringify({
          metric_type: selectedKind,
          unit: selectedUnit,
          value: Number(data.get("value")),
          recorded_at: new Date(String(data.get("recorded_at"))).toISOString(),
        }),
      });
      formElement.reset();
      await reload();
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Unable to save metric.",
      );
    }
  }

  return (
    <div className="page-content">
      <div className="page-heading-row">
        <div>
          <div className="page-kicker">Health and wellness</div>
          <h1 className="page-heading">Your signals, recorded.</h1>
          <p className="page-subtitle">
            Manual entries only. PACE does not infer or measure these values.
          </p>
        </div>
      </div>
      {error && (
        <div className="error-message" role="alert">
          {error}
        </div>
      )}
      <form className="content-panel form-panel" onSubmit={submit}>
        <div className="form-grid">
          <div className="field">
            <label htmlFor="metric_type">Metric</label>
            <select
              id="metric_type"
              value={kind}
              onChange={(event) => setKind(event.target.value)}
            >
              <option value="body_weight">Body weight</option>
              <option value="body_fat_percentage">Body fat</option>
              <option value="resting_heart_rate">Resting heart rate</option>
              <option value="sleep_duration">Sleep duration</option>
              <option value="daily_steps">Daily steps</option>
              <option value="custom">Custom metric</option>
            </select>
          </div>
          {kind === "custom" && (
            <>
              <div className="field">
                <label htmlFor="custom_type">Metric key</label>
                <input
                  id="custom_type"
                  value={customType}
                  onChange={(event) =>
                    setCustomType(
                      event.target.value
                        .toLowerCase()
                        .replace(/[^a-z0-9_]/g, "_"),
                    )
                  }
                  pattern="[a-z][a-z0-9_]*"
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="custom_unit">Unit</label>
                <input
                  id="custom_unit"
                  value={customUnit}
                  onChange={(event) => setCustomUnit(event.target.value)}
                  maxLength={16}
                  required
                />
              </div>
            </>
          )}
          <div className="field">
            <label htmlFor="value">
              Value {selectedUnit ? `(${selectedUnit})` : ""}
            </label>
            <input
              id="value"
              name="value"
              type="number"
              min="0"
              max="1000000"
              step="0.001"
              required
            />
          </div>
          <div className="field">
            <label htmlFor="recorded_at">Recorded at</label>
            <input
              id="recorded_at"
              name="recorded_at"
              type="datetime-local"
              defaultValue={new Date(
                Date.now() - new Date().getTimezoneOffset() * 60000,
              )
                .toISOString()
                .slice(0, 16)}
              required
            />
          </div>
        </div>
        <div className="form-actions">
          <button className="button-primary" type="submit">
            <Plus size={15} />
            Add measurement
          </button>
        </div>
      </form>
      <section className="content-panel" style={{ marginTop: 18, padding: 20 }}>
        <div className="section-heading" style={{ margin: "0 0 15px" }}>
          <h2>
            {selectedKind ? selectedKind.replaceAll("_", " ") : "Metric trend"}
          </h2>
          <span className="table-caption">{selectedUnit}</span>
        </div>
        {chartData.length > 1 ? (
          <div style={{ width: "100%", height: 250 }}>
            <ResponsiveContainer>
              <LineChart
                data={chartData}
                margin={{ top: 8, right: 8, left: -18, bottom: 4 }}
              >
                <CartesianGrid stroke="#2b352d" vertical={false} />
                <XAxis
                  dataKey="date"
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
                <Line
                  type="monotone"
                  dataKey="value"
                  name={selectedUnit}
                  stroke="#83b9d1"
                  strokeWidth={2}
                  dot={{ r: 3 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="empty-state">
            <span className="empty-icon">
              <HeartPulse size={20} />
            </span>
            <h3>
              {chartData.length
                ? "One entry recorded"
                : "No measurements for this metric"}
            </h3>
            <p>Record it over time to see a trend. Nothing is estimated.</p>
          </div>
        )}
      </section>
      <div className="section-heading">
        <h2>Recent entries</h2>
      </div>
      <div className="activity-table">
        {metrics.length ? (
          metrics.slice(0, 20).map((metric) => (
            <article className="activity-row" key={metric.id}>
              <span className="activity-name">
                <span className="activity-symbol">
                  <HeartPulse size={16} />
                </span>
                <span className="activity-title">
                  {metric.metric_type.replaceAll("_", " ")}
                </span>
              </span>
              <span className="table-value">
                {metric.value} {metric.unit}
              </span>
              <span className="table-value">
                {new Date(metric.recorded_at).toLocaleDateString()}
              </span>
            </article>
          ))
        ) : (
          <div className="empty-state">
            <h3>No health metrics logged</h3>
            <p>Add a measurement when you have one to track.</p>
          </div>
        )}
      </div>
    </div>
  );
}
