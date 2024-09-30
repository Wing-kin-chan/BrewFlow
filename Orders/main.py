from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from Orders.app.generate_order import generateOrder
from Manager.app.models import Order
import httpx, json, logging

logging.basicConfig(level = logging.DEBUG)
app = FastAPI()

@app.get('/', response_class = HTMLResponse)
def home():
    pageHTML = """
    <html>
    <head>
        <title>FastAPI Form</title>
    </head>
    <body>
        <h1>Enter a URL</h1>
        <form action="/send_order" method="post">
            <label for="url">HTTP Address:</label>
            <input type="text" id="url" name="url" placeholder="Enter URL here">
            <button type="submit">Send</button>
        </form>
    </body>
    </html>
    """
    return pageHTML

@app.post("/send_order")
async def sendOrder(url: str = Form(...)):
    order: Order = generateOrder()
    data: dict = json.loads(order.model_dump_json())
    logging.info(f"Sending Order: {data}")

    async with httpx.AsyncClient() as client:
        await client.post(
            url,
            headers = {"Content-Type": "application/json"}, 
            json = data
        )
        return RedirectResponse(url = "/", status_code = 303)

@app.get('/random_order', response_model = Order)
def getOrder():
    order = generateOrder()
    return JSONResponse(order.model_dump_json())
