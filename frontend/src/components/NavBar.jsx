import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../AuthContext.jsx";

export default function NavBar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <header className="topbar">
      <Link className="brand" to="/">
        Pathfinder Job Copilot
      </Link>
      <nav>
        {user ? (
          <>
            <Link to="/jobs">Jobs</Link>
            <Link to="/criteria">Criteria</Link>
            <Link to="/portfolio">Portfolio</Link>
            <button className="link-button" onClick={handleLogout}>
              Log out ({user.username})
            </button>
          </>
        ) : (
          <>
            <Link to="/login">Log in</Link>
            <Link to="/signup">Sign up</Link>
          </>
        )}
      </nav>
    </header>
  );
}
