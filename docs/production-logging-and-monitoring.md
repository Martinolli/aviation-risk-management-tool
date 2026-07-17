# Production Logging and Error Monitoring Preparation

## Purpose

Production Logging and Error Monitoring preparation supports operational troubleshooting, Operational Diagnostics, Safe Logging, production readiness, and SMS governance support for the Aviation Risk Management Tool. This MVP prepares safe logs, Request ID correlation, request completion logs, startup diagnostics, and future monitoring integration without connecting an external provider.

## Scope

This guide covers:

- Application logs
- Request IDs
- Request completion logs
- Error logs
- Health/readiness diagnostics
- Future monitoring provider integration

## What Is Logged

- HTTP method
- Request path without query string values
- Response status code
- Request duration
- Request ID
- Safe startup summary
- Unhandled exception stack trace in backend logs only

## What Must Not Be Logged

- JWT tokens
- Passwords
- Database URLs
- Request bodies
- Uploaded evidence contents
- Personal/sensitive operational details unless approved
- Secrets

## Request ID Correlation

Incoming `X-Request-ID` is preserved. If a request does not include a Request ID, the backend generates one. The response includes `X-Request-ID`, and backend logs include `request_id` so operators can correlate a user-reported failure with backend log entries.

## Log Configuration

| Setting | Default | Notes |
| --- | --- | --- |
| `LOG_LEVEL` | `INFO` | Allowed values: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. |
| `LOG_FORMAT` | `plain` | Allowed values: `plain`, `json`. |
| `ENABLE_REQUEST_LOGGING` | `true` | Enables request completion logs. |
| `LOG_REQUEST_HEADERS` | `false` | If enabled, logs only safe headers such as user-agent, content-type, accept, and origin. |
| `LOG_RESPONSE_STATUS` | `true` | Adds response status code to request completion logs. |
| `LOG_REQUEST_DURATION` | `true` | Adds request duration in milliseconds. |
| `REQUEST_ID_HEADER` | `X-Request-ID` | Header accepted and returned for request correlation. |
| `ALLOW_DEBUG_LOGGING_IN_PRODUCTION` | `false` | Production rejects `DEBUG` unless this is explicitly enabled. |

## Production Recommendations

- Use `INFO` or `WARNING` level in production.
- Use JSON logs if collected by a centralized platform.
- Plain logs are acceptable for local development and simple operations.
- Collect stdout/stderr from the backend service.
- Protect log access.
- Rotate logs if file logging is added later.
- Avoid `DEBUG` in production except temporary approved troubleshooting.

## Error Monitoring Future Integration

Future candidates include:

- Sentry
- Azure Application Insights
- AWS CloudWatch
- OpenTelemetry
- ELK / OpenSearch
- Datadog

No provider is implemented in this MVP.

## Incident Troubleshooting Procedure

1. Capture timestamp.
2. Capture the user-reported action.
3. Capture Request ID if visible.
4. Check backend logs for `request_id`.
5. Check `/health` and `/health/readiness`.
6. Check Audit Trail for governed actions.
7. Verify database and storage availability.
8. Document the operational finding.

## Relationship to Audit Trail

Logs support operations and troubleshooting. Audit Trail supports governed action traceability. Logs do not replace audit records, and audit records do not replace technical logs.

## Known MVP Limitations

- No external monitoring provider
- No metrics dashboard
- No alerting
- No log retention automation
- No distributed tracing
- No file log rotation

## Future Improvements

- OpenTelemetry trace IDs
- Structured metrics
- Alerting
- External error monitoring
- Uptime checks
- Log retention policy
- Admin diagnostics dashboard

## SMS Governance Note

"The logging and monitoring preparation supports operational reliability and SMS governance by improving traceability of technical failures and user-reported issues. It does not replace formal audit trail, committee decisions, safety reporting, or investigation records."
