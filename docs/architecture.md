# Stage 1 architecture

`main.py` is the canonical FastAPI entry point. It creates the application from
`brewflow/application.py`, which owns startup/shutdown, the single process-local queue runtime,
API routers, WebSocket connections, and serving the compiled Vue frontend.

The backend is split into domain models and queue behavior (`brewflow/domain`), unchanged
SQLAlchemy table metadata and direct persistence operations (`brewflow/persistence`), and focused
HTTP/WebSocket route modules (`brewflow/api`). Queue mutations are serialized by the runtime.
Successful intake and completion broadcast invalidation events; clients always refetch an
authoritative snapshot after connecting, reconnecting, or receiving an event.

The Vue application lives in `frontend/`. Queue and Order History are distinct lazy-loaded pages
at `/api/queue` and `/api/history`. JSON and WebSocket endpoints use explicit child paths, and
there is no catch-all route under `/api`.

Stage 1 runs one queue in one backend process for local MVP validation. Cafe isolation,
authentication, POS, payments, Menu, Configuration, Stock, and Performance are not implemented.
The existing `orders` and `drinks` database tables and columns are unchanged.
