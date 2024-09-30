import requests
from Manager.app.models import Order
import logging

logging.basicConfig(level = logging.DEBUG)

orderAPI_endpoint = 'http://127.0.0.1:8000/random_order'

def fetchOrder() -> Order|None:
    '''Returns an order that is randomly generated from the /order HTTP endpoint.'''
    try:
        response = requests.get(orderAPI_endpoint)
    except requests.exceptions.ConnectTimeout as e:
        logging.error(f'Connection timed out: {e}')
        return None
    except requests.exceptions.TooManyRedirects as e:
        logging.error(f'Too many redirects: {e}')
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f'Request error: {e}')
        return None
    
    try:
        responseData: str = response.json()
    except requests.JSONDecodeError as e:
        logging.error(f'JSON Decode error: {e}')
        return None

    order = Order.model_validate_json(responseData)

    return order
