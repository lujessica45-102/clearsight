import { Link } from "react-router-dom";

export default function Record() {
  return (
    <main className="page">
      <h2>Decision record</h2>
      <p className="muted">Coming next.</p>
      <Link className="btn" to="/">← Back</Link>
    </main>
  );
}