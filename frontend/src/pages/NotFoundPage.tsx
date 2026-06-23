import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <section className="page-intro" aria-labelledby="not-found-heading">
      <p className="eyebrow">404</p>
      <h1 id="not-found-heading">Page not found</h1>
      <p>The page you requested does not exist.</p>
      <Link className="button" to="/">
        Return home
      </Link>
    </section>
  );
}
