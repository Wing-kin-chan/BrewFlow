# Covfefes/Orders

## About

This is a simple Web API that generates random espresso based drink orders, and serves the data
at the HTTP endpoint `/random_order`. Generated orders can be submitted to BrewFlow at
`/api/queue/orders` while the POS is not yet implemented.

The form accepts an arbitrary destination URL and is a local-only development demo. Bind it only
to loopback; it is not intended to be exposed to untrusted users or networks.

## Notable Libraries

- FastAPI for Endpoint creation
- Pydantic for data modelling and validation
- PyTest for testing
