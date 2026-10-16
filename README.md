# BrewFlow

BrewFlow runs as one FastAPI process and serves a Vue frontend. The local MVP provides Queue,
Order History, and a static-catalog POS with Stripe-hosted card Checkout.

## Development

```text
uv sync
npm --prefix frontend ci
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000
npm --prefix frontend run dev
```

The Vite development server proxies queue data and WebSocket routes to FastAPI at
`127.0.0.1:8000`. Open the Vite URL and navigate to `/api/queue`.

## Production-style local run

```text
npm --prefix frontend run build
uv run uvicorn main:app --host 127.0.0.1 --port 8000
```

FastAPI serves the compiled frontend at `/api/queue`, `/api/history`, `/api/pos`,
`/api/receipt`, and `/api/configuration`; `/` redirects to the queue. The default SQLite database remains under
`brewflow/data/` and is ignored by Git.

## Local Stripe test mode

Set test-mode values in your shell; never commit them:

```text
export STRIPE_SECRET_KEY=sk_test_REPLACE_ME
export STRIPE_WEBHOOK_SECRET=whsec_REPLACE_ME
export BREWFLOW_CHECKOUT_RETURN_BASE_URL=http://127.0.0.1:8000
stripe listen --forward-to http://127.0.0.1:8000/api/payments/stripe/webhook
```

The Stripe CLI prints a forwarding-specific webhook secret. Use that value for
`STRIPE_WEBHOOK_SECRET`. Checkout creation returns a hosted link that the POS displays as a QR
code and copyable URL. No live Stripe calls are made by the automated tests.

The default return URL is suitable when Checkout and the receipt are opened on the server device.
For QR scanning from another device, set the return URL to an address reachable on a trusted local
network and bind Uvicorn accordingly. This MVP has no authentication, so do not expose it to an
untrusted network or a public tunnel.

## Local demo payments

Demo mode is disabled unless the server starts with `BREWFLOW_ALLOW_DEMO_MODE=true`. Once enabled,
use Configuration to turn it on. Demo checkout never calls Stripe: its inert QR contains only the
fixed text `BREWFLOW DEMO PAYMENT`, and the POS provides a local Submit Payment action instead of a
link. Turning demo mode off does not convert existing payment attempts into Stripe attempts.

This remains a local-only MVP without authentication. Do not expose Configuration, demo payment,
or the trusted direct intake endpoint (`POST /api/queue/orders`) to an untrusted network.

The configured currency is GBP. Whole and Semi-skimmed milk have no surcharge; Oat and Soy add
60 pence. `No Milk` adds nothing. Existing drink options have no surcharge. Prices are final
customer-facing configured prices; BrewFlow does not calculate VAT or other taxes in this MVP.

## Current static queue settings

Configuration beyond the demo toggle and account settings are intentionally deferred. Queue search depth, batch
capacity, catalog prices, and milk surcharges currently come from
`brewflow/config/config.json`. Existing queue volume values remain unchanged.

## Packaging scope

The app is run from a source checkout after building `frontend/dist`. The Python wheel does not
bundle the root `main.py` entry point or compiled frontend and is not a standalone deployment
artifact.
