import { useEffect, useState } from "react";
import * as api from "../api.js";
import GuidePanel from "../components/GuidePanel.jsx";

const emptyForm = { title: "", doc_type: "other", tags: "", body_text: "" };
const DOC_TYPES = [
  ["cv", "CV / Resume"],
  ["certificate", "Certificate"],
  ["project", "Project write-up"],
  ["other", "Other"],
];

export default function PortfolioPage() {
  const [documents, setDocuments] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    api
      .fetchDocuments()
      .then((data) => setDocuments(data.results ?? data))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const handleChange = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    await api.createDocument(form);
    setForm(emptyForm);
    load();
  };

  const handleDelete = async (id) => {
    await api.deleteDocument(id);
    load();
  };

  return (
    <div className="container">
      <GuidePanel pageKey="portfolio" title="What goes here">
        <p>
          Store the raw material AI tools draw from: your <strong>CV</strong>, certificates, and project
          write-ups.
        </p>
        <ul>
          <li>
            <strong>Body text</strong> is what gets read - paste your actual CV text or key bullet points,
            not just a title
          </li>
          <li>
            <strong>Tags</strong> (skills/keywords) help you find the right document later, e.g.{" "}
            <code>python, sql, agile</code>
          </li>
          <li>
            Nothing here is used automatically - when you tailor a CV or write a cover letter for a job,
            you pick which documents to include
          </li>
        </ul>
        <p>Add your main CV first, then anything else worth drawing on: certificates, past projects, etc.</p>
      </GuidePanel>

      <h1>Your portfolio</h1>
      <p>
        CVs, certificates, and project write-ups. Tick the ones relevant to a job when tailoring a CV or
        cover letter - nothing is used without being selected.
      </p>

      {loading && <p>Loading...</p>}
      {documents.map((doc) => (
        <div className="card" key={doc.id}>
          <h3>{doc.title}</h3>
          <span className="pill">{DOC_TYPES.find(([v]) => v === doc.doc_type)?.[1] || doc.doc_type}</span>
          {doc.tags && (
            <p>
              <small>{doc.tags}</small>
            </p>
          )}
          <button className="link-button" onClick={() => handleDelete(doc.id)}>
            Delete
          </button>
        </div>
      ))}
      {!loading && documents.length === 0 && (
        <p>No portfolio documents yet - add your CV below to get started.</p>
      )}

      <form onSubmit={handleSubmit} className="stacked card">
        <label>
          Title
          <input value={form.title} onChange={handleChange("title")} required />
        </label>
        <label>
          Type
          <select value={form.doc_type} onChange={handleChange("doc_type")}>
            {DOC_TYPES.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Tags (comma-separated)
          <input value={form.tags} onChange={handleChange("tags")} placeholder="python, sql, agile" />
        </label>
        <label>
          Body text
          <textarea value={form.body_text} onChange={handleChange("body_text")} rows={8} />
        </label>
        <button className="primary" type="submit">
          Add to portfolio
        </button>
      </form>
    </div>
  );
}
