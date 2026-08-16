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
      setMessage(`Search complete: ${result.new_jobs} new job(s) added to your tracker.`);
      if (result.warnings.length) {
        setError(result.warnings.join(" | "));
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
          Jobs matching that keyword get checked against the figure you enter, and marked as clearing or
          missing the threshold.
        </p>
        <p>
          If this profile's salary mode is "flat minimum" instead, you can ignore the table entirely - just
          click Run search.
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
          <input value={rowForm.keyword_match} onChange={handleRowChange("keyword_match")} required />
        </label>
        <label>
          Occupation code
          <input value={rowForm.occupation_code} onChange={handleRowChange("occupation_code")} />
        </label>
        <label>
          Threshold amount
          <input
            type="number"
            value={rowForm.threshold_amount}
            onChange={handleRowChange("threshold_amount")}
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
