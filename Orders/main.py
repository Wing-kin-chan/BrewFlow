from fastapi import FastAPI
from fastapi.responses import JSONResponse
from Orders.app.generate_order import Order

app = FastAPI()

@app.get('/order', response_model = Order)
def getOrder():
    order = Order.generateOrder()
    return JSONResponse(order.model_dump_json())
