import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import * as api from "../api.js";
import GuidePanel from "../components/GuidePanel.jsx";

const emptyRow = { keyword_match: "", occupation_code: "", threshold_amount: "", currency: "GBP", verified: false, source_note: "" };

export default function CriteriaDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [profile, setProfile] = useState(null);
  const [rows, setRows] = useState([]);
  const [rowForm, setRowForm] = useState(emptyRow);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [searching, setSearching] = useState(false);

  const load = () => {
    api.fetchCriteriaProfile(id).then((data) => {
      setProfile(data);
      setRows(data.threshold_rows);
    });
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const handleRunSearch = async () => {
    setSearching(true);
    setMessage("");
    setError("");
    try {
      const result = await api.runSearch(id);
      const skipped = result.skipped_below_threshold || 0;
      const duplicate = result.skipped_duplicate || 0;
      const extras = [];
      if (skipped) extras.push(`${skipped} skipped for not meeting the salary threshold`);
      if (duplicate) extras.push(`${duplicate} skipped as duplicates of jobs already in your tracker`);
      setMessage(
        `Search complete: ${result.new_jobs} new job(s) added to your tracker` +
          (extras.length ? `, ${extras.join(", ")}.` : ".")
      );
      if (result.warnings.length) {
        setError(`Some sources had trouble and were skipped this time: ${result.warnings.join(" · ")}`);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setSearching(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm(`Delete "${profile.name}"? This also deletes its going-rate table rows.`)) return;
    await api.deleteCriteriaProfile(id);
    navigate("/criteria");
  };

  const handleRowSubmit = async (e) => {
    e.preventDefault();
    await api.createThresholdRow({ ...rowForm, profile: id });
    setRowForm(emptyRow);
    load();
  };

  const handleRowDelete = async (rowId) => {
    await api.deleteThresholdRow(rowId);
    load();
  };

  const handleRowChange = (field) => (e) => {
    const value = e.target.type === "checkbox" ? e.target.checked : e.target.value;
    setRowForm((f) => ({ ...f, [field]: value }));
  };

  if (!profile) return <p className="container">Loading...</p>;

  return (
    <div className="container">
      <GuidePanel pageKey="criteria-detail" title="What happens here">
        <p>
          <strong>Run search now</strong> queries job sites for postings matching this profile's keywords
          and location, and adds any new ones to your <Link to="/jobs">job tracker</Link>.
        </p>
        <p>
          The <strong>going-rate table</strong> below only matters if this profile's salary mode is
          "going-rate table". Add one row per role type, e.g. keyword <code>data analyst</code> matched to
          the official minimum salary for that occupation (such as a UK Skilled Worker visa going rate).
        </p>
        <p>
          If this profile's salary mode is "flat minimum" instead, you can ignore the table entirely - just
          click Run search.
        </p>
        <p>
          Once a row (or the flat minimum) applies to a job, the threshold is <strong>mandatory</strong>:
          jobs that don't clear it are skipped and never added to your tracker at all - a posting with no
          listed salary counts as £0, so it won't sneak through. Roles you haven't added a row for yet are
          still shown (unevaluated), so you can spot new keyword patterns and add a row for them.
        </p>
      </GuidePanel>

      <h1>{profile.name}</h1>
      <p>
        Keywords: {profile.keywords}
        <br />
        Location: {profile.location || "any"} &middot; Country: {profile.country_code}
        <br />
        Salary mode: {profile.salary_mode}
        {profile.salary_mode === "flat_minimum" && ` (min ${profile.flat_minimum_salary})`}
      </p>

      <button className="primary" onClick={handleRunSearch} disabled={searching}>
        {searching ? "Searching..." : "Run search now"}
      </button>

      {message && <p className="message">{message}</p>}
      {error && <p className="error">{error}</p>}

      <p>
        <Link to={`/jobs?profile=${id}`}>View jobs found by this profile</Link> &middot;{" "}
        <button className="link-button" onClick={handleDelete}>
          Delete this profile
        </button>
      </p>

      <h3>Going-rate table</h3>
      {rows.map((row) => (
        <div className="card" key={row.id}>
          <strong>{row.keyword_match}</strong> - {row.threshold_amount} {row.currency}{" "}
          {row.occupation_code && <span className="pill">{row.occupation_code}</span>}{" "}
          <span className={`pill ${row.verified ? "pass" : ""}`}>
            {row.verified ? "verified" : "unverified"}
          </span>{" "}
          <button className="link-button" onClick={() => handleRowDelete(row.id)}>
            Delete
          </button>
        </div>
      ))}
      {rows.length === 0 && (
        <p>No rows yet - only matters if this profile's salary mode is "going-rate table".</p>
      )}

      <form onSubmit={handleRowSubmit} className="stacked card">
        <label>
          Keyword match
          <input
            value={rowForm.keyword_match}
            onChange={handleRowChange("keyword_match")}
            maxLength={150}
            required
          />
        </label>
        <label>
          Occupation code
          <input value={rowForm.occupation_code} onChange={handleRowChange("occupation_code")} maxLength={50} />
        </label>
        <label>
          Threshold amount
          <input
            type="number"
            value={rowForm.threshold_amount}
            onChange={handleRowChange("threshold_amount")}
            min={0}
            max={1000000}
            required
          />
        </label>
        <label>
          Currency
          <input value={rowForm.currency} onChange={handleRowChange("currency")} maxLength={3} />
        </label>
        <label>
          <input type="checkbox" checked={rowForm.verified} onChange={handleRowChange("verified")} />{" "}
          Verified against an official source
        </label>
        <button className="primary" type="submit">
          Add row
        </button>
      </form>
    </div>
  );
}
