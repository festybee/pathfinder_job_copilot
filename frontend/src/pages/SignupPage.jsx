import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../AuthContext.jsx";

export default function SignupPage() {
  const { signup } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [pendingMessage, setPendingMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const data = await signup(username, email, password);
      if (data.token) {
        navigate("/jobs");
      } else {
        // Account created but inactive - stay here and show the message
        // instead of navigating somewhere that requires being logged in.
        setPendingMessage(data.detail || "Account created. An admin needs to approve it before you can log in.");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  if (pendingMessage) {
    return (
      <div className="container">
        <h1>Almost there</h1>
        <p className="message">{pendingMessage}</p>
        <p>
          Once approved, you can <Link to="/login">log in</Link>.
        </p>
      </div>
    );
  }

  return (
    <div className="container">
      <h1>Create your account</h1>
      <form onSubmit={handleSubmit} className="stacked card">
        {error && <p className="error">{error}</p>}
        <label>
          Username
          <input value={username} onChange={(e) => setUsername(e.target.value)} maxLength={150} required />
        </label>
        <label>
          Email
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            maxLength={254}
            required
          />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            maxLength={128}
            required
          />
        </label>
        <button className="primary" type="submit" disabled={submitting}>
          {submitting ? "Signing up..." : "Sign up"}
        </button>
      </form>
      <p>
        Already have an account? <Link to="/login">Log in</Link>
      </p>
    </div>
  );
}
