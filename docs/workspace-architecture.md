# Network Threat Detection: implementation architecture

## Request path

The responsive browser UI calls one read endpoint (`GET /api/state`) and one action endpoint (`POST /api/action`). The loopback server checks the request host, validates a per-process token, rejects foreign origins for API calls, limits JSON bodies to 4 MiB and serves only three explicit static paths. A process-local operation lock returns HTTP 409 if another mutation is running.

`webapp/app.py` owns domain validation and workflows. `webapp/runtime.py` owns the HTTP boundary and local document-store helper. SQLite connections use parameterized values and foreign-key enforcement. The community app also has dedicated relational tables and an immediate assignment transaction. Browser templates escape user text; no user text is evaluated as script or injected as active report HTML.

## Persistence

SQLite state is local, with no external service dependency. Model artifacts, when applicable, are created by the training workflow under internally generated UUIDs. The prediction endpoint accepts an experiment ID, not a filesystem path or uploaded model. Raw CSV uploads are held in memory for the request and are not persisted by the ML workspace.

## Scope and failure behavior

Invalid inputs return a client error without publishing or deploying anything. Unexpected server errors omit local data details from the response. A request does not invoke a shell, scan an external system or configure a network device. The application does not provide user authentication, transport encryption, encryption at rest, immutable auditing or multi-user hosting. Keep it bound to loopback as implemented.

## Prior reference material

The prior case study and diagrams are preserved in `docs/reference-case-study.md` and `assets/reference-architecture.svg`. They are historical reference material; the main README and workspace guide define the current executable app. Original collaborative source artifacts remain private.
