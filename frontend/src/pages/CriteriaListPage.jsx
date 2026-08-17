import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import * as api from "../api.js";
import GuidePanel from "../components/GuidePanel.jsx";

const emptyForm = {
  name: "",
  keywords: "",
  location: "",
  country_code: "GB",
  job_type: "",
  salary_mode: "going_rate",
  flat_minimum_salary: "",
  include_sponsorship_keyword: false,
};

// Must match CriteriaProfileSerializer.MAX_KEYWORDS on the backend - that's
// the enforced limit, this is just a faster, friendlier check before the
// request even goes out.
const MAX_KEYWORDS = 12;

function keywordCount(value) {
  return value.split(",").filter((k) => k.trim()).length;
}

export default function CriteriaListPage() {
  const [profiles, setProfiles] = useState([]);
  const [choices, setChoices] = useState({ job_type: {}, salary_mode: {} });
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    api
      .fetchCriteriaProfiles()
      .then((data) => setProfiles(data.results ?? data))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
    api.fetchChoices().then(setChoices).catch(() => {});
  }, []);

  const handleChange = (field) => (e) => {
    const value = e.target.type === "checkbox" ? e.target.checked : e.target.value;
    setForm((f) => ({ ...f, [field]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    const count = keywordCount(form.keywords);
    if (count > MAX_KEYWORDS) {
      setError(
        `Too many keywords (${count}) - max ${MAX_KEYWORDS} per profile. Split extra role variants into ` +
          "a separate criteria profile instead."
      );
      return;
    }

    try {
      const payload = { ...form, flat_minimum_salary: form.flat_minimum_salary || null };
      await api.createCriteriaProfile(payload);
      setForm(emptyForm);
      load();
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="container">
      <GuidePanel pageKey="criteria-list" title="How to fill this in">
        <p>
          A <strong>criteria profile</strong> is a saved search. Create one per type of role you want to
          track - you can have several.
        </p>
        <ul>
          <li>
            <strong>Keywords</strong>: comma-separated terms to search for, e.g.{" "}
            <code>data analyst, business analyst</code>. Capped at{" "}
            <strong>{MAX_KEYWORDS} per profile</strong>. Got more role variants than that? Split them
            across <strong>several criteria profiles</strong> instead of piling them all into one.
          </li>
          <li>
            <strong>Location</strong>: a city, or <code>remote</code> - leave blank to search anywhere
          </li>
          <li>
            <strong>Country code</strong>: 2 letters, e.g. <code>GB</code> - restricts results to that
            country
          </li>
          <li>
            <strong>Salary mode</strong>: <em>going-rate table</em> checks each job against per-role
            thresholds you define after creating the profile (best for visa-sponsorship checks);{" "}
            <em>flat minimum</em> just checks against one number you set below
          </li>
          <li>
            The sponsorship checkbox is optional and a weak signal - only leave it on if you want "visa
            sponsorship" tried as an extra search term
          </li>
        </ul>
        <p>
          After saving, click into the profile to add going-rate rows (if needed) and run your first
          search.
        </p>
      </GuidePanel>

      <h1>Search criteria</h1>
      <p>Nothing here is fixed - add as many keyword/location/salary-mode combinations as you want.</p>

      {loading && <p>Loading...</p>}
      {profiles.map((profile) => (
        <div className="card" key={profile.id}>
          <h3>
            <Link to={`/criteria/${profile.id}`}>{profile.name}</Link>
          </h3>
          <p>
            {profile.keywords} &middot; {profile.location || "any location"} &middot;{" "}
            {profile.country_code}
          </p>
          <span className="pill">{choices.salary_mode[profile.salary_mode] || profile.salary_mode}</span>
        </div>
      ))}
      {!loading && profiles.length === 0 && <p>No criteria profiles yet - create one below.</p>}

      <form onSubmit={handleSubmit} className="stacked card">
        {error && <p className="error">{error}</p>}
        <label>
          Name
          <input value={form.name} onChange={handleChange("name")} required />
        </label>
        <label>
          Keywords (comma-separated)
          <input value={form.keywords} onChange={handleChange("keywords")} required />
        </label>
        <p style={{ margin: "0.25rem 0 0 0", fontSize: "0.8rem" }}>
          <small
            style={{
              color: keywordCount(form.keywords) > MAX_KEYWORDS ? "#b3261e" : "var(--muted)",
            }}
          >
            {keywordCount(form.keywords)} / {MAX_KEYWORDS} keywords
          </small>
        </p>
        <label>
          Location
          <input value={form.location} onChange={handleChange("location")} placeholder="City, or 'remote'" />
        </label>
        <label>
          Country code
          <input value={form.country_code} onChange={handleChange("country_code")} maxLength={2} />
        </label>
        <label>
          Job type
          <select value={form.job_type} onChange={handleChange("job_type")}>
            <option value="">Any</option>
            {Object.entries(choices.job_type)
              .filter(([value]) => value)
              .map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
          </select>
        </label>
        <label>
          Salary mode
          <select value={form.salary_mode} onChange={handleChange("salary_mode")}>
            {Object.entries(choices.salary_mode).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        {form.salary_mode === "flat_minimum" && (
          <label>
            Flat minimum salary
            <input
              type="number"
              value={form.flat_minimum_salary}
              onChange={handleChange("flat_minimum_salary")}
            />
          </label>
        )}
        <label>
          <input
            type="checkbox"
            checked={form.include_sponsorship_keyword}
            onChange={handleChange("include_sponsorship_keyword")}
          />{" "}
          Also search "visa sponsorship" as an extra term (weak signal - only kept if also relevant to
          your keywords)
        </label>
        <button className="primary" type="submit">
          Create criteria profile
        </button>
      </form>
    </div>
  );
}
