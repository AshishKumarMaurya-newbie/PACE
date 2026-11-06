"use client";

import { useEffect, useState } from "react";
import { Trophy } from "lucide-react";
import { api } from "@/lib/api";

type RecordEntry = {
  category: string;
  value: number;
  unit: string;
  achieved_at: string;
  source: string;
};

export default function RecordsPage() {
  const [records, setRecords] = useState<RecordEntry[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    api<{ records: RecordEntry[] }>("/records")
      .then((result) => setRecords(result.records))
      .catch((cause: Error) => setError(cause.message));
  }, []);
  return (
    <div className="page-content">
      <div className="page-heading-row">
        <div>
          <div className="page-kicker">Personal records</div>
          <h1 className="page-heading">Milestones, earned.</h1>
          <p className="page-subtitle">
            Only records supported by your logged sessions are shown.
          </p>
        </div>
      </div>
      {error && (
        <div className="error-message" role="alert">
          {error}
        </div>
      )}
      <div className="activity-table">
        {records.length ? (
          records.map((record) => (
            <article
              className="activity-row"
              key={`${record.category}-${record.achieved_at}`}
            >
              <span className="activity-name">
                <span className="activity-symbol">
                  <Trophy size={16} />
                </span>
                <span>
                  <span className="activity-title" style={{ display: "block" }}>
                    {record.category}
                  </span>
                  <span className="activity-date" style={{ display: "block" }}>
                    {record.source} ·{" "}
                    {new Date(record.achieved_at).toLocaleDateString()}
                  </span>
                </span>
              </span>
              <span
                className="table-value"
                style={{ gridColumn: "span 2", fontSize: 17, fontWeight: 700 }}
              >
                {record.value.toLocaleString()} {record.unit}
              </span>
            </article>
          ))
        ) : (
          <div className="empty-state">
            <span className="empty-icon">
              <Trophy size={20} />
            </span>
            <h3>Records will come from your log</h3>
            <p>
              Longest recorded run and strength bests appear when your
              activities include enough detail. No benchmark times are
              estimated.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
