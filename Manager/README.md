# About

Covfefes/Waiter is the order queue management system. 

# Logic

To ensure the queueManager does not move drinks that the barista may have already started
preparing, the variable MIN_ORDER_NUMBER_OPT is set to some arbritrary value such that orders with
an index in the buffer less than MIN_ORDER_NUMBER_OPT, are not moved. This also ensures orders are prepared
succinctly during quiet times when customers are more likely to complain not receiving their drink first despite
ordering first.

The logic will look ahead for drinks that have the same milk, texture, and temperature, and group them together
to maximize milk steaming efficiency; the main bottle neck of coffee preparation. Additionally, two single
shot drinks can be prepared using the same grouphead reducing wastage, and increasing productivity.

To prevent customers from waiting too long, each order will have a maximum number of times it can be moved backwards in the queue. Drink orders can be moved forwards an indefinite amount of times.