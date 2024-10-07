from fastapi import FastAPI, Request, Form, WebSocket, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from Manager.app.scripts.queueManager import Queue
from Manager.app.scripts.services import ConnectionManager, FormData, Utils

from typing import Optional
from contextlib import asynccontextmanager
from Manager.app.models import Order
import os, json, uuid, logging


################################################### PATH VARIABLES AND DATA ##################################################

RELATIVE_PATH = "./config/config.json"
CONFIG_FILE_PATH = os.path.join(os.path.dirname(__file__), RELATIVE_PATH)
STATIC_DIR = os.path.join(os.path.dirname(__file__), "app/static")
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "app/templates")
DATABASE_URI = "sqlite+aiosqlite:///" + os.path.join(os.path.dirname(__file__), "app/data/", "database.db")

with open(CONFIG_FILE_PATH, 'r') as f:
    data = json.load(f)
    MILK_COLORS = data.get('MILK_COLORS')
    PORT = data.get('PORT')
    ENDPOINT = data.get('ENDPOINT')
    LOGGING_CONFIG = data.get('LOGGING')

ADDRESS = Utils.getAddress()

if not ENDPOINT:
    ENDPOINT = uuid.uuid4().hex

@asynccontextmanager
async def lifespan(app: FastAPI):
    global queue
    queue = await Queue.create(DATABASE_URI)
    await queue._load_from_db()
    yield
    if queue and queue.connection:
        await queue.connection.close()

app = FastAPI(lifespan = lifespan)
connectionManager = ConnectionManager()
app.mount("/static", StaticFiles(directory = STATIC_DIR), name = "static")
templates = Jinja2Templates(directory = TEMPLATE_DIR)


################################################## MAIN ######################################################

@app.get("/", response_class = HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        "index.html", 
        context = {
            "request": request, 
            "queue": queue,
            "colors": MILK_COLORS
            }
        )
 
@app.post("/complete")
async def complete(
    selectedDrinkIDs: Optional[str] = Form(default = '[]'),
    selectedItemIndex: Optional[str] = Form(default = None),
):
    try:
        form_data = FormData(
            selectedDrinkIDs = json.loads(selectedDrinkIDs),
            selectedItemIndex = selectedItemIndex
        )

        if form_data.selectedDrinkIDs:
            await queue.completeDrinks(form_data.selectedDrinkIDs.root)

        if form_data.selectedItemIndex is not None:
            await queue.completeItem(form_data.selectedItemIndex)

        return JSONResponse(content = {
            'updatedOrderList': [order.model_dump_json() for order in queue.orders],
            'updatedTotalOrders': queue.totalOrders,
            'updatedTotalDrinks': queue.totalDrinks
        })
    
    except json.JSONDecodeError as e:
        logging.error(f'JSONDecodeError: {e}')
        raise HTTPException(status_code = 400, detail = 'Invalid encoding for selectedDrinkIDs')
    except Exception as e:
        logging.error(f'Error: {e}')
        raise HTTPException(status_code = 400, detail = str(e))
        
@app.get("/history", response_class = HTMLResponse)
async def history(request: Request):
    return templates.TemplateResponse(
        "history.html",
        context = {
            "request": request,
            "history": queue.getCompletedItems(),
            "colors": MILK_COLORS,
            "totalOrders": queue.countCompletedOrders(),
            "totalDrinks": queue.DrinksComplete
        }
    )

@app.websocket("/newOrder")
async def newOrder(websocket: WebSocket):
    await connectionManager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception as e:
        logging.error(f'Connection error: {e}')
    finally:
        connectionManager.disconnect(websocket)

@app.post(f"/receive")
async def receiveData(request: Request):
    data = await request.json()
    try:
        order = Order(**data)
    except:
        return None 

    await queue.addOrder(order, update_db=True)
    queue_data = {
        "orders": [order.model_dump_json() for order in queue.orders],
        "totalOrders": queue.totalOrders,
        "totalDrinks": queue.totalDrinks,
    }
    await connectionManager.broadcast(json.dumps(queue_data))


if __name__ == "__main__":
    import uvicorn

    log_config = LOGGING_CONFIG
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.DEBUG)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.INFO)
    logging.info(f'Send orders in JSON to: {ADDRESS}:{PORT}/{ENDPOINT}')

    uvicorn.run(app, 
                host=ADDRESS, 
                port=PORT, 
                reload=True,
                reload_excludes=[DATABASE_URI,])
    