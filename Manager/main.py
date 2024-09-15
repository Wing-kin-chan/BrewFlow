from fastapi import FastAPI, Request, Form, BackgroundTasks, WebSocket
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from Manager.app.scripts.queueManager import Queue
from Manager.app.scripts.services import ConnectionManager
from Manager.app.scripts.services import Item
from Menu import Order
import os, json, uuid, logging

RELATIVE_PATH = "../Menu/menu.json"
MENU_FILE_PATH = os.path.join(
    os.path.dirname(__file__), RELATIVE_PATH
)

app = FastAPI()
queue = Queue()
connectionManager = ConnectionManager()

STATIC_DIR = os.path.join(os.path.dirname(__file__), "app/static")
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "app/templates")
ENDPOINT = uuid.uuid4().hex

app.mount("/static", StaticFiles(directory = STATIC_DIR), name = "static")
templates = Jinja2Templates(directory = TEMPLATE_DIR)

with open(MENU_FILE_PATH, 'r') as f:
    data = json.load(f)
    MILK_COLORS = data.get('MILK_COLORS')
    ADDRESS = data.get('ADDRESS')
    PORT = data.get('PORT')

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

@app.get("/history", response_class = HTMLResponse)
async def history(request: Request):
    return templates.TemplateResponse(
        "history.html",
        context = {
            "request": request,
            "history": queue.getCompletedItems(),
            "colors": MILK_COLORS
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

    queue.addOrder(order)
    queue_data = {
        "orders": [order.model_dump_json() for order in queue.orders],
        "totalOrders": queue.totalOrders,
    }
    await connectionManager.broadcast(json.dumps(queue_data))


if __name__ == "__main__":
    import uvicorn
    logging.info(f'Receive orders on: 127.0.0.1:8080/{ENDPOINT}')
    uvicorn.run(app, host = ADDRESS, port = PORT)