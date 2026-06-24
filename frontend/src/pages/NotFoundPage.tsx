import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <section className="page-intro" aria-labelledby="not-found-heading">
      <p className="eyebrow">404</p>
      <h1 id="not-found-heading">Page not found</h1>
      <p>
        The address may be incorrect, or the page may have moved. Return home
        to continue.
      </p>
      <Link className="button" to="/">
        Return home
      </Link>
    </section>
  );
}
