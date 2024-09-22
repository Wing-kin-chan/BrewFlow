from fastapi import FastAPI, Request, Form, BackgroundTasks, WebSocket, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from Manager.app.scripts.queueManager import Queue
from Manager.app.scripts.services import ConnectionManager, FormData, JSONList
from typing import Optional
from Menu import Order
import os, json, uuid, logging

RELATIVE_PATH = "../Menu/menu.json"
MENU_FILE_PATH = os.path.join(
    os.path.dirname(__file__), RELATIVE_PATH
)

app = FastAPI()
global queue
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
            "colors": MILK_COLORS}
        )

@app.post("/complete")
async def complete(
    selectedDrinkIDs: Optional[str] = Form(default = '[]'),
    selectedItemIndex: Optional[str] = Form(default = None)
):
    try:
        form_data = FormData(
            selectedDrinkIDs = json.loads(selectedDrinkIDs),
            selectedItemIndex = int(selectedItemIndex)
        )

        if form_data.selectedDrinkIDs:
            queue.completeDrinks(form_data.selectedDrinkIDs.root)
            logging.info(f'Completed drinks: {form_data.selectedDrinkIDs.root}')
        if form_data.selectedItemIndex is not None:
            queue.completeItem(form_data.selectedItemIndex)
            logging.info(f'Completed Order at idx: {form_data.selectedItemIndex}')

        return JSONResponse(content = {
            'updatedOrderList': [order.model_dump_json() for order in queue.orders],
            'updatedTotalOrders': queue.totalOrders
        })
    
    except json.JSONDecodeError as e:
        logging.error(f'JSONDecodeError: {e}')
        raise HTTPException(status_code = 400, detail = 'Invalid encoding for selectedDrinkIDs')
    except Exception as e:
        logging.error(f'Error: {e}')
        raise HTTPException(status_code = 400, detail = str(e))

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