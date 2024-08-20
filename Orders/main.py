from fastapi import FastAPI
from fastapi.responses import JSONResponse
from Orders.app.generate_order import generateOrder
from Menu import Order

app = FastAPI()

@app.get('/order', response_model = Order)
def getOrder():
    order = generateOrder()
    return JSONResponse(order.model_dump_json())
