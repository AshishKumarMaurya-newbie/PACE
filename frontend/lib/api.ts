export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...init.headers,
    },
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const message =
      typeof body?.detail === "string"
        ? body.detail
        : "Something went wrong. Please try again.";
    throw new ApiError(message, response.status);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export type Activity = {
  id: string;
  activity_type: string;
  title: string;
  started_at: string;
  duration_seconds: number;
  distance_m: number | null;
  elevation_gain_m: number | null;
  average_heart_rate: number | null;
  notes: string | null;
};

export type DashboardSummary = {
  total_activities: number;
  total_distance_m: number;
  total_duration_seconds: number;
  week_activities: number;
  week_distance_m: number;
  month_activities: number;
  recent_activities: Activity[];
  recent_strength_workouts: {
    id: string;
    title: string;
    started_at: string;
    duration_seconds: number | null;
  }[];
};

export type User = { id: string; email: string; full_name: string };
