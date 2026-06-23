import { Link } from "react-router-dom";

export function HomePage() {
  return (
    <section className="page-intro">
      <p className="eyebrow">Safety management system</p>
      <h1>Aviation Risk Management Tool</h1>
      <p>
        Backend MVP is available and frontend integration will be built
        incrementally.
      </p>
      <Link className="button" to="/login">
        Go to login
      </Link>
    </section>
  );
}
