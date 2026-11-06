"use client";

import { useEffect, useMemo, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { api, type Activity } from "@/lib/api";

type PlannedWorkout = {
  id: string;
  title: string;
  activity_type: string;
  scheduled_date: string;
  is_completed: boolean;
};
type CalendarData = {
  activities: Activity[];
  planned_workouts: PlannedWorkout[];
  strength_workouts: { id: string; title: string; started_at: string }[];
};

function dateKey(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

export default function CalendarPage() {
  const [month, setMonth] = useState(
    () => new Date(new Date().getFullYear(), new Date().getMonth(), 1),
  );
  const [view, setView] = useState<"month" | "week">("month");
  const [data, setData] = useState<CalendarData>({
    activities: [],
    planned_workouts: [],
    strength_workouts: [],
  });
  const [error, setError] = useState("");
  const range = useMemo(() => {
    if (view === "week") {
      const start = new Date(month);
      start.setDate(start.getDate() - ((start.getDay() + 6) % 7));
      const end = new Date(start);
      end.setDate(end.getDate() + 6);
      return { start, end };
    }
    const start = new Date(month.getFullYear(), month.getMonth(), 1);
    const end = new Date(month.getFullYear(), month.getMonth() + 1, 0);
    return { start, end };
  }, [month, view]);
  const startIso = dateKey(range.start);
  const endIso = dateKey(range.end);
  const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  useEffect(() => {
    api<CalendarData>(
      `/training/calendar?start=${startIso}&end=${endIso}&timezone=${encodeURIComponent(timeZone)}`,
    )
      .then(setData)
      .catch((cause: Error) => setError(cause.message));
  }, [startIso, endIso, timeZone]);
  const days = useMemo(() => {
    const start =
      view === "month" ? new Date(range.start) : new Date(range.start);
    if (view === "month")
      start.setDate(start.getDate() - ((start.getDay() + 6) % 7));
    const total = view === "week" ? 7 : 42;
    return Array.from({ length: total }, (_, index) => {
      const day = new Date(start);
      day.setDate(day.getDate() + index);
      return day;
    });
  }, [range, view]);
  const shift = (direction: number) =>
    setMonth((current) => {
      const next = new Date(current);
      view === "month"
        ? next.setMonth(next.getMonth() + direction)
        : next.setDate(next.getDate() + direction * 7);
      return next;
    });
  const keyOf = dateKey;
  return (
    <div className="page-content">
      <div className="page-heading-row">
        <div>
          <div className="page-kicker">Training calendar</div>
          <h1 className="page-heading">Show up, then look back.</h1>
          <p className="page-subtitle">
            Planned sessions and completed activities share the same calendar.
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            className={`button-secondary${view === "week" ? " active" : ""}`}
            type="button"
            onClick={() => setView("week")}
          >
            Week
          </button>
          <button
            className="button-secondary"
            type="button"
            onClick={() => setView("month")}
          >
            Month
          </button>
        </div>
      </div>
      {error && (
        <div className="error-message" role="alert">
          {error}
        </div>
      )}
      <div className="content-panel" style={{ padding: 16 }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: 15,
          }}
        >
          <button
            className="button-secondary"
            aria-label="Previous"
            onClick={() => shift(-1)}
          >
            <ChevronLeft size={16} />
          </button>
          <strong>
            {view === "month"
              ? month.toLocaleDateString("en", {
                  month: "long",
                  year: "numeric",
                })
              : `${range.start.toLocaleDateString()} – ${range.end.toLocaleDateString()}`}
          </strong>
          <button
            className="button-secondary"
            aria-label="Next"
            onClick={() => shift(1)}
          >
            <ChevronRight size={16} />
          </button>
        </div>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(7, minmax(0, 1fr))",
            gap: 5,
          }}
        >
          {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((day) => (
            <div
              key={day}
              className="table-caption"
              style={{ padding: "5px 3px", textAlign: "center" }}
            >
              {day}
            </div>
          ))}
          {days.map((day) => {
            const key = keyOf(day);
            const completed =
              data.activities.filter(
                (item) => localDateKey(item.started_at, timeZone) === key,
              ).length +
              data.strength_workouts.filter(
                (item) => localDateKey(item.started_at, timeZone) === key,
              ).length;
            const planned = data.planned_workouts.filter(
              (item) => item.scheduled_date === key,
            );
            const inMonth = day.getMonth() === month.getMonth();
            return (
              <div
                key={key}
                style={{
                  minHeight: view === "week" ? 112 : 80,
                  padding: 7,
                  color:
                    inMonth || view === "week" ? "var(--ink)" : "var(--dim)",
                  background: "#151a16",
                  border: "1px solid var(--line)",
                  borderRadius: 4,
                }}
              >
                <div style={{ fontSize: 11 }}>{day.getDate()}</div>
                {completed > 0 && (
                  <div
                    title={`${completed} completed`}
                    style={{
                      width: 7,
                      height: 7,
                      marginTop: 7,
                      background: "var(--lime)",
                      borderRadius: 8,
                    }}
                  />
                )}
                {planned.some((item) => !item.is_completed) && (
                  <div
                    title="Planned"
                    style={{
                      width: 7,
                      height: 7,
                      marginTop: 4,
                      background: "var(--blue)",
                      borderRadius: 8,
                    }}
                  />
                )}
              </div>
            );
          })}
        </div>
        <div
          style={{
            display: "flex",
            gap: 16,
            marginTop: 14,
            color: "var(--muted)",
            fontSize: 11,
          }}
        >
          <span>
            <i
              style={{
                display: "inline-block",
                width: 8,
                height: 8,
                marginRight: 6,
                background: "var(--lime)",
                borderRadius: 8,
              }}
            />
            Completed
          </span>
          <span>
            <i
              style={{
                display: "inline-block",
                width: 8,
                height: 8,
                marginRight: 6,
                background: "var(--blue)",
                borderRadius: 8,
              }}
            />
            Planned
          </span>
        </div>
      </div>
      <div className="section-heading">
        <h2>Sessions in view</h2>
      </div>
      <div className="activity-table">
        {[
          ...data.activities.map((item) => ({
            title: item.title,
            date: localDateKey(item.started_at, timeZone),
            type: item.activity_type,
            status: "Completed",
          })),
          ...data.strength_workouts.map((item) => ({
            title: item.title,
            date: localDateKey(item.started_at, timeZone),
            type: "strength",
            status: "Completed",
          })),
          ...data.planned_workouts.map((item) => ({
            title: item.title,
            date: item.scheduled_date,
            type: item.activity_type,
            status: item.is_completed ? "Completed" : "Planned",
          })),
        ]
          .sort((a, b) => a.date.localeCompare(b.date))
          .map((item, index) => (
            <article
              className="activity-row"
              key={`${item.date}-${item.title}-${index}`}
            >
              <span className="activity-title">{item.title}</span>
              <span className="table-value">{item.type}</span>
              <span className="table-value">
                {new Date(`${item.date}T12:00:00`).toLocaleDateString()}
              </span>
              <span className="table-value">{item.status}</span>
            </article>
          ))}
        {!data.activities.length &&
          !data.strength_workouts.length &&
          !data.planned_workouts.length && (
            <div className="empty-state">
              <h3>A clear week</h3>
              <p>Log an activity or add a planned workout to see it here.</p>
            </div>
          )}
      </div>
    </div>
  );
}

function localDateKey(value: string, timeZone: string) {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date(value));
  const part = (type: string) =>
    parts.find((item) => item.type === type)?.value ?? "";
  return `${part("year")}-${part("month")}-${part("day")}`;
}
