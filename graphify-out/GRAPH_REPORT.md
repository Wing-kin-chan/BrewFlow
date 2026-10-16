# Graph Report - BrewFlow  (2026-10-16)

## Corpus Check
- 99 files · ~38,011 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 760 nodes · 1616 edges · 67 communities (55 shown, 12 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 129 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `cb750b23`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- QueueRuntime
- application.py
- QueuePage.vue
- PosStore
- devDependencies
- test_payments.py
- What You Must Do When Invoked
- Requirements
- compilerOptions
- Covfefes/Orders Web API
- ollama
- queueManager
- Request router
- BrewFlow — Agent Instructions
- Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International Public License
- graphify reference: extra exports and benchmark
- QueueEvents
- graphify reference: query, path, explain
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- Covfefes/Orders
- graphify.js
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: transcribe video and audio
- api/__init__.py
- data/__init__.py
- brewflow/__init__.py
- adr/README.md
- architecture.md
- features/README.md
- extraction-spec.md
- yagni/SKILL.md
- demoMode.ts
- PosPage.vue
- BrewFlow
- PaymentRuntime
- client.ts
- dependencies.py
- OrderHistoryPage.vue
- pages.test.ts
- ReceiptPage.vue
- Queue
- test_orders.py
- domain/queue.py
- queue_runtime.py
- Order

## God Nodes (most connected - your core abstractions)
1. `PaymentRuntime` - 61 edges
2. `QueueRuntime` - 42 edges
3. `Order` - 41 edges
4. `Queue` - 29 edges
5. `make_runtime()` - 27 edges
6. `PosStore` - 26 edges
7. `make_order()` - 25 edges
8. `OrderStore` - 23 edges
9. `Drink` - 22 edges
10. `pos_order()` - 22 edges

## Surprising Connections (you probably didn't know these)
- `sendOrder()` --uses--> `Order`  [INFERRED]
  Orders/main.py → brewflow/domain/models.py
- `test_drink_generation_does_not_mutate_shared_menu()` --uses--> `Drink`  [INFERRED]
  Orders/tests/test_orders.py → brewflow/domain/models.py
- `test_order_generation_is_offline_when_name_source_is_stubbed()` --uses--> `Order`  [INFERRED]
  Orders/tests/test_orders.py → brewflow/domain/models.py
- `test_checkout_is_server_priced_persisted_first_and_idempotent()` --uses--> `Order`  [INFERRED]
  tests/test_payments.py → brewflow/domain/models.py
- `pos_order()` --uses--> `PosOrderInput`  [INFERRED]
  tests/test_payments.py → brewflow/domain/pos.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Order Queue Management Logic** — graphify-out::manager_readme_queuemanager, graphify-out::manager_readme_min_order_number_opt, graphify-out::manager_readme_milk_steaming_grouping, graphify-out::manager_readme_grouphead_share, graphify-out::manager_readme_max_backward_moves [EXTRACTED 0.95]

## Communities (67 total, 12 thin omitted)

### Community 0 - "QueueRuntime"
Cohesion: 0.17
Nodes (11): datetime, HistorySnapshot, QueueSnapshot, QueueRuntime, asyncio, test_completion_domain_failure_has_no_persistence_effect(), test_completion_persistence_failure_does_not_mutate_memory(), test_intake_domain_failure_has_no_persistence_effect() (+3 more)

### Community 1 - "application.py"
Cohesion: 0.10
Nodes (34): APIRouter, create_pages_router(), Path, create_app(), Path, CatalogItem, CatalogSettings, load_catalog_settings() (+26 more)

### Community 2 - "QueuePage.vue"
Cohesion: 0.17
Nodes (13): completeDrinks(), fetchCatalog(), fetchQueue(), responseJson(), QueueSnapshot, applySnapshot(), completeSelected(), completing (+5 more)

### Community 3 - "PosStore"
Cohesion: 0.06
Nodes (31): Base, CafeAccounts, Database, Drinks, _enable_sqlite_foreign_keys(), _migrate_sqlite_schema(), Orders, PaymentAttempts (+23 more)

### Community 4 - "devDependencies"
Cohesion: 0.06
Nodes (35): dependencies, qrcode, vue, vue-router, devDependencies, jsdom, @types/node, @types/qrcode (+27 more)

### Community 5 - "test_payments.py"
Cohesion: 0.13
Nodes (44): PosConflictError, Clock, close_runtime(), FakeSessions, FakeStripeClient, make_runtime(), paid_event(), payment_settings() (+36 more)

### Community 6 - "What You Must Do When Invoked"
Cohesion: 0.08
Nodes (24): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+16 more)

### Community 7 - "Requirements"
Cohesion: 0.09
Nodes (22): Add Order, BrewFlow, Cafe Accounts, Complete Drink, Complete Drinks, Complete Order, Configuration Page, Drink Class (+14 more)

### Community 8 - "compilerOptions"
Cohesion: 0.09
Nodes (22): compilerOptions, esModuleInterop, isolatedModules, jsx, lib, module, moduleResolution, resolveJsonModule (+14 more)

### Community 9 - "Covfefes/Orders Web API"
Cohesion: 0.29
Nodes (7): Orders README, Covfefes/Orders Web API, FastAPI, /orders Endpoint, Pydantic, PyTest, Random Espresso Order Generation

### Community 10 - "ollama"
Cohesion: 0.13
Nodes (14): name, deepseek-r1:14b, qwen3.5:9b, models, name, npm, options, baseURL (+6 more)

### Community 11 - "queueManager"
Cohesion: 0.29
Nodes (7): Manager README, Covfefes/Waiter Order Queue Manager, Grouphead Single-Shot Sharing, Max Backward Moves Limit, Milk Steaming Grouping, MIN_ORDER_NUMBER_OPT Buffer Guard, queueManager

### Community 12 - "Request router"
Cohesion: 0.17
Nodes (11): Delegation, Escalation, Local model lifecycle, Request router, Routing matrix, Task type, Tier 0 — direct, Tier 1 — local (+3 more)

### Community 13 - "BrewFlow — Agent Instructions"
Cohesion: 0.20
Nodes (9): BrewFlow — Agent Instructions, Commands, Communication, Git, graphify, Implementation philosophy, Planning, Purpose (+1 more)

### Community 14 - "Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International Public License"
Cohesion: 0.20
Nodes (9): Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International Public License, Section 1 – Definitions., Section 2 – Scope., Section 3 – License Conditions., Section 4 – Disclaimer of Warranties and Limitation of Liability., Section 5 – Disclaimer of Warranties and Limitation of Liability., Section 6 – Term and Termination., Section 7 – Other Terms and Conditions. (+1 more)

### Community 15 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 16 - "QueueEvents"
Cohesion: 0.18
Nodes (10): WebSocket, QueueEvents, HandshakePeer, Peer, asyncio, test_broadcast_sends_to_peers_concurrently_and_drops_slow_or_failed_peers(), test_concurrent_broadcasts_are_serialized_and_stale_revisions_are_skipped(), test_connect_registers_peer_and_serializes_connected_before_change() (+2 more)

### Community 17 - "graphify reference: query, path, explain"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 18 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 19 - "graphify reference: commit hook and native CLAUDE.md integration"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 20 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

### Community 21 - "Covfefes/Orders"
Cohesion: 0.50
Nodes (3): About, Covfefes/Orders, Notable Libraries

### Community 34 - "demoMode.ts"
Cohesion: 0.22
Nodes (14): fetchDemoMode(), updateDemoMode(), refresh(), route, configuration, demoModeConfiguration, refreshDemoMode(), saveDemoMode() (+6 more)

### Community 37 - "PosPage.vue"
Cohesion: 0.07
Nodes (40): createCheckout(), fetchDemoReceipt(), submitDemoPayment(), Temperature, Texture, addItem(), applyReceipt(), BasketLine (+32 more)

### Community 56 - "PaymentRuntime"
Cohesion: 0.08
Nodes (47): demo_mode(), get, update_demo_mode(), catalog(), create_pos_order(), demo_receipt(), CheckoutResponse, get (+39 more)

### Community 57 - "client.ts"
Cohesion: 0.12
Nodes (17): ApiError, BatchQueueItem, Catalog, CatalogItem, CheckoutResponse, CheckoutResponseBase, CompletedOrder, DemoModeConfiguration (+9 more)

### Community 58 - "dependencies.py"
Cohesion: 0.21
Nodes (11): payment_runtime_from_request(), Request, WebSocket, runtime_from_request(), runtime_from_websocket(), websocket, queue_events(), history_orders() (+3 more)

### Community 59 - "OrderHistoryPage.vue"
Cohesion: 0.27
Nodes (8): fetchHistory(), connectQueueEvents(), QueueEventConnection, QueueEventKind, HistorySnapshot, error, refresh(), snapshot

### Community 60 - "pages.test.ts"
Cohesion: 0.25
Nodes (3): drink, FakeWebSocket, MockResponse

### Community 61 - "ReceiptPage.vue"
Cohesion: 0.20
Nodes (7): fetchReceipt(), Receipt, error, receipt, refresh(), route, routes

### Community 62 - "Queue"
Cohesion: 0.21
Nodes (11): time, Queue, make_order(), parametrize, test_all_product_textures_can_batch(), test_batches_only_matching_milk_and_texture_and_sorts_temperature(), test_cross_order_batch_respects_capacity(), test_history_has_one_parent_and_completion_is_repeat_safe() (+3 more)

### Community 63 - "test_orders.py"
Cohesion: 0.21
Nodes (12): generateDrink(), Random drink generator. Generates an espresso based drink of certain type, with…, generateOrder(), getCustomerName(), Gets a random name from a random user generator API., getOrder(), home(), get (+4 more)

### Community 64 - "domain/queue.py"
Cohesion: 0.27
Nodes (7): Batch, BatchQueueItem, HistorySnapshot, OrderQueueItem, BaseModel, Drink, QueueSnapshot

### Community 65 - "queue_runtime.py"
Cohesion: 0.22
Nodes (14): add_order(), complete_drinks(), CompletionRequest, IntakeResponse, BaseModel, get, post, QueueSnapshot (+6 more)

### Community 69 - "Order"
Cohesion: 0.17
Nodes (5): Order, Any, BaseModel, datetime, model_validator

## Knowledge Gaps
- **189 isolated node(s):** `$schema`, `.opencode/plugins/graphify.js`, `npm`, `name`, `baseURL` (+184 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **12 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `QueueRuntime` connect `QueueRuntime` to `queue_runtime.py`, `application.py`, `PosStore`, `test_payments.py`, `Order`, `QueueEvents`, `PaymentRuntime`, `dependencies.py`?**
  _High betweenness centrality (0.053) - this node is a cross-community bridge._
- **Why does `PaymentRuntime` connect `PaymentRuntime` to `QueueRuntime`, `application.py`, `test_payments.py`, `Order`, `dependencies.py`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._
- **Why does `Order` connect `Order` to `domain/queue.py`, `queue_runtime.py`, `QueueRuntime`, `PosStore`, `test_payments.py`, `PaymentRuntime`, `Queue`, `test_orders.py`?**
  _High betweenness centrality (0.048) - this node is a cross-community bridge._
- **Are the 27 inferred relationships involving `PaymentRuntime` (e.g. with `demo_mode()` and `update_demo_mode()`) actually correct?**
  _`PaymentRuntime` has 27 INFERRED edges - model-reasoned connections that need verification._
- **Are the 22 inferred relationships involving `QueueRuntime` (e.g. with `runtime_from_request()` and `runtime_from_websocket()`) actually correct?**
  _`QueueRuntime` has 22 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `Order` (e.g. with `add_order()` and `HistorySnapshot`) actually correct?**
  _`Order` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `Queue` (e.g. with `Drink` and `Order`) actually correct?**
  _`Queue` has 3 INFERRED edges - model-reasoned connections that need verification._