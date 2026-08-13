import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import * as api from "../api.js";

const ACTIONS = {
  "tailor-cv": { kind: "cv", label: "Tailor CV", needsQuestion: false, call: api.tailorCv },
  "cover-letter": {
    kind: "cover_letter",
    label: "Cover letter",
    needsQuestion: false,
    call: api.draftCoverLetter,
  },
  qa: { kind: "qa", label: "Application Q&A", needsQuestion: true, call: api.askQuestion },
};

export default function AiAssistPage() {
  const { jobId } = useParams();
  const [searchParams] = useSearchParams();
  const action = ACTIONS[searchParams.get("action")] ? searchParams.get("action") : "tailor-cv";
  const { kind, label, needsQuestion, call } = ACTIONS[action];

  const [job, setJob] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [selectedIds, setSelectedIds] = useState([]);
  const [question, setQuestion] = useState("");
  const [drafts, setDrafts] = useState([]);
  const [error, setError] = useState("");
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    api.fetchJob(jobId).then(setJob);
    api.fetchDocuments().then((data) => setDocuments(data.results ?? data));
    api.fetchDrafts(jobId, kind).then(setDrafts);
    setError("");
  }, [jobId, kind]);

  const toggleDocument = (id) => {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  const handleGenerate = async (e) => {
    e.preventDefault();
    setError("");
    setGenerating(true);
    try {
      const draft = needsQuestion
        ? await call(jobId, selectedIds, question)
        : await call(jobId, selectedIds);
      setDrafts((prev) => [draft, ...prev]);
      if (needsQuestion) setQuestion("");
    } catch (err) {
      setError(err.message);
    } finally {
      setGenerating(false);
    }
  };

  if (!job) return <p className="container">Loading...</p>;

  return (
    <div className="container">
      <h1>
        {label}: {job.title} @ {job.company}
      </h1>
      <p>
        <Link to="/jobs">&larr; back to jobs</Link>
      </p>
      <p>
        {Object.entries(ACTIONS).map(([key, a], i) => (
          <span key={key}>
            {i > 0 && " · "}
            <Link to={`/jobs/${jobId}/ai?action=${key}`}>{a.label}</Link>
          </span>
        ))}
      </p>

      <form onSubmit={handleGenerate} className="stacked card">
        {error && <p className="error">{error}</p>}
        <p>Tick which portfolio documents to ground this draft in:</p>
        {documents.map((doc) => (
          <label key={doc.id} style={{ display: "block" }}>
            <input
              type="checkbox"
              checked={selectedIds.includes(doc.id)}
              onChange={() => toggleDocument(doc.id)}
            />{" "}
            {doc.title}
          </label>
        ))}
        {documents.length === 0 && (
          <p>
            No portfolio documents yet - <Link to="/portfolio">add one first</Link>.
          </p>
        )}

        {needsQuestion && (
          <label>
            Application question
            <textarea value={question} onChange={(e) => setQuestion(e.target.value)} rows={3} required />
          </label>
        )}

        <button className="primary" type="submit" disabled={generating}>
          {generating ? "Generating..." : "Generate"}
        </button>
      </form>

      {drafts.map((draft) => (
        <div className="card" key={draft.id}>
          {draft.prompt_question && (
            <p>
              <strong>Q:</strong> {draft.prompt_question}
            </p>
          )}
          <p>
            <small>{new Date(draft.created_at).toLocaleString()}</small>
          </p>
          <pre style={{ whiteSpace: "pre-wrap", fontFamily: "inherit" }}>{draft.content}</pre>
        </div>
      ))}
      {drafts.length === 0 && <p>No drafts yet - select documents above and generate one.</p>}
    </div>
  );
}
