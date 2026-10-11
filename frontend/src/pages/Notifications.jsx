import { Link } from "react-router-dom";

export default function Notifications() {
  return (
    <main className="page">
      <h2>Notifications</h2>
      <p className="muted">Coming next.</p>
      <Link className="btn" to="/">← Back</Link>
    </main>
  );
}