# Stage 2 architecture

`main.py` is the canonical FastAPI entry point. It creates the application from
`brewflow/application.py`, which owns startup/shutdown, the single process-local queue runtime,
API routers, WebSocket connections, and serving the compiled Vue frontend.

The backend is split into domain models and queue behavior (`brewflow/domain`), unchanged existing
Orders/Drinks SQLAlchemy metadata plus additive POS persistence (`brewflow/persistence`), and
focused HTTP/WebSocket route modules (`brewflow/api`). Queue mutations are serialized by the runtime.
Successful intake and completion broadcast invalidation events; clients always refetch an
authoritative snapshot after connecting, reconnecting, or receiving an event.

The Vue application lives in `frontend/`. Queue and Order History are distinct lazy-loaded pages
at `/api/queue` and `/api/history`. JSON and WebSocket endpoints use explicit child paths, and
there is no catch-all route under `/api`.

Stage 2 keeps the same one-process, one-cafe local MVP boundary and adds a static-catalog POS and
Stripe-hosted card Checkout. `pos_orders` and `pos_order_items` hold a server-priced immutable
pending order snapshot; `payment_attempts` holds Checkout Session lifecycle and idempotency data.
The existing `orders` and `drinks` tables and columns remain unchanged.

Unpaid POS records never enter the preparation queue. A raw-body, signature-verified Stripe
webhook retrieves the Checkout Session, reconciles its order metadata, GBP amount, payment mode,
and paid status, then invokes the existing idempotent queue intake. The paid marker is durable
before intake and the queued marker follows it, so webhook replay, process restart, and receipt
polling can safely recover paid-but-unqueued orders. Redirects and receipt pages cannot mark an
order paid.

An opt-in local demo mode is gated by `BREWFLOW_ALLOW_DEMO_MODE` and persisted on the singleton
local cafe record. Demo and Stripe provenance is immutable per payment attempt. Demo submission
marks the persisted attempt paid and uses the same idempotent queue fulfillment path without
calling Stripe. Paid demo orders are recoverable only while the server gate and saved setting are
both enabled; real Stripe recovery remains active in either mode. SQLite startup performs only the
idempotent additive migration needed for the demo provenance column.

The POS catalog uses only `brewflow/config/config.json`; Configuration currently exposes only the
demo-mode toggle, while the remaining configuration features and Menu UI remain deferred. There
is one Drinks group because no food catalog exists. Checkout links are shown as a QR code and a
copyable URL. SMS/email delivery, refunds, tax calculation, Stripe Terminal/NFC, authentication,
cafe isolation, Stock, and Performance are not implemented.
