"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

type ProjectCard = {
  id: string;
  name: string;
  description: string;
  original_filename: string;
  status: string;
  file_type: string;
  file_size: number;
  created_at: string;
};

type RunStatus = {
  run_id: string;
  project_id: string;
  status: string;
  progress: number;
  current_stage: string;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
};

type TopValue = {
  value: string;
  count: number;
};

type NumericStat = {
  column_name: string;
  count: number;
  mean: number | null;
  std_dev: number | null;
  min: number | null;
  q1: number | null;
  median: number | null;
  q3: number | null;
  max: number | null;
  null_count: number;
};

type CategoricalStat = {
  column_name: string;
  count: number;
  cardinality: number;
  min_count_freq: number;
  max_count_freq: number;
  lowest_freq_value: string;
  highest_freq_value: string;
  null_count: number;
  top_values: TopValue[];
};

type DateStat = {
  column_name: string;
  count: number;
  min_date: string;
  max_date: string;
  null_count: number;
};

type Metrics = {
  run_id: string;
  numeric_stats: NumericStat[];
  categorical_stats: CategoricalStat[];
  date_stats: DateStat[];
  correlation_stats: Record<string, Record<string, number>>;
  pps_stats: Record<string, Record<string, number>>;
};

const apiBaseUrl = "http://localhost:8000";

function buildMatrixEntries(matrix: Record<string, Record<string, number>>) {
  const rows = Object.keys(matrix);
  const columns = Array.from(
    new Set(rows.flatMap((row) => Object.keys(matrix[row] ?? {}))),
  );

  return { rows, columns };
}

function getCorrelationHeatColor(value: number) {
  if (value > 0) {
    return `rgba(201, 95, 45, ${Math.max(0.12, Math.min(Math.abs(value), 1))})`;
  }

  if (value < 0) {
    return `rgba(58, 110, 165, ${Math.max(0.12, Math.min(Math.abs(value), 1))})`;
  }

  return "rgba(29, 41, 61, 0.06)";
}

function getPpsHeatColor(value: number) {
  return `rgba(39, 126, 86, ${Math.max(0.08, Math.min(value, 1))})`;
}

function HeatmapTable({
  title,
  eyebrow,
  matrix,
  variant,
}: {
  title: string;
  eyebrow: string;
  matrix: Record<string, Record<string, number>>;
  variant: "correlation" | "pps";
}) {
  const { rows, columns } = buildMatrixEntries(matrix);

  if (rows.length === 0 || columns.length === 0) {
    return (
      <article className="detail-card detail-section-card">
        <div className="section-heading">
          <div>
            <p className="eyebrow">{eyebrow}</p>
            <h2>{title}</h2>
          </div>
        </div>
        <p className="empty-metrics-copy">No matrix data available for this run.</p>
      </article>
    );
  }

  return (
    <article className="detail-card detail-section-card">
      <div className="section-heading">
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h2>{title}</h2>
        </div>
      </div>

      <div className="heatmap-shell">
        <div className="heatmap-frame">
          <table className="heatmap-table">
            <thead>
              <tr>
                <th>Column</th>
                {columns.map((column) => (
                  <th key={column}>{column}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row}>
                  <th>{row}</th>
                  {columns.map((column) => {
                    const rawValue = matrix[row]?.[column] ?? 0;
                    const cellColor =
                      variant === "correlation"
                        ? getCorrelationHeatColor(rawValue)
                        : getPpsHeatColor(rawValue);

                    return (
                      <td
                        key={`${row}-${column}`}
                        className="heatmap-cell"
                        style={{ backgroundColor: cellColor }}
                        title={`${row} -> ${column}: ${rawValue}`}
                      >
                        {rawValue.toFixed(3)}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </article>
  );
}

export default function ProjectDetailPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const [projectId, setProjectId] = useState<string>("");
  const [project, setProject] = useState<ProjectCard | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [runStatus, setRunStatus] = useState<RunStatus | null>(null);
  const [metrics, setMetrics] = useState<Metrics | null>(null);

  useEffect(() => {
    params.then((resolvedParams) => setProjectId(resolvedParams.projectId));
  }, [params]);

  useEffect(() => {
    if (!projectId) {
      return;
    }

    async function loadProject() {
      try {
        setIsLoading(true);
        setError("");
        const response = await fetch(`${apiBaseUrl}/projects/${projectId}`, {
          cache: "no-store",
        });
        if (!response.ok) {
          throw new Error("Failed to load project");
        }

        const data = (await response.json()) as ProjectCard;
        setProject(data);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Something went wrong");
      } finally {
        setIsLoading(false);
      }
    }

    void loadProject();
  }, [projectId]);

  useEffect(() => {
    if (!runStatus?.run_id) {
      return;
    }

    const eventSource = new EventSource(`${apiBaseUrl}/runs/${runStatus.run_id}/events`);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as {
          run_id: string;
          project_id: string;
          status: string;
          progress: number;
          current_stage: string;
          message?: string;
          timestamp?: string;
        };

        setRunStatus((current) => ({
          run_id: data.run_id,
          project_id: data.project_id,
          status: data.status,
          progress: data.progress,
          current_stage: data.current_stage,
          error_message: current?.error_message ?? null,
          created_at: current?.created_at ?? data.timestamp ?? new Date().toISOString(),
          started_at: current?.started_at ?? null,
          completed_at:
            data.status === "completed" ? data.timestamp ?? new Date().toISOString() : null,
        }));

        if (data.message) {
          setMessage(data.message);
        }

        if (data.status === "completed") {
          setIsRunning(false);
          eventSource.close();
          void pollRunStatus(data.run_id);
          void loadMetrics(data.run_id);
        }

        if (data.status === "failed") {
          setIsRunning(false);
          setError(data.message || "Profiling run failed");
          eventSource.close();
          void pollRunStatus(data.run_id);
        }
      } catch {
        setError("Failed to parse run progress event");
      }
    };

    eventSource.onerror = () => {
      eventSource.close();
      void pollRunStatus(runStatus.run_id);
    };

    return () => eventSource.close();
  }, [runStatus?.run_id, runStatus?.status]);

  async function handleStartProfiling() {
    if (!projectId) {
      return;
    }

    try {
      setError("");
      setMessage("");
      setMetrics(null);
      setIsRunning(true);
      const response = await fetch(`${apiBaseUrl}/projects/${projectId}/run`, {
        method: "POST",
      });

      if (!response.ok) {
        throw new Error("Failed to start profiling run");
      }

      const data = (await response.json()) as {
        run_id: string;
        project_id: string;
        status: string;
        progress: number;
        current_stage: string;
        created_at: string;
      };

      setRunStatus({
        run_id: data.run_id,
        project_id: data.project_id,
        status: data.status,
        progress: data.progress,
        current_stage: data.current_stage,
        error_message: null,
        created_at: data.created_at,
        started_at: null,
        completed_at: null,
      });
      setMessage("Profiling run started");
    } catch (runError) {
      setIsRunning(false);
      setError(runError instanceof Error ? runError.message : "Something went wrong");
    }
  }

  async function pollRunStatus(runId: string) {
    try {
      const response = await fetch(`${apiBaseUrl}/runs/${runId}/status`, {
        cache: "no-store",
      });
      if (!response.ok) {
        throw new Error("Failed to fetch run status");
      }

      const data = (await response.json()) as RunStatus;
      setRunStatus(data);
    } catch (statusError) {
      setError(statusError instanceof Error ? statusError.message : "Something went wrong");
      setIsRunning(false);
    }
  }

  async function loadMetrics(runId: string) {
    try {
      const response = await fetch(`${apiBaseUrl}/runs/${runId}/metrics`, {
        cache: "no-store",
      });
      if (!response.ok) {
        throw new Error("Failed to load profiling metrics");
      }

      const data = (await response.json()) as Metrics;
      setMetrics({
        ...data,
        numeric_stats: data.numeric_stats ?? [],
        categorical_stats: data.categorical_stats ?? [],
        date_stats: data.date_stats ?? [],
        correlation_stats: data.correlation_stats ?? {},
        pps_stats: data.pps_stats ?? {},
      });
      setMessage("Profiling completed successfully");
    } catch (metricsError) {
      setError(metricsError instanceof Error ? metricsError.message : "Something went wrong");
    }
  }

  function handleDownload(format: "json" | "csv") {
    if (!runStatus?.run_id) {
      return;
    }

    window.open(`${apiBaseUrl}/runs/${runStatus.run_id}/export/${format}`, "_blank");
  }

  return (
    <main className="workspace-page">
      <section className="workspace-board detail-board">
        <div className="detail-actions">
          <Link className="secondary-link" href="/workspace">
            Back to Workspace
          </Link>
        </div>

        {isLoading ? (
          <article className="empty-card">
            <h3>Loading project</h3>
            <p>Fetching project details from the backend.</p>
          </article>
        ) : error ? (
          <article className="empty-card">
            <h3>Unable to load project</h3>
            <p>{error}</p>
          </article>
        ) : project ? (
          <>
            <article className="detail-card">
              <p className="eyebrow">Project Detail</p>
              <div className="detail-heading">
                <div>
                  <h1 className="workspace-title">{project.name}</h1>
                  <p className="detail-subtitle">
                    Start profiling for this CSV and review stats after the run completes.
                  </p>
                </div>
                <button
                  className="primary-button"
                  type="button"
                  onClick={handleStartProfiling}
                  disabled={isRunning}
                >
                  {isRunning ? "Profiling..." : "Next Step"}
                </button>
              </div>

              {message ? <p className="status-message success-message">{message}</p> : null}
              {runStatus?.error_message ? (
                <p className="status-message error-message">{runStatus.error_message}</p>
              ) : null}

              <div className="detail-grid">
                <div className="detail-block">
                  <span className="detail-label">Uploaded File</span>
                  <p>{project.original_filename}</p>
                </div>
                <div className="detail-block">
                  <span className="detail-label">Project Status</span>
                  <p>{project.status}</p>
                </div>
                <div className="detail-block">
                  <span className="detail-label">Created At</span>
                  <p>{new Date(project.created_at).toLocaleString()}</p>
                </div>
                <div className="detail-block">
                  <span className="detail-label">File Type</span>
                  <p>{project.file_type}</p>
                </div>
                <div className="detail-block">
                  <span className="detail-label">File Size</span>
                  <p>{project.file_size} bytes</p>
                </div>
                <div className="detail-block detail-block-wide">
                  <span className="detail-label">Description</span>
                  <p>{project.description || "No description provided."}</p>
                </div>
              </div>
            </article>

            <article className="detail-card detail-section-card">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Run Status</p>
                  <h2>Profiling Progress</h2>
                </div>
                <span className="project-badge status-pill">
                  {runStatus?.status ?? "not started"}
                </span>
              </div>

              <div className="progress-shell">
                <div className="progress-track">
                  <div
                    className="progress-fill"
                    style={{ width: `${runStatus?.progress ?? 0}%` }}
                  />
                </div>
                <p className="progress-copy">
                  {runStatus
                    ? `${runStatus.current_stage} • ${runStatus.progress}%`
                    : "Run has not been started yet."}
                </p>
              </div>
            </article>

            {metrics ? (
              <section className="metrics-layout">
                <article className="detail-card detail-section-card">
                  <div className="section-heading">
                    <div>
                      <p className="eyebrow">Exports</p>
                      <h2>Download Results</h2>
                    </div>
                    <div className="export-actions">
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() => handleDownload("json")}
                      >
                        Download JSON
                      </button>
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() => handleDownload("csv")}
                      >
                        Download CSV
                      </button>
                    </div>
                  </div>
                </article>

                <article className="detail-card detail-section-card">
                  <div className="section-heading">
                    <div>
                      <p className="eyebrow">Numeric Stats</p>
                      <h2>Numeric Columns</h2>
                    </div>
                  </div>
                  <div className="table-shell">
                    <table className="stats-table">
                      <thead>
                        <tr>
                          <th>Column</th>
                          <th>Count</th>
                          <th>Mean</th>
                          <th>Median</th>
                          <th>Min</th>
                          <th>Q1</th>
                          <th>Q3</th>
                          <th>Max</th>
                          <th>Nulls</th>
                        </tr>
                      </thead>
                      <tbody>
                        {metrics.numeric_stats.map((stat) => (
                          <tr key={stat.column_name}>
                            <td>{stat.column_name}</td>
                            <td>{stat.count}</td>
                            <td>{stat.mean ?? "-"}</td>
                            <td>{stat.median ?? "-"}</td>
                            <td>{stat.min ?? "-"}</td>
                            <td>{stat.q1 ?? "-"}</td>
                            <td>{stat.q3 ?? "-"}</td>
                            <td>{stat.max ?? "-"}</td>
                            <td>{stat.null_count}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </article>

                <article className="detail-card detail-section-card">
                  <div className="section-heading">
                    <div>
                      <p className="eyebrow">Categorical Stats</p>
                      <h2>Categorical Columns</h2>
                    </div>
                  </div>
                  <div className="table-shell">
                    <table className="stats-table">
                      <thead>
                        <tr>
                          <th>Column</th>
                          <th>Count</th>
                          <th>Cardinality</th>
                          <th>Highest Freq</th>
                          <th>Lowest Freq</th>
                          <th>Nulls</th>
                        </tr>
                      </thead>
                      <tbody>
                        {metrics.categorical_stats.map((stat) => (
                          <tr key={stat.column_name}>
                            <td>{stat.column_name}</td>
                            <td>{stat.count}</td>
                            <td>{stat.cardinality}</td>
                            <td>{stat.highest_freq_value}</td>
                            <td>{stat.lowest_freq_value}</td>
                            <td>{stat.null_count}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </article>

                <article className="detail-card detail-section-card">
                  <div className="section-heading">
                    <div>
                      <p className="eyebrow">Date Stats</p>
                      <h2>Date Columns</h2>
                    </div>
                  </div>
                  <div className="table-shell">
                    <table className="stats-table">
                      <thead>
                        <tr>
                          <th>Column</th>
                          <th>Count</th>
                          <th>Min Date</th>
                          <th>Max Date</th>
                          <th>Nulls</th>
                        </tr>
                      </thead>
                      <tbody>
                        {metrics.date_stats.map((stat) => (
                          <tr key={stat.column_name}>
                            <td>{stat.column_name}</td>
                            <td>{stat.count}</td>
                            <td>{new Date(stat.min_date).toLocaleString()}</td>
                            <td>{new Date(stat.max_date).toLocaleString()}</td>
                            <td>{stat.null_count}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </article>

                <HeatmapTable
                  title="Correlation Matrix"
                  eyebrow="Correlation"
                  matrix={metrics.correlation_stats}
                  variant="correlation"
                />

                <HeatmapTable
                  title="Predictive Power Scores"
                  eyebrow="PPS"
                  matrix={metrics.pps_stats}
                  variant="pps"
                />
              </section>
            ) : null}
          </>
        ) : (
          <article className="empty-card">
            <h3>Project not found</h3>
            <p>The selected project does not exist in the current workspace.</p>
          </article>
        )}
      </section>
    </main>
  );
}
