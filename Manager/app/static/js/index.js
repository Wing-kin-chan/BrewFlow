const socket = new WebSocket(`ws://${window.location.host}/newOrder`)

socket.onopen = function() {
    console.log("WebSocket Open");
};

socket.onmessage = function(event) {
    const data = JSON.parse(event.data);

    const queue = data.orders.map(order => JSON.parse(order));
    const totalOrders = data.totalOrders;

    updateOrderList(queue, totalOrders);
}

socket.onerror = function(error) {
    console.error("WebSocket error:", error);
};

socket.onclose = function() {
    console.log("WebSocket closed");
};

function updateOrderList(queue, totalOrders) {
    const totalOrdersElement = document.querySelector('.order-count');
    totalOrdersElement.textContent = totalOrders;

    const orderList = document.getElementById('orderList');
    orderList.innerHTML = '';

    queue.forEach((order, orderIndex) => {
        const orderCard = document.createElement('div');
        orderCard.classList.add('order-batch-card');
        orderCard.id = `order-${orderIndex}`;
        orderCard.setAttribute('onclick', `selectOrder(${orderIndex}, event)`);

        let orderHeaderHTML = `
            <div class="order-batch-card-header">
                <h2>Order</h2>
                <h3>${order.customer}</h3>
                <h6>${order.time}</h6>
            </div>`;

        let orderBodyHTML = '<div class="order-batch-card-body"><ul>';

        order.drinks.forEach(drink => {
            let drinkOptionsHTML = '';
            drink.options.forEach(option => {
                drinkOptionsHTML += `<p>${option}</p>`;
            });

            const drinkHTML = `
                <li>
                    <div class="drink-card" id="drink-${drink.identifier}" onclick="selectDrink(${drink.identifier}, event)">
                        <div class="drink-card-header ${drink.milk}">
                            <span class="drink-name">${drink.drink}</span>
                        </div>
                        <div class="drink-card-body">
                            <ul>
                                <li class="drink-card-text-info">
                                    <p>${drink.milk.replace('Milk', '')} Milk</p>
                                    ${drinkOptionsHTML}
                                </li>
                            </ul>
                        </div>
                    </div>
                </li>`;
            
            orderBodyHTML += drinkHTML;
        });

        orderBodyHTML += '</ul></div>';

        orderCard.innerHTML = orderHeaderHTML + orderBodyHTML;
        orderList.appendChild(orderCard);
    });
};

let selectedItemIndex = null
let selectedDrinkIDs = []

function selectOrder(orderIndex, event) {
    event.stopPropagation();

    let orderElement = document.getElementById(`order-${orderIndex}`);

    if (orderElement.classList.contains('selected')) {
        orderElement.classList.remove('selected');
        selectedItemIndex = null
    } else {
        deselectAll();
        orderElement.classList.add('selected');
        selectedItemIndex = orderIndex
    }
}

function selectDrink(drinkIdentifier, event) {
    event.stopPropagation();

    let drinkElement = document.getElementById(`drink-${drinkIdentifier}`);

    if (selectedDrinkIDs.includes(drinkIdentifier)) {
        selectedDrinkIDs.filter(id => id !== drinkIdentifier);
        drinkElement.classList.remove('selected');
    } else {
        selectedDrinkIDs.push(drinkIdentifier);
        drinkElement.classList.add('selected');
    }
}

function deselectAll() {
    document.querySelectorAll('.order-batch-card.selected').forEach(order => {
        order.classList.remove('selected');
    });

    document.querySelectorAll('.drink-card.selected').forEach(drink => {
        drink.classList.remove('selected');
    });

    selectedItemIndex = null;
    selectedDrinkIDs = [];
}
