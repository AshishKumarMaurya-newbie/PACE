"use client";

import { useEffect, useState } from "react";
import { CalendarPlus, Plus } from "lucide-react";
import { api } from "@/lib/api";

type Plan = {
  id: string;
  title: string;
  goal: string;
  target_date: string | null;
  is_active: boolean;
};
type Planned = {
  id: string;
  plan_id: string;
  title: string;
  activity_type: string;
  scheduled_date: string;
  is_completed: boolean;
};

export default function TrainingPage() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [sessions, setSessions] = useState<Planned[]>([]);
  const [error, setError] = useState("");
  async function reload() {
    const [planList, calendar] = await Promise.all([
      api<Plan[]>("/training/plans"),
      api<{ planned_workouts: Planned[] }>(
        `/training/calendar?start=${new Date().toISOString().slice(0, 10)}&end=${new Date(Date.now() + 90 * 86400000).toISOString().slice(0, 10)}`,
      ),
    ]);
    setPlans(planList);
    setSessions(calendar.planned_workouts);
  }
  useEffect(() => {
    reload().catch((cause: Error) => setError(cause.message));
  }, []);

  async function createPlan(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const data = new FormData(formElement);
    setError("");
    try {
      await api("/training/plans", {
        method: "POST",
        body: JSON.stringify({
          title: data.get("title"),
          goal: data.get("goal"),
          target_date: data.get("target_date") || null,
        }),
      });
      formElement.reset();
      await reload();
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Unable to create plan.",
      );
    }
  }

  async function addSession(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const data = new FormData(formElement);
    const planId = String(data.get("plan_id"));
    setError("");
    try {
      await api(`/training/plans/${planId}/workouts`, {
        method: "POST",
        body: JSON.stringify({
          title: data.get("title"),
          activity_type: data.get("activity_type"),
          scheduled_date: data.get("scheduled_date"),
        }),
      });
      formElement.reset();
      await reload();
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Unable to schedule workout.",
      );
    }
  }

  async function complete(id: string) {
    try {
      await api(`/training/workouts/${id}/complete`, { method: "POST" });
      await reload();
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Unable to update session.",
      );
    }
  }

  return (
    <div className="page-content">
      <div className="page-heading-row">
        <div>
          <div className="page-kicker">Training plans</div>
          <h1 className="page-heading">Give your weeks a shape.</h1>
          <p className="page-subtitle">
            Set a goal, place sessions on the calendar, and track what gets
            done.
          </p>
        </div>
      </div>
      {error && (
        <div className="error-message" role="alert">
          {error}
        </div>
      )}
      <div
        style={{
          display: "grid",
          gridTemplateColumns:
            "repeat(auto-fit, minmax(min(100%, 340px), 1fr))",
          gap: 14,
        }}
      >
        <form className="content-panel form-panel" onSubmit={createPlan}>
          <h2 style={{ margin: "0 0 18px", fontSize: 16 }}>Create a plan</h2>
          <div className="field">
            <label htmlFor="title">Plan name</label>
            <input
              id="title"
              name="title"
              maxLength={160}
              required
              placeholder="Build toward a 10K"
            />
          </div>
          <div className="field" style={{ marginTop: 14 }}>
            <label htmlFor="goal">Goal</label>
            <select id="goal" name="goal">
              <option>Improve endurance</option>
              <option>Increase running distance</option>
              <option>Improve 5K time</option>
              <option>Complete a 10K</option>
              <option>Complete a half marathon</option>
              <option>Build strength</option>
              <option>General fitness</option>
            </select>
          </div>
          <div className="field" style={{ marginTop: 14 }}>
            <label htmlFor="target_date">Target date</label>
            <input id="target_date" name="target_date" type="date" />
          </div>
          <div className="form-actions">
            <button className="button-primary" type="submit">
              <Plus size={15} />
              Create plan
            </button>
          </div>
        </form>
        <form className="content-panel form-panel" onSubmit={addSession}>
          <h2 style={{ margin: "0 0 18px", fontSize: 16 }}>
            Schedule a session
          </h2>
          <div className="field">
            <label htmlFor="plan_id">Plan</label>
            <select
              id="plan_id"
              name="plan_id"
              required
              disabled={!plans.length}
            >
              {plans.map((plan) => (
                <option value={plan.id} key={plan.id}>
                  {plan.title}
                </option>
              ))}
            </select>
          </div>
          <div className="field" style={{ marginTop: 14 }}>
            <label htmlFor="session_title">Session</label>
            <input
              id="session_title"
              name="title"
              maxLength={160}
              required
              placeholder="Easy recovery run"
            />
          </div>
          <div className="field" style={{ marginTop: 14 }}>
            <label htmlFor="activity_type">Activity type</label>
            <select id="activity_type" name="activity_type">
              <option value="run">Running</option>
              <option value="ride">Cycling</option>
              <option value="walk">Walking</option>
              <option value="strength">Strength</option>
              <option value="rest">Rest day</option>
              <option value="other">Other</option>
            </select>
          </div>
          <div className="field" style={{ marginTop: 14 }}>
            <label htmlFor="scheduled_date">Date</label>
            <input
              id="scheduled_date"
              name="scheduled_date"
              type="date"
              required
            />
          </div>
          <div className="form-actions">
            <button
              className="button-primary"
              type="submit"
              disabled={!plans.length}
            >
              <CalendarPlus size={15} />
              Schedule
            </button>
          </div>
        </form>
      </div>
      <div className="section-heading">
        <h2>Your plans</h2>
      </div>
      <div className="activity-table">
        {plans.length ? (
          plans.map((plan) => (
            <article className="activity-row" key={plan.id}>
              <span className="activity-title">
                {plan.title}
                <span className="activity-date" style={{ display: "block" }}>
                  {plan.goal}
                </span>
              </span>
              <span className="table-value">
                {plan.target_date
                  ? new Date(
                      `${plan.target_date}T12:00:00`,
                    ).toLocaleDateString()
                  : "No target"}
              </span>
              <span className="table-value">
                {plan.is_active ? "Active" : "Complete"}
              </span>
            </article>
          ))
        ) : (
          <div className="empty-state">
            <h3>No training plans yet</h3>
            <p>Create a plan to organize upcoming sessions.</p>
          </div>
        )}
      </div>
      <div className="section-heading">
        <h2>Upcoming sessions</h2>
      </div>
      <div className="activity-table">
        {sessions.length ? (
          sessions.map((session) => (
            <article className="activity-row" key={session.id}>
              <span className="activity-title">
                {session.title}
                <span className="activity-date" style={{ display: "block" }}>
                  {session.activity_type} ·{" "}
                  {new Date(
                    `${session.scheduled_date}T12:00:00`,
                  ).toLocaleDateString()}
                </span>
              </span>
              <span className="table-value">
                {session.is_completed ? "Completed" : "Planned"}
              </span>
              {!session.is_completed && (
                <button
                  className="button-secondary"
                  type="button"
                  onClick={() => complete(session.id)}
                >
                  Mark done
                </button>
              )}
            </article>
          ))
        ) : (
          <div className="empty-state">
            <h3>No upcoming sessions</h3>
            <p>Add a session to your plan and it will appear here.</p>
          </div>
        )}
      </div>
    </div>
  );
}
