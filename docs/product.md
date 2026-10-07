# BrewFlow
BrewFlow is a barista workflow optimizer that is aimed at reducing barista cognitive load, increasing milk steaming efficiency, minimizing milk context switching and errors, and improving customer wait times and satisfaction.

## Requirements
### Drink Class
An abstract representation of a drink. This is a data class that should hold all attributes of the drink being prepared. The drink class is a child of its parent order. Attributes include:
    - orderID: The UUID of the order
    - drink: The name of the drink
    - milk: The type of milk in the drink
    - milk_volume: The amount of milk
    - shots: Number of espresso shots
    - temperature: ENUM[Warm, Normal, Extra Hot]
    - texture: The texture of the milk ENUM[Extra Wet, Wet, Dry, Extra Dry]
    - options: Additional drink options such as toppings or syrups
    - customer: The customer name
    - identifier: The UUID of the individual drink as an order may contain multiple drinks
    - time_received: Time the order containing the drink was made
    - time_complete: The time the drink was marked complete

### Order Class
An abstract representation of an order. This is a data class that should hold all attributes of a customer order. Attributes include:
    - orderID: The UUID of the order
    - customer: The name of the customer who made the order
    - date_received: The date the order was received
    - time_received: The time the order was received
    - time_completed: The time at with the entire order was marked complete, or all of its child drinks were marked complete.

### Queue Management Logic
The logic behind queue management is the following:
    1. Queue holds incoming drinks in an array
    2. New order is added containing drinks
    3. Group drinks based on matching milks and textures into batches
    4. Each batch has a maximum milk capacity based on user configuration
    5. For every new drink that is added to the queue, search for any batches that are of the same milk and texture. Conditions:
        - If a batch exists and has available capacity add the drink to the batch.
        - If another drink of same milk and texture exists, create a batch at the existing drink's position in the queue.
        - If no other drinks or batches of the same milk and texture exists, add drink to the end of the queue.

### Order History
A order history page containing a list of orders and drinks that have been completed. There is no batching in this list.

### Order History Database
A relational database that holds information regarding past and current orders and drinks. Has two tables; Orders, and Drinks.

Orders:
    - orderID: String, Primary key
    - customer: String
    - dateReceived: Date
    - timeReceived: Time
    - timeComplete: Time

Drinks:
    - identifier: String, Primary key
    - orderID: String, Foreign key to Orders:orderID
    - drink: String
    - milk: String
    - milkVolume: integer
    - shots: integer
    - temperature: String
    - texutre: String
    - Options: String
    - Customer: String
    - timeReceived: String
    - timeComplete: String

### Add Order
Function to add order containing drink or drinks to the queue. Given an order containing any number of drinks, when the order and drinks are added to the queue, then the order and all of its child drinks must have their time_received attribute updated with the current time.

### Complete Drink
Function to complete a selected drink. Given a drink, when it is marked complete, then its time_completed attribute should be updated with the current time and the drink should be moved to the order history list.

### Complete Order
Function to complete a selected order and all child drinks. Given an order containing a drink or multiple drinks, when the order is marked compelte, then the time_complete attribute of the order and every child drink should be updated with the current time and the order and drinks should be moved to the order history list.

### Complete Drinks
Function to complete selected drinks. Given a list of selected drinks, when the selected drinks are marked completed, then their time_completed attribute should be updated with the current time and the drinks should be moved to the order history list.

### Queue Page
The Queue Page is the default page that baristas see. This page displays all drinks and orders that have not yet been marked completed with the oldest orders and drinks on the left and the newer orders and drinks to the right.

### Order History Page
The Order History page displays all orders and drinks that have been completed for the given service period. Drinks are grouped by their original orders and not batched by milk and milk texture type.

### Configuration Page
The Configuration page allows baristas to specify the following parameters:
    - Max batch size: The maximum amount of milk their largest steaming jug can hold.
    - Minimum search distance: Minimum number of drinks or orders from the start of the queue the batching function can search in and start grouping new drinks into.
    - Smart queuing: A boolean toggle to switch between FIFO and milk batching queue modes.
    - Service periods: Create service periods by day and specify the times they start and end. 

### POS Page

### Menu Page

### Stock Page

### Performance Page