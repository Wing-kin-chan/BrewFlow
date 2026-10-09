# Graph Report - BrewFlow  (2026-10-09)

## Corpus Check
- 87 files · ~25,888 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 497 nodes · 773 edges · 58 communities (46 shown, 12 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 51 edges (avg confidence: 0.51)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `99aebae1`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Order
- QueueRuntime
- QueuePage.vue
- OrderStore
- devDependencies
- application.py
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
- BrewFlow
- test_orders.py
- test_api.py

## God Nodes (most connected - your core abstractions)
1. `Order` - 36 edges
2. `QueueRuntime` - 34 edges
3. `Queue` - 29 edges
4. `make_order()` - 25 edges
5. `OrderStore` - 20 edges
6. `Requirements` - 17 edges
7. `QueueEvents` - 16 edges
8. `Drink` - 15 edges
9. `QueueSettings` - 13 edges
10. `compilerOptions` - 12 edges

## Surprising Connections (you probably didn't know these)
- `sendOrder()` --uses--> `Order`  [INFERRED]
  Orders/main.py → brewflow/domain/models.py
- `test_drink_generation_does_not_mutate_shared_menu()` --uses--> `Drink`  [INFERRED]
  Orders/tests/test_orders.py → brewflow/domain/models.py
- `test_order_generation_is_offline_when_name_source_is_stubbed()` --uses--> `Order`  [INFERRED]
  Orders/tests/test_orders.py → brewflow/domain/models.py
- `test_schema_metadata_is_unchanged()` --uses--> `Base`  [INFERRED]
  tests/test_persistence.py → brewflow/persistence/db.py
- `generateOrder()` --calls--> `Order`  [EXTRACTED]
  Orders/app/generate_order.py → brewflow/domain/models.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Order Queue Management Logic** — graphify-out::manager_readme_queuemanager, graphify-out::manager_readme_min_order_number_opt, graphify-out::manager_readme_milk_steaming_grouping, graphify-out::manager_readme_grouphead_share, graphify-out::manager_readme_max_backward_moves [EXTRACTED 0.95]

## Communities (58 total, 12 thin omitted)

### Community 0 - "Order"
Cohesion: 0.09
Nodes (24): Drink, Order, Any, BaseModel, datetime, Batch, BatchQueueItem, HistorySnapshot (+16 more)

### Community 1 - "QueueRuntime"
Cohesion: 0.13
Nodes (25): add_order(), complete_drinks(), CompletionRequest, IntakeResponse, BaseModel, get, post, QueueSnapshot (+17 more)

### Community 2 - "QueuePage.vue"
Cohesion: 0.07
Nodes (31): completeDrinks(), fetchHistory(), fetchQueue(), responseJson(), connectQueueEvents(), QueueEventConnection, QueueEventKind, BatchQueueItem (+23 more)

### Community 3 - "OrderStore"
Cohesion: 0.11
Nodes (20): Base, Database, Drinks, Orders, AsyncSession, decode_options(), drink_from_record(), order_from_record() (+12 more)

### Community 4 - "devDependencies"
Cohesion: 0.06
Nodes (31): dependencies, vue, vue-router, devDependencies, jsdom, @types/node, typescript, vite (+23 more)

### Community 5 - "application.py"
Cohesion: 0.10
Nodes (23): APIRouter, WebSocket, runtime_from_request(), runtime_from_websocket(), websocket, queue_events(), history_orders(), get (+15 more)

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

### Community 56 - "test_orders.py"
Cohesion: 0.23
Nodes (12): generateDrink(), Random drink generator. Generates an espresso based drink of certain type, with…, generateOrder(), getCustomerName(), Gets a random name from a random user generator API., getOrder(), home(), get (+4 more)

### Community 57 - "test_api.py"
Cohesion: 0.27
Nodes (12): test_random_order_endpoint_returns_an_order(), TestClient, make_client(), parametrize, Path, raw_order(), test_all_product_textures_are_accepted_batched_and_temperature_sorted(), test_intake_completion_history_and_validation() (+4 more)

## Knowledge Gaps
- **159 isolated node(s):** `$schema`, `.opencode/plugins/graphify.js`, `npm`, `name`, `baseURL` (+154 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **12 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Order` connect `Order` to `test_orders.py`, `QueueRuntime`, `OrderStore`, `application.py`?**
  _High betweenness centrality (0.046) - this node is a cross-community bridge._
- **Why does `QueueRuntime` connect `QueueRuntime` to `Order`, `QueueEvents`, `OrderStore`, `application.py`?**
  _High betweenness centrality (0.045) - this node is a cross-community bridge._
- **Why does `QueueEvents` connect `QueueEvents` to `QueueRuntime`?**
  _High betweenness centrality (0.031) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `Order` (e.g. with `add_order()` and `HistorySnapshot`) actually correct?**
  _`Order` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 19 inferred relationships involving `QueueRuntime` (e.g. with `runtime_from_request()` and `runtime_from_websocket()`) actually correct?**
  _`QueueRuntime` has 19 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `Queue` (e.g. with `Drink` and `Order`) actually correct?**
  _`Queue` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `OrderStore` (e.g. with `Order` and `Database`) actually correct?**
  _`OrderStore` has 7 INFERRED edges - model-reasoned connections that need verification._