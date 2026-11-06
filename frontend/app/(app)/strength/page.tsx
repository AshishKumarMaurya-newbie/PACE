"use client";

import { useEffect, useState } from "react";
import { Dumbbell, Plus, Trash2 } from "lucide-react";
import { api } from "@/lib/api";

type SetInput = {
  repetitions: string;
  weight_kg: string;
  rest_seconds: string;
};
type ExerciseInput = { name: string; sets: SetInput[] };
type Workout = {
  id: string;
  title: string;
  started_at: string;
  duration_seconds: number | null;
  exercises: {
    name: string;
    sets: { repetitions: number; weight_kg: string | null }[];
  }[];
};
const emptySet = (): SetInput => ({
  repetitions: "8",
  weight_kg: "",
  rest_seconds: "90",
});

export default function StrengthPage() {
  const [workouts, setWorkouts] = useState<Workout[]>([]);
  const [exercises, setExercises] = useState<ExerciseInput[]>([
    { name: "", sets: [emptySet()] },
  ]);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  async function reload() {
    setWorkouts(await api<Workout[]>("/strength/workouts"));
  }
  useEffect(() => {
    reload().catch((cause: Error) => setError(cause.message));
  }, []);

  function updateExercise(index: number, patch: Partial<ExerciseInput>) {
    setExercises((current) =>
      current.map((item, position) =>
        position === index ? { ...item, ...patch } : item,
      ),
    );
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSaving(true);
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    try {
      await api("/strength/workouts", {
        method: "POST",
        body: JSON.stringify({
          title: form.get("title"),
          started_at: new Date(String(form.get("started_at"))).toISOString(),
          duration_seconds: form.get("duration_minutes")
            ? Number(form.get("duration_minutes")) * 60
            : null,
          exercises: exercises.map((exercise) => ({
            name: exercise.name,
            sets: exercise.sets.map((set) => ({
              repetitions: Number(set.repetitions),
              weight_kg: set.weight_kg ? Number(set.weight_kg) : null,
              rest_seconds: set.rest_seconds ? Number(set.rest_seconds) : null,
            })),
          })),
        }),
      });
      formElement.reset();
      setExercises([{ name: "", sets: [emptySet()] }]);
      await reload();
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Unable to save workout.",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="page-content">
      <div className="page-heading-row">
        <div>
          <div className="page-kicker">Strength training</div>
          <h1 className="page-heading">Build the work.</h1>
          <p className="page-subtitle">
            Exercises, sets, reps, and load. Your log, exactly as completed.
          </p>
        </div>
      </div>
      {error && (
        <div className="error-message" role="alert">
          {error}
        </div>
      )}
      <form className="content-panel form-panel" onSubmit={submit}>
        <h2 style={{ margin: "0 0 18px", fontSize: 16 }}>Log a workout</h2>
        <div className="form-grid">
          <div className="field">
            <label htmlFor="title">Workout name</label>
            <input
              id="title"
              name="title"
              required
              maxLength={160}
              placeholder="Upper body"
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
            />
          </div>
        </div>
        {exercises.map((exercise, exerciseIndex) => (
          <section
            key={exerciseIndex}
            style={{
              marginTop: 22,
              paddingTop: 18,
              borderTop: "1px solid var(--line)",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                gap: 10,
              }}
            >
              <h3 style={{ margin: 0, fontSize: 14 }}>
                Exercise {exerciseIndex + 1}
              </h3>
              {exercises.length > 1 && (
                <button
                  className="signout"
                  type="button"
                  aria-label="Remove exercise"
                  onClick={() =>
                    setExercises((current) =>
                      current.filter((_, index) => index !== exerciseIndex),
                    )
                  }
                >
                  <Trash2 size={16} />
                </button>
              )}
            </div>
            <div className="field" style={{ marginTop: 12 }}>
              <label htmlFor={`exercise-${exerciseIndex}`}>Exercise name</label>
              <input
                id={`exercise-${exerciseIndex}`}
                required
                maxLength={120}
                value={exercise.name}
                onChange={(event) =>
                  updateExercise(exerciseIndex, { name: event.target.value })
                }
                placeholder="Bench press"
              />
            </div>
            {exercise.sets.map((set, setIndex) => (
              <div
                key={setIndex}
                className="form-grid"
                style={{
                  marginTop: 12,
                  gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
                }}
              >
                <div className="field">
                  <label htmlFor={`reps-${exerciseIndex}-${setIndex}`}>
                    Set {setIndex + 1} · reps
                  </label>
                  <input
                    id={`reps-${exerciseIndex}-${setIndex}`}
                    type="number"
                    min="1"
                    max="1000"
                    required
                    value={set.repetitions}
                    onChange={(event) =>
                      updateExercise(exerciseIndex, {
                        sets: exercise.sets.map((row, i) =>
                          i === setIndex
                            ? { ...row, repetitions: event.target.value }
                            : row,
                        ),
                      })
                    }
                  />
                </div>
                <div className="field">
                  <label htmlFor={`weight-${exerciseIndex}-${setIndex}`}>
                    Weight (kg)
                  </label>
                  <input
                    id={`weight-${exerciseIndex}-${setIndex}`}
                    type="number"
                    min="0"
                    max="2000"
                    step="0.25"
                    value={set.weight_kg}
                    placeholder="Bodyweight"
                    onChange={(event) =>
                      updateExercise(exerciseIndex, {
                        sets: exercise.sets.map((row, i) =>
                          i === setIndex
                            ? { ...row, weight_kg: event.target.value }
                            : row,
                        ),
                      })
                    }
                  />
                </div>
                <div className="field">
                  <label htmlFor={`rest-${exerciseIndex}-${setIndex}`}>
                    Rest (sec)
                  </label>
                  <input
                    id={`rest-${exerciseIndex}-${setIndex}`}
                    type="number"
                    min="0"
                    max="7200"
                    value={set.rest_seconds}
                    onChange={(event) =>
                      updateExercise(exerciseIndex, {
                        sets: exercise.sets.map((row, i) =>
                          i === setIndex
                            ? { ...row, rest_seconds: event.target.value }
                            : row,
                        ),
                      })
                    }
                  />
                </div>
              </div>
            ))}
            <button
              className="button-secondary"
              type="button"
              style={{ marginTop: 12 }}
              onClick={() =>
                updateExercise(exerciseIndex, {
                  sets: [...exercise.sets, emptySet()],
                })
              }
            >
              <Plus size={14} />
              Add set
            </button>
          </section>
        ))}
        <div
          className="form-actions"
          style={{ justifyContent: "space-between" }}
        >
          <button
            className="button-secondary"
            type="button"
            onClick={() =>
              setExercises((current) => [
                ...current,
                { name: "", sets: [emptySet()] },
              ])
            }
          >
            <Plus size={15} />
            Add exercise
          </button>
          <button className="button-primary" type="submit" disabled={saving}>
            {saving ? "Saving..." : "Save workout"}
          </button>
        </div>
      </form>
      <div className="section-heading">
        <h2>Workout history</h2>
        <span className="table-caption">{workouts.length} logged</span>
      </div>
      <div className="activity-table">
        {workouts.length ? (
          workouts.map((workout) => {
            const sets = workout.exercises.flatMap((exercise) => exercise.sets);
            const volume = sets.reduce(
              (sum, set) => sum + Number(set.weight_kg ?? 0) * set.repetitions,
              0,
            );
            return (
              <article className="activity-row strength-row" key={workout.id}>
                <span className="activity-name">
                  <span className="activity-symbol">
                    <Dumbbell size={16} />
                  </span>
                  <span>
                    <span
                      className="activity-title"
                      style={{ display: "block" }}
                    >
                      {workout.title}
                    </span>
                    <span
                      className="activity-date"
                      style={{ display: "block" }}
                    >
                      {new Date(workout.started_at).toLocaleDateString()} ·{" "}
                      {workout.exercises.map((item) => item.name).join(", ")}
                    </span>
                  </span>
                </span>
                <span>
                  <span className="table-caption" style={{ display: "block" }}>
                    Exercises
                  </span>
                  <span className="table-value">
                    {workout.exercises.length}
                  </span>
                </span>
                <span>
                  <span className="table-caption" style={{ display: "block" }}>
                    Sets
                  </span>
                  <span className="table-value">{sets.length}</span>
                </span>
                <span>
                  <span className="table-caption" style={{ display: "block" }}>
                    Volume
                  </span>
                  <span className="table-value">
                    {volume.toLocaleString()} kg
                  </span>
                </span>
              </article>
            );
          })
        ) : (
          <div className="empty-state">
            <span className="empty-icon">
              <Dumbbell size={20} />
            </span>
            <h3>No strength workouts yet</h3>
            <p>Your completed exercises and set volume will appear here.</p>
          </div>
        )}
      </div>
    </div>
  );
}
