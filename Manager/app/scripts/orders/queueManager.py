from Menu import Drink, Order
from typing import List, Set
from itertools import product
import logging, json, os

logging.basicConfig(level = logging.DEBUG)

RELATIVE_PATH = "../../../../Menu/menu.json"
MENU_FILE_PATH = os.path.join(
    os.path.dirname(__file__), RELATIVE_PATH
)
with open(MENU_FILE_PATH, 'r') as f:
    data = json.load(f)

MILKS = data.get('milks', [])
TEXTURES = data.get('textures', [])
COMBINATIONS = product(MILKS, TEXTURES)

class Batch:
    '''
    Class to hold drinks that can be made at the same time.

    Attributes:
    - drinks: List - List to store pending drinks in the batch
    - milk: str (default None) - String to dictate which milk type the batch requires
    - texture: str (default None) - String to dictate the milk texture
    - volume: float - The current volume of milk the batch requires
    '''

    def __init__(self):
        self.drinks: List[Drink] = []
        self.milk: str|None = None
        self.texture: str|None = None
        self.volume: float = 0

    def __repr__(self):
        result = "Batch Instance\n"
        result += f"      Milk type: {self.texture} {self.milk}\n"
        result += "      Drinks:\n"
        for drink in self.drinks:
            result += f"      - {drink.customer}'s {drink.drink}\n"
        
        return result

    def add_drink(self, drink: Drink):
        if not self.milk:
            self.milk = drink.milk
        if not self.texture:
            self.texture = drink.texture
        self.drinks.append(drink)
        self.volume += drink.milk_volume

    def can_add_drink(self, drink: Drink) -> bool:
        return(
            self.milk == drink.milk and
            self.texture == drink.texture and
            self.volume + drink.milk_volume <= 5
        )

class Queue:
    '''
    Queue class to store orders and batches.

    Attributes:
    - orders: List[Order] - List to store pending drink orders
    - totalOrders: int - Keeps track of how many orders there are
    - totalDrinks: int - Keeps track of how many drinks awaiting preparation
    - OrdersComplete: int - Number of completed orders
    - DrinksComplete: int - Number of drinks made
    - lookupTable: dict - Hashmap of index/queue position of drink types

    Workflow queue optimization logic:
        1. Add new order to queue
        2. For each drink, add the order's position in the queue's order list, 
           to the relevant milk texture key in the lookup table.
        3. If there are more than MIN_DRINK_NUMBER_OPT (N) drinks in the queue (queue.totalDrinks),
           for each drink after the first N drink, starting with the N+1 drink, search for an index with the same
           milk texture in lookup table. 
           
           If a the drink, and drinks at the index can be grouped together into a Batch,
           create a new Batch object at the index in the queue, and move drinks into the Batch instance.

           If the drink can't be grouped with drinks at that index, try the next index in the list of indexes under
           the corresponding milk type and texture in the lookupTable. If all indexes have been tried, keep the drink within
           the order at its original position in the queue.

        4. Update lookup table with new postions should drinks be moved into batches.
        5. Drinks can only be added to batches, not removed.
    '''

    def __init__(self):
        self.orders: List[Order, Batch] = []
        self.totalOrders: int = 0
        self.totalDrinks: int = 0
        self.OrdersComplete: int = 0
        self.DrinksComplete: int = 0
        # Use hash table as lookup is O(1) rather than searching for
        # drink in the orders attribute which is O(n) at worst.
        self.lookupTable: dict[str, Set[int]] = {
            f"{milk}_{texture}": set() for milk, texture in COMBINATIONS
        }

    def __repr__(self):
        # Basic info about the Queue instance
        output = [f"Queue Instance @{hex(id(self))}:\n", "Orders:\n"]

        # Adding each order's repr along with its index
        for index, order in enumerate(self.orders):
            output.append(f"{index:<5} {repr(order)}\n")

        # Summary of the total drinks and orders
        output.append(f"\nDrinks in Queue: {self.totalDrinks}")
        output.append(f"\nOrders in Queue: {self.totalOrders}\n")

        return "".join(output)

    def remove_item_from_lookupTable(self, position: int):
        '''
        When an item is removed at queue position/index N,
        all values of N are purged from the lookup table.
        Remaining values greater than N will have 1 subtracted to move them forward in the queue.
        '''
        for k, v in self.lookupTable.items():
            if not v:
                self.lookupTable[k] = set()
            if position in v:
                self.lookupTable[k] = v.remove(position)
            self.lookupTable[k] = set(i-1 if i > position else i for i in v)
    
    def _clean_empty_orders(self):
        i = 0
        while i < len(self.orders):
            if not self.orders[i].drinks:
                self.orders.pop(i)

                for key, indices in self.lookupTable.items():
                    self.lookupTable[key] = set(index-1 if index > i else index for index in indices)
            else:
                i += 1

    def update_lookupTable_on_Batch(self, position: int, milk_type: str):
        '''
        Batches are always created immediately after an existing order;
        If Order (O) at index N, has drink A, and A is added to Batch (B),
        orders.index(B) == orders.index(O) + 1.

        Thus if A has an index I in the lookupTable, within the key of A's
        corresponding milk type, we need to update A's index to reflect the batch's position.
        '''
        for k, v in self.lookupTable.items():
            if k == milk_type:
                self.lookupTable[k] = set(i+1 if i >= position - 1 else i for i in v)
            elif v:
                self.lookupTable[k] = set(i+1 if i > position - 1 else i for i in v)

    def addOrder(self, order: Order):
        self.orders.append(order)
        self.totalOrders += 1
        self.totalDrinks += len(order.drinks)
        original_position = len(self.orders) - 1
        
        # Group drinks into batches if possible
        for drink in order.drinks[:]:
            milk_type_texture = f'{drink.milk}_{drink.texture}'
            batch_found = False

            # Check if drink can be added to existing batch
            try:
                indexes = [i for i in self.lookupTable[milk_type_texture] if 1 < i <= original_position]
                indexes.sort(reverse = True)
                #Check for batches closest to the position of original order first
                for index in indexes:
                    # Check if drink can be added to a batch
                    if isinstance(self.orders[index], Batch):
                        batch = self.orders[index]
                        if batch.can_add_drink(drink):
                            batch.add_drink(drink)
                            self.orders[original_position].drinks.remove(drink)
                            batch_found = True
                
                # Check if a new batch can be created
                    elif isinstance(self.orders[index], Order):
                        existing_order = self.orders[index]
                        similar_drinks = [
                            d for d in existing_order.drinks if d.milk == drink.milk and 
                            d.texture == drink.texture and
                            id(d) != id(drink)
                        ]

                        if similar_drinks:
                            batch = Batch()
                            for d in similar_drinks + [drink]:
                                batch.add_drink(d)
                            batch.volume = sum(d.milk_volume for d in batch.drinks)
                            self.orders[-1].drinks.remove(drink)
                            self.orders.insert(index + 1, batch)
                            self.update_lookupTable_on_Batch(index + 1, milk_type_texture)
                            batch_found = True
                        
                        # Delete similar drinks from existing order as they are in batch
                        for d in similar_drinks:
                            existing_order.drinks.remove(d)

                # If drink can't be allocated to a batch, keep its position in order and index it
                if not batch_found:
                    self.lookupTable[milk_type_texture].add(original_position)

            except KeyError:
                continue

        logging.debug(f"{self}")
        logging.debug(f"{self.lookupTable}")
                
        # Clear any instance of an order that have no drinks from the queue
        self._clean_empty_orders()

    def completeOrder(self, orderID: int):
        self.orders = [item for item in self.orders if item.orderID != orderID]
        logging.info(f'Order {orderID} complete.')