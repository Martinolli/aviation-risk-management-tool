import type { FormEvent } from "react";

export function LoginPage() {
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
  }

  return (
    <section className="form-page" aria-labelledby="login-heading">
      <div className="form-card">
        <p className="eyebrow">Account access</p>
        <h1 id="login-heading">Login</h1>
        <p className="form-description">
          Authentication will be connected in Task 046.
        </p>
        <form onSubmit={handleSubmit}>
          <label htmlFor="email">Email</label>
          <input autoComplete="email" id="email" name="email" type="email" />

          <label htmlFor="password">Password</label>
          <input
            autoComplete="current-password"
            id="password"
            name="password"
            type="password"
          />

          <button type="submit">Login</button>
        </form>
      </div>
    </section>
  );
}
