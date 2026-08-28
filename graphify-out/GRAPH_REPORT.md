# Graph Report - BrewFlow  (2026-08-20)

## Corpus Check
- 29 files · ~6,965 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 214 nodes · 295 edges · 23 communities (21 shown, 2 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 37 edges (avg confidence: 0.68)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Database Models & CRUD Tests
- Order & Drink Models
- Queue Test Fixtures
- Order Generator API
- Queue Core Logic
- WebSocket Services & Utils
- FastAPI Routes
- Web UI Templates
- Frontend Scripts
- Orders Documentation
- Database Session
- Manager Documentation
- Order Completion Logic
- Data Storage

## God Nodes (most connected - your core abstractions)
1. `Connection` - 20 edges
2. `Queue` - 18 edges
3. `Order` - 15 edges
4. `Drink` - 11 edges
5. `Orders` - 9 edges
6. `Drinks` - 8 edges
7. `Drink Orders Template` - 8 edges
8. `Batch` - 7 edges
9. `generateOrder()` - 7 edges
10. `TestDeleteOperations` - 6 edges

## Surprising Connections (you probably didn't know these)
- `Order` --calls--> `receiveData()`  [INFERRED]
  app/models/__init__.py → main.py
- `Queue` --calls--> `queue()`  [INFERRED]
  app/scripts/queueManager/__init__.py → tests/test_queueManager.py
- `queue()` --indirect_call--> `index()`  [INFERRED]
  tests/test_queueManager.py → main.py
- `generateDrink()` --calls--> `test_generateDrink()`  [INFERRED]
  app/generate_drink.py → tests/tests.py
- `generateDrink()` --calls--> `test_random_drink_generation()`  [INFERRED]
  app/generate_drink.py → tests/tests.py

## Import Cycles
- None detected.

## Communities (23 total, 2 thin omitted)

### Community 0 - "Database Models & CRUD Tests"
Cohesion: 0.10
Nodes (20): Base, Drinks, Orders, Connection, Clears all records from previous day from local storage, Adds an order and its drinks to the database, This function returns a list of order objects and their respective drinks. Will…, PydanticORM (+12 more)

### Community 1 - "Order & Drink Models"
Cohesion: 0.09
Nodes (9): Drink, Order, BaseModel, fetchOrder(), Returns an order that is randomly generated from the /order HTTP endpoint., Batch, BaseModel, Class to hold drinks that can be made at the same time. Attributes: - drinks:… (+1 more)

### Community 2 - "Queue Test Fixtures"
Cohesion: 0.14
Nodes (15): adam_order(), date_time(), hannah_order(), jeff_order(), kayleigh_order(), oat_cappuccinos(), orders(), asyncio (+7 more)

### Community 3 - "Order Generator API"
Cohesion: 0.13
Nodes (16): generateDrink(), Random drink generator. Generates an espresso based drink of certain type, with…, generateOrder(), getCustomerName(), Gets a random name from a random user generator API., get, getOrder(), home() (+8 more)

### Community 4 - "Queue Core Logic"
Cohesion: 0.15
Nodes (8): Queue, Updates the hashmap of orderID's and their position (index) in the orderHistory…, When an item is removed at queue position/index N, all values of N are purged…, Drops orders with no drinks in order.drinks from self.orders, Batches are always created immediately infront of an existing order. Therefore…, Logic to complete one or more drinks and remove it from the preparation list.…, Logic to complete an entire Batch or Order and remove it from the preparation…, Queue class to store orders and batches. Attributes: - orders: List[Order] -…

### Community 5 - "WebSocket Services & Utils"
Cohesion: 0.14
Nodes (7): ConnectionManager, FormData, JSONList, BaseModel, WebSocket, Utils, RootModel

### Community 6 - "FastAPI Routes"
Cohesion: 0.24
Nodes (11): FastAPI, get, complete(), history(), index(), lifespan(), newOrder(), websocket (+3 more)

### Community 7 - "Web UI Templates"
Cohesion: 0.26
Nodes (12): style.css, index.js, Order History Template, Batch, Order History Context, selectDrink, Drink Orders Template, Batch (+4 more)

### Community 8 - "Frontend Scripts"
Cohesion: 0.28
Nodes (7): deselectAll(), form, selectDrink(), selectedDrinkIDs, selectOrder(), socket, submitButton

### Community 9 - "Orders Documentation"
Cohesion: 0.29
Nodes (7): Orders README, Covfefes/Orders Web API, FastAPI, /orders Endpoint, Pydantic, PyTest, Random Espresso Order Generation

### Community 11 - "Manager Documentation"
Cohesion: 0.29
Nodes (7): Manager README, Covfefes/Waiter Order Queue Manager, Grouphead Single-Shot Sharing, Max Backward Moves Limit, Milk Steaming Grouping, MIN_ORDER_NUMBER_OPT Buffer Guard, queueManager

### Community 12 - "Order Completion Logic"
Cohesion: 0.40
Nodes (3): Updates the timeComplete field for an order record with the respective orderID, Updates the timeComplete field for the drink record with the respective…, time

## Knowledge Gaps
- **11 isolated node(s):** `form`, `selectedDrinkIDs`, `socket`, `submitButton`, `Manager README` (+6 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Connection` connect `Database Models & CRUD Tests` to `Database Session`, `Order Completion Logic`, `Queue Core Logic`?**
  _High betweenness centrality (0.188) - this node is a cross-community bridge._
- **Why does `Queue` connect `Queue Core Logic` to `Database Models & CRUD Tests`, `Order & Drink Models`, `Database Session`, `Queue Test Fixtures`?**
  _High betweenness centrality (0.175) - this node is a cross-community bridge._
- **Why does `Order` connect `Order & Drink Models` to `Database Models & CRUD Tests`, `Queue Core Logic`, `FastAPI Routes`?**
  _High betweenness centrality (0.123) - this node is a cross-community bridge._
- **Are the 10 inferred relationships involving `Connection` (e.g. with `Database` and `Drinks`) actually correct?**
  _`Connection` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `Queue` (e.g. with `Connection` and `queue()`) actually correct?**
  _`Queue` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `Orders` (e.g. with `Connection` and `PydanticORM`) actually correct?**
  _`Orders` has 6 INFERRED edges - model-reasoned connections that need verification._
- **What connects `form`, `selectedDrinkIDs`, `socket` to the rest of the system?**
  _11 weakly-connected nodes found - possible documentation gaps or missing edges._