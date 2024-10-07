from Manager.app.models import Drink, Order
from Manager.app.scripts.services.CRUD import Connection

from pydantic import BaseModel

from typing import List, Set, Union, Optional
from itertools import product
from datetime import datetime
import logging, json, os, copy, asyncio

logging.basicConfig(level = logging.DEBUG)

class Batch(BaseModel):
    '''
    Class to hold drinks that can be made at the same time.

    Attributes:
    - drinks: List - List to store pending drinks in the batch
    - milk: str (default None) - String to dictate which milk type the batch requires
    - texture: str (default None) - String to dictate the milk texture
    - volume: float - The current volume of milk the batch requires
    '''
    drinks: List[Drink] = []
    milk: Union[str, None] = None
    texture: Union[str, None] = None
    volume: float = 0.0

    def __repr__(self):
        result = "Batch Instance\n"
        result += f"      Milk type: {self.texture} {self.milk}\n"
        result += "      Drinks:\n"
        for drink in self.drinks:
            result += f"      - {drink.customer}'s {drink.drink}\n"
        
        return result

    def add_drink(self, drink: Drink) -> None:
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

        2. First check inside the order to see if a batch of drinks 
           with similar milk type and texture can be created. If so create
           batch immediately after the order.

        3. For each drink that has not been placed in batches from the previous step,
           search for positions infront of the new order within the queue, for orders or batches
           containing drinks with the same milk type and texture. Search indexes starting from the
           index closest to the original order. Indexes included in the search must be greater than
           MIN_DRINK_NUMBER_OPT (N) positions in the queue (queue.totalDrinks).

        4. If the drink, and drinks at the index can be grouped together into a Batch,
           create a new Batch object at the index in the queue, and move drinks into the Batch instance.

           If the drink can't be grouped with drinks at that index, try the next index in the list of indexes under
           the corresponding milk type and texture in the lookupTable. If all searchable indexes have been tried, 
           keep the drink within the order at its original position in the queue.

        5. Update lookup table with new postions should drinks be moved into batches.
           Drinks can only be added to batches, not removed.
    '''

    def __init__(self):
        self.orders: List[Order, Batch] = []
        self.orderHistory: List[Order] = []
        self.orderHistoryIndex: dict = {}
        self.totalOrders: int = 0
        self.totalDrinks: int = 0
        self.OrdersComplete: int = 0
        self.DrinksComplete: int = 0
        self._initialize_lookupTable()
        self.connection: Optional[Connection] = None

################################################# INIT AND DUNDER METHODS #######################################################        
    @classmethod
    async def create(cls, URI: str):
        self = cls()
        self.connection = await Connection.new(URI)
        return self

    def _initialize_lookupTable(self):
        RELATIVE_PATH = "../../../config/config.json"
        CONFIG_FILE_PATH = os.path.join(
            os.path.dirname(__file__), RELATIVE_PATH
        )

        with open(CONFIG_FILE_PATH, 'r') as f:
            data = json.load(f)

        MILKS = data.get('milks', [])
        TEXTURES = data.get('textures', [])
        COMBINATIONS = product(MILKS, TEXTURES)

        self.__SEARCH_DEPTH = data.get('SEARCH_DEPTH')
        self.lookupTable: dict[str, Set[int]] = {
            f"{milk}_{texture}": set() for milk, texture in COMBINATIONS
        }

    async def _load_from_db(self) -> None:
        orders = await self.connection.getQueue()

        for order in orders:
            self.orderHistory.insert(0, order)
            if order.timeComplete:
                self.DrinksComplete += len(order.drinks)
                continue
            else:
                live_order = copy.deepcopy(order)
                live_order.drinks = [
                    d for d in live_order.drinks if not d.timeComplete
                ]
                await self.addOrder(live_order, update_db=False)
                self.DrinksComplete += len(order.drinks) - len(live_order.drinks)
        return None

    def __repr__(self):
        output = [f"Queue Instance @{hex(id(self))}:\n", "Orders:\n"]

        for index, order in enumerate(self.orders):
            output.append(f"{index:<5} {repr(order)}\n")

        output.append(f"\nDrinks in Queue: {self.totalDrinks}")
        output.append(f"\nOrders in Queue: {self.totalOrders}\n")

        return "".join(output)
    

########################################## PRIVATE LOOKUPTABLE & DATA MANIPULATION METHODS ##########################################
    def _remove_item_from_lookupTable(self, position: int) -> None:
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
        'Drops orders with no drinks in order.drinks from self.orders'
        i = 0
        while i < len(self.orders):
            if not self.orders[i].drinks:
                self.orders.pop(i)
                self._remove_item_from_lookupTable(i)
            else:
                i += 1

        self.totalOrders = len(set(drink.orderID for order in self.orders for drink in order.drinks))

    def _update_lookupTable_on_Batch(self, position: int, milk_type: str) -> None:
        '''
        Batches are always created immediately infront of an existing order. Therefore if a new order
        spawns batches infront of its own position in the queue, everything that is behind the new batch's
        position (i) in the queue, needs to have its index in the lookupTable incremented by +1 for each new batch.
        '''
        for k, v in self.lookupTable.items():
            if not v:
                continue
            elif v:
                self.lookupTable[k] = set(i+1 if i > position - 1 else i for i in v)


################################################# PUBLIC METHODS ##########################################################
    async def addOrder(self, order: Order, update_db: bool) -> None:
        self.orders.append(order)
        self.orderHistory.insert(0, copy.deepcopy(order))

        # Update orderHistory hashmap
        # Previous implimentation of Queue did not have orderHistoryIndex leading to traversal of entire orderHistory list
        # to update timeComplete in both orders and another nested traversal of the drinks list in each order.
        # This lead to minimum quadratic time complexity (frontend waiting 3 seconds to respond).
        # Now impliment hashmap to keep track of the index of orderIDs as well as what drinkIDs they have.
        self.orderHistoryIndex[order.orderID] = {
            'drinkIDs': set(d.identifier for d in order.drinks),
            'index': -1} 
        for idx in self.orderHistoryIndex.keys():
            self.orderHistoryIndex[idx]['index'] += 1

        new_order_index = len(self.orders) - 1
        self.totalOrders += 1
        self.totalDrinks += len(order.drinks)
        
        if update_db:
            await self.connection.addOrder(order)

        # If order has mutiple drinks, you may want to batch drinks with others
        # near the original order's position, else if it a single drink
        # you can move the individual forward in the queue any amount
        search_depth = new_order_index

        # Prioritize creating batches of same milk type within the order,
        # by searching inside order.drinks first.
        if len(order.drinks) > 1:
            grouped_drinks = order.group_drinks()
            search_depth = self.__SEARCH_DEPTH
            if grouped_drinks:
                for group in grouped_drinks:
                    if len(group) > 1:
                        # Create batches of drinks with same milk type
                        batch = Batch()
                        list(map(lambda drink: batch.add_drink(drink), group)) # Add drinks to batch
                        list(map(lambda drink: order.drinks.remove(drink), group)) # Remove drink from original order
                        self.orders.insert(new_order_index, batch) # Batch is inserted in front of original order
                        try:
                            self.lookupTable[f"{batch.milk}_{batch.texture}"].add(new_order_index)
                        except KeyError:
                            continue
                        new_order_index += 1 # Batch inserted infront so new order is moved back in the queue by one
                    else:
                        continue

        # For remaining drinks, have option to search for orders ahead
        for drink in order.drinks:
            if drink.milk == "No Milk":
                continue
            milk_type = f"{drink.milk}_{drink.texture}"
            batch_found = False
            indexes = [
                i for i in self.lookupTable[milk_type] if 1 < i and 
                new_order_index - search_depth <= i < new_order_index 
                ]
            
            for index in indexes:
                # Check if drink can be added to an existing batch
                if isinstance(self.orders[index], Batch):
                    batch: Batch = self.orders[index]
                    if batch.can_add_drink(drink):
                        batch.add_drink(drink)
                        order.drinks.remove(drink)
                        batch_found = True
                        break
                
                # Check if drink can be batched with a drink from existing order
                elif isinstance(self.orders[index], Order):
                    existing_order: Order = self.orders[index]
                    similar_drinks = [
                        d for d in existing_order.drinks if d.milk == drink.milk and
                        d.texture == drink.texture
                    ]

                    if similar_drinks:
                        batch = Batch()
                        for d in similar_drinks + [drink]:
                            batch.add_drink(d)
                        list(map(lambda d: existing_order.drinks.remove(d), similar_drinks))
                        order.drinks.remove(drink)
                        self.orders.insert(index, batch)
                        new_order_index += 1
                        self._update_lookupTable_on_Batch(index + 1, milk_type)
                        batch_found = True
                        break

            if not batch_found:
                self.lookupTable[milk_type].add(new_order_index)
        
        self._clean_empty_orders() 


    async def completeDrinks(self, drink_identifiers: List[int]) -> None:
        """
        Logic to complete one or more drinks and remove it from the preparation list.

        Parameters:
            - drink_identifiers: List[int] list of drink identifiers that are to be removed from the queue
        """
        time_complete = datetime.now().time()
        # Use sets for O(1) time complexity
        complete_drink_identifier_set: set[int] = set(drink_identifiers)
        order_identifier_set: set[int] = set() 

        for item in self.orders:
            item_drinkIDs = set(d.identifier for d in item.drinks)
            if complete_drink_identifier_set & item_drinkIDs:
                for drink in item.drinks:
                    if drink.identifier in drink_identifiers:
                        order_identifier_set.add(drink.orderID) # Add drink's parent order to list of orders to be updated
                item.drinks = [
                    drink for drink in item.drinks if drink.identifier not in drink_identifiers
                ]

        self._clean_empty_orders()

        for orderID in order_identifier_set:
            idx = self.orderHistoryIndex[orderID]['index']
            order = self.orderHistory[idx]

            for drink in order.drinks:
                if drink.identifier in complete_drink_identifier_set:
                    drink.timeComplete = time_complete
                    if self.connection:
                        await self.connection.completeDrink(drink.identifier, time_complete)

            if all(drink.timeComplete for drink in order.drinks):
                self.orderHistory[idx].timeComplete = time_complete
                self.OrdersComplete += 1
                if self.connection:
                    await self.connection.completeOrder(order.orderID, time_complete)

        self.totalDrinks -= len(complete_drink_identifier_set)
        self.DrinksComplete += len(complete_drink_identifier_set)


    async def completeItem(self, index: int) -> None:
        """
        Logic to complete an entire Batch or Order and remove it from the preparation list.

        Parameters:
            - index: int index of the item to be completed.
        """
        drink_identifiers = [d.identifier for d in self.orders[index].drinks]
        await self.completeDrinks(drink_identifiers)
        

    def getCompletedItems(self) -> List[Order]:
        out = []
        for order in self.orderHistory:
            completed_drinks = [drink for drink in order.drinks if drink.timeComplete is not None]
            if completed_drinks:
                order_copy = copy.deepcopy(order)
                order_copy.drinks = completed_drinks
                out.append(order_copy)
        return out


    def countCompletedOrders(self) -> int:
        return len([order for order in self.orderHistory if order.timeComplete])
    