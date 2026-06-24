import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { ApiError } from "../api/client";
import { getHealth } from "../api/health";
import type { HealthResponse } from "../api/types";
import { useAuth } from "../auth/AuthContext";

type HealthCheckState =
  | { status: "loading" }
  | { status: "success"; health: HealthResponse }
  | { status: "error"; message: string };

export function HomePage() {
  const { isAuthenticated, user } = useAuth();
  const [healthCheck, setHealthCheck] = useState<HealthCheckState>({
    status: "loading",
  });

  useEffect(() => {
    let isCurrent = true;

    async function checkBackendHealth() {
      try {
        const health = await getHealth();
        if (isCurrent) {
          setHealthCheck({ status: "success", health });
        }
      } catch (error) {
        if (!isCurrent) {
          return;
        }

        const message =
          error instanceof ApiError
            ? error.message
            : "Unable to connect to the backend.";
        setHealthCheck({ status: "error", message });
      }
    }

    void checkBackendHealth();

    return () => {
      isCurrent = false;
    };
  }, []);

  return (
    <section className="page-intro">
      <p className="eyebrow">Safety management system</p>
      <h1>Aviation Risk Management Tool</h1>
      <p>
        Backend MVP is available and frontend integration will be built
        incrementally.
      </p>
      <BackendConnectionStatus healthCheck={healthCheck} />
      {isAuthenticated && user ? (
        <section className="signed-in-card" aria-labelledby="signed-in-heading">
          <p className="eyebrow">Your session</p>
          <h2 id="signed-in-heading">
            Signed in as {user.display_name || user.email}
          </h2>
          <p>
            You can now start working with risk records when the risk workspace
            is added.
          </p>
        </section>
      ) : (
        <Link className="button" to="/login">
          Go to login
        </Link>
      )}
    </section>
  );
}

function BackendConnectionStatus({
  healthCheck,
}: {
  healthCheck: HealthCheckState;
}) {
  if (healthCheck.status === "loading") {
    return (
      <p aria-live="polite" className="connection-status connection-status--loading">
        Checking backend connection...
      </p>
    );
  }

  if (healthCheck.status === "success") {
    return (
      <div aria-live="polite" className="connection-status connection-status--success">
        <strong>Backend connected: {healthCheck.health.service}</strong>
        <span>Status: {healthCheck.health.status}</span>
      </div>
    );
  }

  return (
    <div aria-live="polite" className="connection-status connection-status--error">
      <strong>Backend unavailable</strong>
      <span>{healthCheck.message}</span>
    </div>
  );
}
