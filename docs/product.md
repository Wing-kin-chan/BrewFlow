# BrewFlow
BrewFlow is a barista workflow optimizer that is aimed at reducing barista cognitive load, increasing milk steaming efficiency, minimizing milk context switching and errors, and improving customer wait times and satisfaction.

## Usage
The application should be a lightweight browser based SaaS product. It should be able to run on low-end portable devices such as tablets that are used as kitchen and bar order screens in many small businesses. For cafes with multiple coffee stations, each coffee station should have their separate queue instance, for now just assume multiple POS systems feed orders into one queue system.

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
The point of sales (POS) page will be the screen used to select items to add to a customer's order. It should have food and drink items grouped into tabs configured in the menu page. The tabs should be present in a navigation bar on the left handside of the screen. To the right of the navigation bar and in the centre of the page is an area that should display the food or drink items present in the group. On the right hand side of the page, there should be an area to display the customer's basket, item quantities and cost, and total cost. Additionally, it should have a search bar for staff members to search for items manually and add the desired result to the customer basket.

When an order is complete and payment processed, only the drinks items should be sent to the queue page.

### Menu Page
The menu page is an area where a cafe staff member can add, edit, and remove food and drink items on their menu. Food and drink items should have the following attributes:
    - Item name
    - Item picture
    - Item cost
    - Externally sourced?
    - Item ingredients and amounts

Food and drink items can be put into groups, a group can be made or deleted by the appropriate staff member. Each group and its child items will correspond to their respective tab on the POS page. If the item is externally sourced, adding ingredients will be disabled. When adding ingredients to a food item, users will be able to search a dropdown of their existing ingredients, or add a new ingredient. A newly added ingredient will create a new record in their stock page.  

### Stock Page
The stock page will be an interactive visualization of a stock database table for the cafe. There will be two tables, one for raw ingredients, and one for menu items. The table for raw ingredients should have the following columns:
    - Item name
    - Supplier
    - Current quantity
    - Unit cost

The table for menu items should have the following columns:
    - Item name
    - Sales (Currency)
    - Sales quantity
    - Amount remaining
    - Expected Sales
    - Waste
    - Variance

The stock page will give the user ability to update quantities for each record either through restocking (adding stock) or wastage (manually decreasing stock not through sales or wastage). When a menu item that uses ingredients is restocked, the associated ingredients used for that menu item should be adjusted accordingly (see item ingredients and amounts for items in the menu page).

### Performance Page
The performance page will present a dashboard to show cafe performance metrics. Metrics include, in order of importance:
    - Net Sales
    - Gross Sales
    - Ingredient Cost
    - Wastage
    - Variance
    - Top 5 drinks items
    - Top 5 food items
    - Low stock items
    - Basket size
    - Drink preparation time

Metrics should be filterable by preset and custom date/time periods.

## Security
### Cafe Accounts 
There should be a record of cafe accounts. When a cafe logs into the application, they should only be able to access their menu, their stock, their order history, their performance page, their POS system, and their queueing system. 

### Payment Methods
BrewFlow will use Stripe as a payment provider. After checkout, provide a QR code for the customer to scan, or collect contact information such as and email or phone number which a payment link will be sent to.