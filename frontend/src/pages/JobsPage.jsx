import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import * as api from "../api.js";
import GuidePanel from "../components/GuidePanel.jsx";

const PAGE_SIZE = 20;

function JobCard({ job, statusChoices, sponsorChoices, onUpdate }) {
  const [updateError, setUpdateError] = useState("");

  const handleChange = async (field, value) => {
    setUpdateError("");
    try {
      const updated = await api.updateJob(job.id, { [field]: value });
      onUpdate(updated);
    } catch (err) {
      setUpdateError(err.message);
    }
  };

  return (
    <div className="card">
      <h3>
        {job.url ? (
          <a href={job.url} target="_blank" rel="noopener noreferrer">
            {job.title}
          </a>
        ) : (
          job.title
        )}
      </h3>
      <p>
        {job.company} &middot; {job.location} &middot; {job.source}
        {job.profile_name ? ` · ${job.profile_name}` : ""}
      </p>
      {job.compensation_raw && <p>{job.compensation_raw}</p>}
      {job.threshold_pass !== null && (
        <span className={`pill ${job.threshold_pass ? "pass" : "fail"}`}>
          {job.threshold_pass ? "clears threshold" : "below threshold"}
        </span>
      )}
      <div>
        <label>
          Status:{" "}
          <select value={job.status} onChange={(e) => handleChange("status", e.target.value)}>
            {Object.entries(statusChoices).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>{" "}
        <label>
          Sponsor:{" "}
          <select
            value={job.sponsor_status}
            onChange={(e) => handleChange("sponsor_status", e.target.value)}
          >
            {Object.entries(sponsorChoices).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
      </div>
      {updateError && <p className="error">{updateError}</p>}
      <p>
        <Link to={`/jobs/${job.id}/ai?action=tailor-cv`}>Tailor CV</Link> &middot;{" "}
        <Link to={`/jobs/${job.id}/ai?action=cover-letter`}>Cover letter</Link> &middot;{" "}
        <Link to={`/jobs/${job.id}/ai?action=qa`}>Q&amp;A</Link>
      </p>
    </div>
  );
}

export default function JobsPage() {
  const [searchParams] = useSearchParams();
  const [jobs, setJobs] = useState([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState(searchParams.get("status") || "");
  const [sponsorFilter, setSponsorFilter] = useState(searchParams.get("sponsor_status") || "");
  const [profileFilter, setProfileFilter] = useState(searchParams.get("profile") || "");
  const [profiles, setProfiles] = useState([]);
  const [choices, setChoices] = useState({ job_status: {}, sponsor_status: {} });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.fetchChoices().then(setChoices).catch(() => {});
    api.fetchCriteriaProfiles().then((data) => setProfiles(data.results ?? data)).catch(() => {});
  }, []);

  const loadJobs = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await api.fetchJobs({
        status: statusFilter,
        sponsor_status: sponsorFilter,
        profile: profileFilter,
        page,
      });
      setJobs(data.results ?? data);
      setCount(data.count ?? (data.results ?? data).length);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, sponsorFilter, profileFilter, page]);

  useEffect(() => {
    loadJobs();
  }, [loadJobs]);

  const handleUpdate = (updatedJob) => {
    setJobs((prev) => prev.map((j) => (j.id === updatedJob.id ? updatedJob : j)));
  };

  const totalPages = Math.max(1, Math.ceil(count / PAGE_SIZE));

  return (
    <div className="container">
      <GuidePanel pageKey="jobs" title="Getting started">
        <p>
          This is your <strong>job tracker</strong> - every job you find lands here, whether it came from
          an automated search or you added it manually.
        </p>
        <p>
          Jobs don't appear by themselves. First,{" "}
          <Link to="/criteria">create a criteria profile</Link> (keywords, location, and a salary rule),
          then open it and click <strong>Run search now</strong>. New matches show up back here.
        </p>
        <p>Once jobs are listed, you can:</p>
        <ul>
          <li>Update <strong>Status</strong> and <strong>Sponsor</strong> as you apply and hear back</li>
          <li>Filter the list by status, sponsor status, or which profile found it</li>
          <li>Use <strong>Tailor CV</strong>, <strong>Cover letter</strong>, or <strong>Q&amp;A</strong> on any job for AI help</li>
        </ul>
        <p>
          The <strong>clears threshold</strong> / <strong>below threshold</strong> pill shows whether that
          job's pay meets the salary rule on the profile that found it.
        </p>
      </GuidePanel>

      <h1>Job tracker</h1>
      <p>
        <Link to="/criteria">Manage search criteria</Link>
      </p>

      <div className="stacked" style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
        <label>
          Filter by status:
          <select
            value={statusFilter}
            onChange={(e) => {
              setPage(1);
              setStatusFilter(e.target.value);
            }}
          >
            <option value="">All</option>
            {Object.entries(choices.job_status).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Filter by sponsor status:
          <select
            value={sponsorFilter}
            onChange={(e) => {
              setPage(1);
              setSponsorFilter(e.target.value);
            }}
          >
            <option value="">All</option>
            {Object.entries(choices.sponsor_status).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Filter by search criteria:
          <select
            value={profileFilter}
            onChange={(e) => {
              setPage(1);
              setProfileFilter(e.target.value);
            }}
          >
            <option value="">All</option>
            {profiles.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
            <option value="none">Manually added (no profile)</option>
          </select>
        </label>
      </div>

      {error && <p className="error">{error}</p>}
      {loading && <p>Loading...</p>}

      {!loading && jobs.length === 0 && (
        <p>
          No jobs yet. <Link to="/criteria">Create a criteria profile</Link> and run a search.
        </p>
      )}

      {jobs.map((job) => (
        <JobCard
          key={job.id}
          job={job}
          statusChoices={choices.job_status}
          sponsorChoices={choices.sponsor_status}
          onUpdate={handleUpdate}
        />
      ))}

      {totalPages > 1 && (
        <p>
          Page {page} of {totalPages} ({count} jobs total){" "}
          {page > 1 && (
            <button className="link-button" onClick={() => setPage((p) => p - 1)}>
              &larr; Previous
            </button>
          )}{" "}
          {page < totalPages && (
            <button className="link-button" onClick={() => setPage((p) => p + 1)}>
              Next &rarr;
            </button>
          )}
        </p>
      )}
    </div>
  );
}
