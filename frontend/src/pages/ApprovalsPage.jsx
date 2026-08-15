import { useEffect, useState } from "react";
import { approveUser, fetchPendingUsers } from "../api.js";

export default function ApprovalsPage() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [approvingId, setApprovingId] = useState(null);

  useEffect(() => {
    fetchPendingUsers()
      .then(setUsers)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const handleApprove = async (id) => {
    setApprovingId(id);
    setError("");
    try {
      await approveUser(id);
      setUsers((prev) => prev.filter((u) => u.id !== id));
    } catch (err) {
      setError(err.message);
    } finally {
      setApprovingId(null);
    }
  };

  return (
    <div className="container">
      <h1>Pending approvals</h1>
      <p>New accounts land here and can't log in until you approve them.</p>
      {error && <p className="error">{error}</p>}

      {loading ? (
        <p>Loading...</p>
      ) : users.length === 0 ? (
        <p>No pending signups right now.</p>
      ) : (
        users.map((u) => (
          <div className="card" key={u.id}>
            <h3>{u.username}</h3>
            <p>
              {u.email || "(no email)"} &middot; signed up{" "}
              {new Date(u.date_joined).toLocaleString()}
            </p>
            <button
              className="primary"
              disabled={approvingId === u.id}
              onClick={() => handleApprove(u.id)}
            >
              {approvingId === u.id ? "Approving..." : "Approve"}
            </button>
          </div>
        ))
      )}
    </div>
  );
}
