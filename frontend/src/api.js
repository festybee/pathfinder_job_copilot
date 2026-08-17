const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";
const TOKEN_KEY = "pathfinder_token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

/**
 * Thin fetch wrapper: adds the API base URL, JSON headers, and the auth
 * token if we have one. Throws ApiError on non-2xx responses so callers
 * can catch a single error type.
 */
export class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

/**
 * Turn whatever the API sent back on an error response into a short,
 * readable sentence - never raw JSON or a stack-trace-y string.
 * Handles: {"detail": "..."} (our hand-written views), DRF validation
 * errors like {"email": ["already exists"], "password": ["too short"]},
 * and plain-text/empty bodies (e.g. a 500 with no JSON body at all).
 */
function friendlyErrorMessage(data, status) {
  if (data && typeof data === "object" && !Array.isArray(data)) {
    if (typeof data.detail === "string") return data.detail;

    const parts = [];
    for (const [field, value] of Object.entries(data)) {
      const messages = Array.isArray(value) ? value : [value];
      for (const msg of messages) {
        if (typeof msg !== "string") continue;
        parts.push(field === "non_field_errors" ? msg : `${field}: ${msg}`);
      }
    }
    if (parts.length) return parts.join(" ");
  }

  if (typeof data === "string" && data.trim() && !data.trim().startsWith("<")) {
    // Plain-text body, but not an HTML error page (Django's DEBUG=False
    // 500 pages aren't something a user should ever see rendered as text).
    return data.trim();
  }

  return `Something went wrong (error ${status}). Please try again.`;
}

export async function apiFetch(path, { method = "GET", body, isFormData = false } = {}) {
  const headers = {};
  const token = getToken();
  if (token) {
    headers["Authorization"] = `Token ${token}`;
  }
  if (!isFormData && body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : isFormData ? body : JSON.stringify(body),
  });

  if (response.status === 204) {
    return null;
  }

  let data = null;
  const text = await response.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!response.ok) {
    throw new ApiError(friendlyErrorMessage(data, response.status), response.status, data);
  }

  return data;
}

// --- Auth ---
export const login = (username, password) =>
  apiFetch("/auth/login/", { method: "POST", body: { username, password } });

export const signup = (username, email, password) =>
  apiFetch("/auth/signup/", { method: "POST", body: { username, email, password } });

export const logout = () => apiFetch("/auth/logout/", { method: "POST" });

export const fetchMe = () => apiFetch("/auth/me/");

// --- Admin approval (staff only - server enforces this via IsAdminUser) ---
export const fetchPendingUsers = () => apiFetch("/auth/pending-users/");
export const approveUser = (id) => apiFetch(`/auth/pending-users/${id}/approve/`, { method: "POST" });
export const fetchApprovedUsers = () => apiFetch("/auth/approved-users/");
export const suspendUser = (id) => apiFetch(`/auth/approved-users/${id}/suspend/`, { method: "POST" });
export const deleteUser = (id) => apiFetch(`/auth/approved-users/${id}/`, { method: "DELETE" });

// --- Reference data ---
export const fetchChoices = () => apiFetch("/jobsearch/choices/");

// --- Portfolio ---
export const fetchDocuments = () => apiFetch("/portfolio/documents/");
export const createDocument = (data) => apiFetch("/portfolio/documents/", { method: "POST", body: data });
export const deleteDocument = (id) => apiFetch(`/portfolio/documents/${id}/`, { method: "DELETE" });

// --- Criteria profiles ---
export const fetchCriteriaProfiles = () => apiFetch("/jobsearch/criteria/");
export const fetchCriteriaProfile = (id) => apiFetch(`/jobsearch/criteria/${id}/`);
export const createCriteriaProfile = (data) =>
  apiFetch("/jobsearch/criteria/", { method: "POST", body: data });
export const updateCriteriaProfile = (id, data) =>
  apiFetch(`/jobsearch/criteria/${id}/`, { method: "PATCH", body: data });
export const deleteCriteriaProfile = (id) =>
  apiFetch(`/jobsearch/criteria/${id}/`, { method: "DELETE" });
export const runSearch = (id) => apiFetch(`/jobsearch/criteria/${id}/search/`, { method: "POST" });

// --- Threshold rows ---
export const fetchThresholdRows = (profileId) =>
  apiFetch(`/jobsearch/threshold-rows/?profile=${profileId}`);
export const createThresholdRow = (data) =>
  apiFetch("/jobsearch/threshold-rows/", { method: "POST", body: data });
export const deleteThresholdRow = (id) =>
  apiFetch(`/jobsearch/threshold-rows/${id}/`, { method: "DELETE" });

// --- Jobs ---
export const fetchJob = (id) => apiFetch(`/jobsearch/jobs/${id}/`);
export const fetchJobs = (params = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(Object.entries(params).filter(([, v]) => v))
  ).toString();
  return apiFetch(`/jobsearch/jobs/${qs ? `?${qs}` : ""}`);
};
export const updateJob = (id, data) => apiFetch(`/jobsearch/jobs/${id}/`, { method: "PATCH", body: data });

// --- AI assist ---
export const tailorCv = (jobId, documentIds) =>
  apiFetch(`/aiassist/jobs/${jobId}/tailor-cv/`, { method: "POST", body: { document_ids: documentIds } });
export const draftCoverLetter = (jobId, documentIds) =>
  apiFetch(`/aiassist/jobs/${jobId}/cover-letter/`, {
    method: "POST",
    body: { document_ids: documentIds },
  });
export const askQuestion = (jobId, documentIds, question) =>
  apiFetch(`/aiassist/jobs/${jobId}/qa/`, {
    method: "POST",
    body: { document_ids: documentIds, question },
  });
export const fetchDrafts = (jobId, kind) =>
  apiFetch(`/aiassist/jobs/${jobId}/drafts/${kind ? `?kind=${kind}` : ""}`);
