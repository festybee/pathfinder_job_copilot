import { useEffect, useState } from "react";
import {
  approveUser,
  deleteUser,
  fetchApprovedUsers,
  fetchPendingUsers,
  suspendUser,
} from "../api.js";
import { useAuth } from "../AuthContext.jsx";

export default function ApprovalsPage() {
  const { user: currentUser } = useAuth();
  const [pending, setPending] = useState([]);
  const [approved, setApproved] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState(null);

  const loadAll = () => {
    setLoading(true);
    setError("");
    Promise.all([fetchPendingUsers(), fetchApprovedUsers()])
      .then(([pendingData, approvedData]) => {
        setPending(pendingData);
        setApproved(approvedData);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(loadAll, []);

  const handleApprove = async (id) => {
    setBusyId(id);
    setError("");
    try {
      await approveUser(id);
      loadAll();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  };

  const handleSuspend = async (id, username) => {
    if (!confirm(`Suspend "${username}"? They'll lose access until you re-approve them.`)) return;
    setBusyId(id);
    setError("");
    try {
      await suspendUser(id);
      loadAll();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  };

  const handleDelete = async (id, username) => {
    if (!confirm(`Permanently delete "${username}"? This can't be undone.`)) return;
    setBusyId(id);
    setError("");
    try {
      await deleteUser(id);
      setApproved((prev) => prev.filter((u) => u.id !== id));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="container">
      <h1>Pending approvals</h1>
      <p>New accounts land here and can't log in until you approve them.</p>
      {error && <p className="error">{error}</p>}

      {loading ? (
        <p>Loading...</p>
      ) : pending.length === 0 ? (
        <p>No pending signups right now.</p>
      ) : (
        pending.map((u) => (
          <div className="card" key={u.id}>
            <h3>{u.username}</h3>
            <p>
              {u.email || "(no email)"} &middot; signed up{" "}
              {new Date(u.date_joined).toLocaleString()}
            </p>
            <button
              className="primary"
              disabled={busyId === u.id}
              onClick={() => handleApprove(u.id)}
            >
              {busyId === u.id ? "Approving..." : "Approve"}
            </button>
          </div>
        ))
      )}

      <h1 style={{ marginTop: "2.5rem" }}>Approved users</h1>
      <p>
        Everyone with active access right now. Suspend to revoke access without deleting the account
        (they'll drop back into pending approvals above, in case you want them back later), or delete
        permanently.
      </p>

      {!loading && approved.length === 0 && <p>No approved users yet.</p>}

      {approved.map((u) => {
        const isSelf = currentUser && u.id === currentUser.id;
        return (
          <div className="card" key={u.id}>
            <h3>
              {u.username}{" "}
              {u.is_staff && <span className="pill">staff</span>}{" "}
              {isSelf && <span className="pill">you</span>}
            </h3>
            <p>
              {u.email || "(no email)"} &middot; joined {new Date(u.date_joined).toLocaleString()}
            </p>
            <button
              className="link-button"
              disabled={busyId === u.id || isSelf}
              title={isSelf ? "You can't suspend your own account" : undefined}
              onClick={() => handleSuspend(u.id, u.username)}
            >
              {busyId === u.id ? "Working..." : "Suspend"}
            </button>{" "}
            &middot;{" "}
            <button
              className="link-button"
              disabled={busyId === u.id || isSelf}
              title={isSelf ? "You can't delete your own account" : undefined}
              style={{ color: "#b3261e" }}
              onClick={() => handleDelete(u.id, u.username)}
            >
              Delete
            </button>
          </div>
        );
      })}
    </div>
  );
}
