import random, json, os
from typing import List

RELATIVE_PATH = "../../Menu/"
MENU_FILE_PATH = os.path.join(
    os.path.dirname(__file__), RELATIVE_PATH, "menu.json"
)

with open(MENU_FILE_PATH, 'r') as f:
    data = json.load(f)
MILKS: List[str] = data.get('milks', [])
TEXTURES: List[str] = data.get('textures', [])
DRINKS: List[dict] = data.get('drinks', [])
OPTIONS: List[str] = data.get('options', [])

def generateDrink() -> dict:
    '''
    Random drink generator.
    Generates an espresso based drink of certain type, with randomly chosen milk type, 
    shot number, milk texture and temperature, and other options.
    '''
    #Choose drink and milk type
    drink_choice = random.choice(DRINKS)
    if drink_choice['drink'] in ['Espresso', 'Long Black', 'Short Black']:
        milk_choice = "No Milk"
    else:
        milk_choice = random.choice(MILKS)
    drink_choice['milk'] = milk_choice

    #Choose options
    options = set()
    n = random.randint(0, 2)
    while n > 0:
        option = random.choice(OPTIONS)
        options.add(option)
        n -= 1
    drink_choice['options'] = list(options)

    base_shots = drink_choice['shots'] 

    if 'Single Shot' in options:
        drink_choice['shots'] = 1
    elif 'Extra Shot' in options:
        drink_choice['shots'] = base_shots + 1 
    elif 'Extra Shot x2' in options:
        drink_choice['shots'] = base_shots + 2
    else:
        drink_choice['shots'] = base_shots 

    #Choose milk temperature
    if 'Extra Hot' in options:
        drink_choice['temperature'] = 'Extra Hot'
    if 'Warm' in options:
        drink_choice['temperature'] = 'Warm'
    else:
        drink_choice['temperature'] = 'Normal'

    drink_choice['orderID'] = None
    drink_choice['customer'] = None
    drink_choice['timeComplete'] = None
    drink_choice['timeReceived'] = None

    return drink_choice
