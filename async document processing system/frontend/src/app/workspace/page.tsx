"use client";

import Link from "next/link";
import { ChangeEvent, FormEvent, useEffect, useState } from "react";

type ProjectCard = {
  id: string;
  name: string;
  description: string;
  fileName: string;
  status: string;
  createdAt: string;
};

const apiBaseUrl = "http://localhost:8000";

export default function WorkspacePage() {
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [projects, setProjects] = useState<ProjectCard[]>([]);
  const [projectName, setProjectName] = useState("");
  const [description, setDescription] = useState("");
  const [fileName, setFileName] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [sortBy, setSortBy] = useState("created_at");
  const [sortOrder, setSortOrder] = useState("desc");

  useEffect(() => {
    void loadProjects();
  }, [search, statusFilter, sortBy, sortOrder]);

  async function loadProjects() {
    try {
      setIsLoading(true);
      setError("");
      const queryParams = new URLSearchParams();
      if (search.trim()) {
        queryParams.set("search", search.trim());
      }
      if (statusFilter !== "all") {
        queryParams.set("status", statusFilter);
      }
      queryParams.set("sort_by", sortBy);
      queryParams.set("sort_order", sortOrder);

      const response = await fetch(
        `${apiBaseUrl}/projects?${queryParams.toString()}`,
        { cache: "no-store" },
      );
      if (!response.ok) {
        throw new Error("Failed to load projects");
      }

      const data = (await response.json()) as Array<{
        id: string;
        name: string;
        description: string;
        original_filename: string;
        status: string;
        created_at: string;
      }>;

      setProjects(
        data.map((project) => ({
          id: project.id,
          name: project.name,
          description: project.description,
          fileName: project.original_filename,
          status: project.status,
          createdAt: new Date(project.created_at).toLocaleString(),
        })),
      );
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Something went wrong");
    } finally {
      setIsLoading(false);
    }
  }

  function resetForm() {
    setProjectName("");
    setDescription("");
    setFileName("");
    setSelectedFile(null);
  }

  async function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!projectName.trim() || !selectedFile) {
      return;
    }

    const formData = new FormData();
    formData.append("name", projectName.trim());
    formData.append("description", description.trim());
    formData.append("file", selectedFile);

    try {
      setIsSaving(true);
      setError("");
      setMessage("");
      const response = await fetch(`${apiBaseUrl}/projects`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = (await response.json().catch(() => null)) as
          | { detail?: string }
          | null;
        throw new Error(errorData?.detail || "Failed to create project");
      }

      await loadProjects();
      setMessage("Project created successfully");
      resetForm();
      setIsFormOpen(false);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Something went wrong");
    } finally {
      setIsSaving(false);
    }
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const nextFile = event.target.files?.[0] ?? null;
    setSelectedFile(nextFile);
    setFileName(nextFile?.name ?? "");
  }

  async function handleDelete(projectId: string) {
    try {
      setError("");
      setMessage("");
      const response = await fetch(`${apiBaseUrl}/projects/${projectId}`, {
        method: "DELETE",
      });

      if (!response.ok) {
        const errorData = (await response.json().catch(() => null)) as
          | { detail?: string }
          | null;
        throw new Error(errorData?.detail || "Failed to delete project");
      }

      const data = (await response.json()) as { message: string };
      setProjects((currentProjects) =>
        currentProjects.filter((project) => project.id !== projectId),
      );
      setMessage(data.message);
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "Something went wrong");
    }
  }

  return (
    <main className="workspace-page">
      <section className="workspace-board">
        <header className="workspace-header">
          <div className="workspace-header-side">
            <button
              className="primary-button"
              type="button"
              onClick={() => setIsFormOpen(true)}
            >
              Create Project
            </button>
          </div>

          <div className="workspace-header-center">
            <p className="eyebrow">Workspace</p>
            <h1 className="workspace-title">Workspace</h1>
          </div>

          <div className="workspace-header-side workspace-header-side-right">
            <Link className="secondary-link" href="/">
              Back to Home
            </Link>
          </div>
        </header>

        {isFormOpen ? (
          <section className="project-form-shell">
            <div className="form-heading">
              <h2>Create New Project</h2>
              <button
                className="ghost-button"
                type="button"
                onClick={() => {
                  resetForm();
                  setIsFormOpen(false);
                }}
              >
                Close
              </button>
            </div>

            <form className="project-form" onSubmit={handleSave}>
              <label className="form-field">
                <span>Project Name</span>
                <input
                  type="text"
                  value={projectName}
                  onChange={(event) => setProjectName(event.target.value)}
                  placeholder="Customer Churn Profiling"
                  required
                />
              </label>

              <label className="form-field">
                <span>Upload File</span>
                <input type="file" accept=".csv" onChange={handleFileChange} required />
                {fileName ? <small>Selected file: {fileName}</small> : null}
              </label>

              <label className="form-field">
                <span>Description of File</span>
                <textarea
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                  placeholder="Optional notes about the dataset, source, or profiling purpose"
                  rows={4}
                />
              </label>

              <div className="form-actions">
                <button className="primary-button" type="submit" disabled={isSaving}>
                  {isSaving ? "Saving..." : "Save"}
                </button>
              </div>
            </form>
          </section>
        ) : null}

        {message ? <p className="status-message success-message">{message}</p> : null}
        {error ? <p className="status-message error-message">{error}</p> : null}

        <section className="workspace-toolbar">
          <label className="toolbar-field">
            <span>Search</span>
            <input
              type="text"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search by name, description, or file"
            />
          </label>

          <label className="toolbar-field">
            <span>Status</span>
            <select
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value)}
            >
              <option value="all">All</option>
              <option value="queued">Queued</option>
              <option value="processing">Processing</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
            </select>
          </label>

          <label className="toolbar-field">
            <span>Sort By</span>
            <select value={sortBy} onChange={(event) => setSortBy(event.target.value)}>
              <option value="created_at">Created Time</option>
              <option value="name">Name</option>
              <option value="status">Status</option>
            </select>
          </label>

          <label className="toolbar-field">
            <span>Order</span>
            <select
              value={sortOrder}
              onChange={(event) => setSortOrder(event.target.value)}
            >
              <option value="desc">Descending</option>
              <option value="asc">Ascending</option>
            </select>
          </label>
        </section>

        <section className="project-grid">
          {isLoading ? (
            <article className="empty-card">
              <h3>Loading projects</h3>
              <p>Fetching project data from the backend.</p>
            </article>
          ) : projects.length === 0 ? (
            <article className="empty-card">
              <h3>No projects yet</h3>
              <p>
                Click <strong>Create Project</strong> to add your first CSV
                profiling job card.
              </p>
            </article>
          ) : (
            projects.map((project) => (
              <article className="project-card" key={project.id}>
                <Link className="project-card-link" href={`/workspace/${project.id}`}>
                  <div className="project-card-top">
                    <p className="project-file">{project.fileName}</p>
                    <span className="project-badge">{project.status}</span>
                  </div>
                  <h3>{project.name}</h3>
                  <p className="project-description">
                    {project.description || "No description provided."}
                  </p>
                  <div className="project-meta">
                    <span>Created {project.createdAt}</span>
                  </div>
                </Link>
                <button
                  className="delete-button"
                  type="button"
                  onClick={() => handleDelete(project.id)}
                >
                  Delete
                </button>
              </article>
            ))
          )}
        </section>
      </section>
    </main>
  );
}
