from cmu_cpcs_utils import testFunction
from fc_utils import PQ
import math, copy

def almostEqual(x, y):
    return abs(x - y) <= 0.01

################################################################################
# Order
################################################################################

BUY = 'Buy'
SELL = 'Sell'

class Order:
    """An order to buy/sell a currency pair"""

    def __init__(self, base, quote, direction, price, quantity, time):
        """
        Initializes an order

        Args:
            base: The base currency
            quote: The quote currency
            direction: The direction (BUY or SELL)
            price: The price (amount of quote currency) for 1 unit of base currency
            quantity: The amount of the base currency to buy/sell
            time: The time the order was made

        Other Properties:
            fills: A list of (quantity, price) tuples representing amount 
                filled and the price it was filled at. This is a list
                because an order can be filled by multiple different orders
                at different prices, so we need to track all of them.
        """
        self.base = base
        self.quote = quote
        self.direction = direction
        self.price = price
        self.quantity = quantity
        self.time = time
        self.fills = []
    
    def __repr__(self):
        return f'Time {self.time} - {self.direction} {round(self.quantity,2)} {self.base}/{self.quote} @ {self.price}'
    
    def __eq__(self, other):
        return (isinstance(other, Order) and
            self.base == other.base and
            self.quote == other.quote and
            self.direction == other.direction and
            almostEqual(self.price, other.price) and
            almostEqual(self.quantity, other.quantity) and
            self.time == other.time)

    def __hash__(self):
        return hash((self.base, self.quote, self.direction, self.time))

################################################################################
# OrderBook
################################################################################

class OrderBook:
    """An order book for one currency pair"""

    def __init__(self):
        """
        Initializes an order book for a single currency pair.
        
        Stores both buy and sell orders that are pending fulfillment for the 
        currency pair. Stored to allow fast matching, prioritizing who is
        fulfilling the order. i.e.
        - Sellers will match with the buyer willing to pay the highest price
        - Buyers will match with sellers who want the lowest price
        - When tied, the earlier order is prioritized

        Properties:
            bids: The BUY orders that have yet to be fulfilled
            asks: The SELL orders that have yet to be fulfilled
        """
            
        self.bids = PQ(lambda order:(-order.price,order.time))
        self.asks = PQ(lambda order:(order.price,order.time))
        
    
    def __repr__(self):
        if self.bids.size() > 0 and self.asks.size() > 0:
            return f'mkt bid : {self.bids.peek()} vs. mkt ask - {self.asks.peek()}'
        elif self.bids.size() > 0:
            return f'mkt bid : {self.bids.peek()} vs. no mkt ask'
        elif self.asks.size() > 0:
            return f'no mkt bid vs. mkt ask - {self.asks.peek()}'
        else:
            return "No orders"
    
    def UpdateOrderInfo(self,order,order_to_fill):
        
        price_to_fill = order_to_fill.price
        quantity_to_fill = order_to_fill.quantity
        
        if quantity_to_fill >= order.quantity: # the order book covers all
            # update new order
            order.fills.append((order.quantity,price_to_fill))
            
            # update filled order
            order_to_fill.quantity -= order.quantity
            order_to_fill.fills.append((order.quantity,price_to_fill))
            
            # order quantity
            order.quantity = 0
            if order_to_fill.quantity == 0: 
                self.asks.pop() if order.direction == BUY else self.bids.pop() 
            
        else: # order needs to go deeper to the order book
            # update new order
            order.quantity -= quantity_to_fill
            order.fills.append((quantity_to_fill,price_to_fill))
            
            # update filled order
            order_to_fill.quantity = 0
            order_to_fill.fills.append((quantity_to_fill,price_to_fill))
            self.asks.pop() if order.direction == BUY else self.bids.pop() 
        
        
    def processOrder(self, order):
        """
        Updates the order book based on the order given.

        If the order can be fulfilled, it is fulfilled starting with the best
        offer currently available. The order given can be fully, partially,
        or not fulfilled. If not completely fulfilled, it is added to orders
        pending fulfillment. 
        
        Any orders filled (completely or partially) will have their quantity
        updated. They will also have a tuple (quantity, price) added to their
        list of fills.

        Args:
            order: The new order to fill.
        """

        direction = order.direction
        if direction == BUY:
            while order.quantity > 0 and self.asks.size()>0 and order.price >= self.asks.peek().price:
                order_to_fill = self.asks.peek()
                self.UpdateOrderInfo(order,order_to_fill)
            
            if order.quantity > 0:
                self.bids.push(order)
          
        elif direction == SELL:
            while order.quantity > 0 and self.bids.size()>0 and order.price <= self.bids.peek().price:
                order_to_fill = self.bids.peek()
                self.UpdateOrderInfo(order,order_to_fill)
            
            if order.quantity > 0:
                self.asks.push(order)

################################################################################
# Exchange
################################################################################

class Exchange:
    """A currency exchange"""
    def __init__(self):
        """Initializes a currency exchange

        Properties:
            orderBooks: A dictionary mapping currency pairs to order books
            tradingRound: An integer representing the current trading round
            traders: A list of trading bots that will place orders
        """
        # For simplicity, you must submit orders with this base/quote order
        self.orderBooks = {
            ('USD', 'EUR'): OrderBook(),
            ('USD', 'JPY'): OrderBook(),
            ('USD', 'GBP'): OrderBook(),
            ('USD', 'AUD'): OrderBook(),
            ('EUR', 'JPY'): OrderBook(),
            ('EUR', 'GBP'): OrderBook(),
            ('EUR', 'AUD'): OrderBook(),
            ('JPY', 'GBP'): OrderBook(),
            ('JPY', 'AUD'): OrderBook(),
            ('GBP', 'AUD'): OrderBook()
        }
        self.tradingRound = 0
        self.traders = []

    def addTrader(self, trader):
        """Adds a trader to the exchange. This trader should be at the end of the list.

        Args:
            trader: The trader to add
        """
        self.traders.append(trader)

    def performTradingRound(self):
        """Performs one trading round by gathering and processing orders from each trader.

        For now, loop through the traders in order and let them place orders. 
        Later, we will randomize the order every round for fairness.
        """
        for trader in self.traders:
            orders_to_place = trader.placeOrders(self.orderBooks,self.tradingRound)

            for curr_order in orders_to_place:
                trader.orders.append(curr_order)
                curr_order_book = self.orderBooks[(curr_order.base, curr_order.quote)]
                curr_order_book.processOrder(curr_order)

        for trader in self.traders:
            trader.handleFilledOrders()
        self.tradingRound += 1

################################################################################
# TradingBot
################################################################################

class TradingBot:
    """A trading bot. General trading bots do not place any orders. 
    
    This class will be subclassed to implement different bot types.
    """

    def __init__(self):
        """Initializes a trading bot.

        Properties:
            positions: a dictionary mapping currencies to quantities held.
            orders: a list of outstanding orders that have been placed.
        """
        self.positions = {
            'USD': 0,
            'EUR': 0,
            'JPY': 0,
            'GBP': 0,
            'AUD': 0
        }
        self.orders = []
    
    def placeOrders(self, orderBooks, tradingRound):
        """Returns a list of orders to place based on the current state of the exchange. 
        
        Starts by calling handleFilledOrders to update positions based on any
        orders that have been filled (i.e. if other bots placed orders that
        caused this bot's pending orders to be partially or fully filled).
        Updates the self.orders list with new orders placed, and returns a list
        of the new orders so the exchange can process them.

        Args:
            orderBooks: A dictionary mapping currency pairs to order books 
                containing all pending orders in the exchange.
            tradingRound: An integer representing the current trading round (how
                we represent time).

        Returns:
            A list of orders to place in the exchange. These orders are also
            added to the self.orders list so the bot can track the orders filled
            later.
        """
        # update positions based on orders partially or fully filled by other bots
        self.handleFilledOrders()
        return []
    
    def handleFilledOrders(self):
        """ Updates positions based on fills from the existing orders. 
        
        If an order is fully filled, it is removed from the list of orders.

        Positions are updated based on quantity and price filled. For example,
        if an order was filled to buy 10 (quantity) USD (base)/JPY (quote) for 5
        (price): USD increases by 10, but JPY decreases by 10 * 5 = 50 because
        each unit of USD was purchased with 5 JPY.
        """

        for curr_order in self.orders:

            if curr_order.fills !=[]:
                for fill_num, fill_px in curr_order.fills:
                    curr_base = curr_order.base
                    curr_quote = curr_order.quote
                    multiplier = 1 if curr_order.direction == BUY else -1
                    self.positions[curr_base] += fill_num * multiplier
                    self.positions[curr_quote] += fill_num * -multiplier * fill_px
                    #print("curr", self.positions)
                
                # set the fills to be []
                curr_order.fills == []
        
        for curr_order in self.orders:  
            # if order fully filled, we remove it from the trader's order list
            if curr_order.quantity == 0: 
                self.orders.remove(curr_order)

    def calculateUSDValue(self, orderBooks):
        """Gets the estimated value of the trading bot's portfolio in USD.

        Args:
            orderBooks: A dictionary mapping currency pairs to order books 
                containing all pending orders in the exchange. These are used to
                estimate the fair value of USD in terms of the other currencies
                being traded.

        Returns:
            The estimated value of the bot's portfolio in USD, or None if any of
            the order books are empty (in which case an estimated value cannot
            be determined).
        """
        portfolio_value = 0
        ccys = list(self.positions.keys())
        for ccy in ccys:
            if ccy == 'USD': portfolio_value += self.positions[ccy]
            elif self.positions[ccy] != 0: # for other non-zero non-usd position
                curr_orderbook = orderBooks[('USD', ccy)]
                curr_fx = TradingBot.getConversionRateToUSD(curr_orderbook)
                if curr_fx == None: return None
                portfolio_value += self.positions[ccy] / curr_fx 
        
        return portfolio_value
    
    def getPositions(self):
        """Returns dictionary of positions rounded to 3 decimal places
    
        Returns:
            A dictionary mapping currencies to quantities held, where each
            quantity is rounded to 3 decimal places.
        """
        roundedPositions = dict()
        for currency, position in self.positions.items():
            roundedPositions[currency] = round(position, 3)
        return roundedPositions
                
    @staticmethod
    def getConversionRateToUSD(orderBook):
        """Gets an estimated conversion rate to USD based on a specific order book.
        
        The bid/ask spread is the difference between prices of the best
        unfulfilled bid (buy) offer and the best unfulfilled ask (sell) offer.
        Taking the mean of these order prices gives a good estimate of what the
        currency is actually worth (ie the fair value). This is how we estimate
        the values of each currency to calculate the USD value.

        Args:
            orderBook: The order book to generate the conversion rate for. 
                The base is guaranteed to be USD.

        Returns:
            The average of the best bid and ask prices, or None if the order book is empty. 
        """
        if orderBook.bids.size() > 0 and orderBook.asks.size() > 0:
            ask = orderBook.asks.peek().price
            bid = orderBook.bids.peek().price
            return (ask + bid) / 2
        elif orderBook.bids.size() > 0: return orderBook.bids.peek().price
        elif orderBook.asks.size() > 0: return orderBook.asks.peek().price
        return None
    
    

################################################################################
# HardcodedBot
################################################################################

class HardcodedBot(TradingBot):
    """A hardcoded trading bot for testing purposes. Has a set list of orders to place at each round."""
    # orders_rounds: list of lists, each list is the order(s) to place each round
    def __init__(self,orders_rounds):
        super().__init__()
        self.orders_rounds = orders_rounds
        
    def placeOrders(self, orderBooks, tradingRound):
        self.handleFilledOrders()
        return self.orders_rounds[tradingRound]

################################################################################
# ArbitrageBot
################################################################################

class ArbitrageBot(TradingBot):
    """A trading bot that detects arbitrages by finding negative weight cycles in the exchange graph."""
    
    def placeOrders(self, orderBooks, tradingRound):
        self.handleFilledOrders()
        graph = ArbitrageBot.generateGraph(orderBooks, tradingRound)
        negCycle = ArbitrageBot.getNegCycle(graph)
        #print("negcycle", negCycle)
        #print(ArbitrageBot.getOrdersFromCycle(negCycle, orderBooks, tradingRound))
        
        return ArbitrageBot.getOrdersFromCycle(negCycle, orderBooks, tradingRound)
    
    @staticmethod
    def getNegCycle(graph):
        unvisitedNodes = set(graph.keys())
        while unvisitedNodes != set():
            startNode = unvisitedNodes.pop()
            cycle, disrances = ArbitrageBot.getNegCycleFromSource(graph, startNode)
            if cycle != None:
                return cycle
            unvisitedNodes = {node for node, d in distances.items() if d == math.inf}
        return None
    
    @staticmethod
    def getNegCycleFromSource(graph, source):
        n = len(graph)
        distances = {node: math.inf for node in graph}
        distances[source] = 0
        for _ in range(n-1):
            ArbitrageBot.relaxEdges(graph, distances)
        
        changedNodes = ArbitrageBot.relaxEdges(graph, distances)
        if changedNodes == []:
            return None, distances
        
        for changedNode in changedNodes:
            cycle = ArbitrageBot.findCycle(graph, distances, [changedNode])
            if cycle != None:
                return cycle, distances
    
    @staticmethod
    def relaxEdges(graph, distances):
        changed = []
        for u, neighbors in graph.items():
            for v, weight in neighbors.items():
                if distances[u] + weight < distances[v]:
                    distances[v] = distances[u] + weight
                    changed.append(v)
        return changed
    
    @staticmethod
    def findCycle(graph, distances, currPath):
        if (currPath[0] == currPath[-1]) and (len(currPath) > 1):
            return currPath
        lastNode = currPath[-1]
        for neighbor, weight in graph[lastNode].items():
            oldDist = distances[neighbor]
            newDist = distances[lastNode] + weight
            if newDist < oldDist:
                distances[neighbor] = newDist
                currPath.append(neighbor)
                potentialCycle = ArbitrageBot.findCycle(graph, distances, currPath)
                if potentialCycle != None:
                    return potentialCycle
                distances[neighbor] = oldDist
                currPath.pop()
        return None
    
    @staticmethod
    def generateGraph(orderBooks, tradingRound):
        # get the top of book orders and use the log(price) as path weights
        graph = dict()
        for base, quote in orderBooks:
            
            curr_orderbook = orderBooks[(base, quote)]
            
            if curr_orderbook.bids.size() > 0:
                curr_order = curr_orderbook.bids.peek()
                if curr_order.time < tradingRound: 
                    graph[quote] = graph.get(quote,dict())
                    graph[quote][base] = math.log(1 / curr_order.price)
                
            if curr_orderbook.asks.size() > 0:
                curr_order = curr_orderbook.asks.peek()
                if curr_order.time < tradingRound:
                    graph[base] = graph.get(base,dict())
                    graph[base][quote] = math.log(curr_order.price)
        return graph
            
        
    @staticmethod
    def getOrdersFromCycle(negCycle, orderBooks, tradingRound):
        """Gets a list of orders to place to take advantage of the arbitrage formed by negCycle

        Args:
            negCycle: A list representing a cycle of currencies that create an 
                arbitrage. The first and last elements of the list are the same. 
                The list is ordered based on orders in the market, so orders 
                placed will go in the reverse order.
            orderBooks: A dictionary mapping currency pairs to order books for
                the orders currently in the exchange
            tradingRound: An integer representing the current trading round.

        Returns:
            A list of orders to place that make money by taking advantage of the
            arbitrage in negCycle.
        """
        
        # step 1: find quantity to trade
        if negCycle == None: return []
        for i in range(0, len(negCycle) - 1):
            base = negCycle[i]
            quote = negCycle[i + 1]
            pair_in_orderbook = (base, quote) in orderBooks
            
            curr_orderbook = orderBooks[(base, quote)] if pair_in_orderbook else orderBooks[(quote, base)]
            curr_order = curr_orderbook.asks.peek() if pair_in_orderbook else curr_orderbook.bids.peek()
            order_size = curr_order.quantity
            pair_px = curr_order.price if pair_in_orderbook else 1/curr_order.price
            
            if i == 0:
                next_quantity = order_size * pair_px if pair_in_orderbook else order_size
            else:
                next_quantity = min(next_quantity * pair_px, order_size)
        # found quantity to be the starting quantity to place orders in reverse
        #print(next_quantity)
        
        # step 2: generate orders to place
        res = []
        for i in range(len(negCycle) - 1, 0, -1):
            
            base = negCycle[i]
            quote = negCycle[i - 1]
            pair_in_orderbook = (base, quote) in orderBooks
            
            curr_orderbook = orderBooks[(base, quote)] if pair_in_orderbook else orderBooks[(quote, base)]
            curr_order = curr_orderbook.bids.peek() if pair_in_orderbook else curr_orderbook.asks.peek()
            
            if pair_in_orderbook:
                res.append(Order(base, quote, direction = SELL, price = curr_order.price, quantity = next_quantity, time = tradingRound))
                next_quantity = next_quantity * curr_order.price
                #print(base, quote, next_quantity)
            else:
                res.append(Order(quote, base, direction = BUY, price = curr_order.price, quantity = next_quantity * 1 / curr_order.price, time = tradingRound))
                next_quantity = next_quantity * 1 / curr_order.price
                #print(base, quote, next_quantity)
        
        return res


################################################################################
# Testing
################################################################################

@testFunction
def testOrderBooks():
    
    # Test 1: test an orderbook with just one buy bid
    book1 = OrderBook()
    buy1 = Order("EUR", "USD", BUY, price = 100, quantity = 5, time = 1)
    book1.processOrder(buy1)
    assert(not book1.bids.isEmpty())
    assert(book1.asks.isEmpty())
    assert(book1.bids.peek() == buy1)
    assert(buy1.fills == [])

    # Test 2: test an orderbook with just one sell bid
    book2 = OrderBook()
    sell2 = Order("USD", "EUR", SELL, price = 120, quantity = 3, time = 2)
    book2.processOrder(sell2)
    assert(not book2.asks.isEmpty())
    assert(book2.bids.isEmpty())
    assert(book2.asks.peek() == sell2)
    assert(sell2.fills == [])

    # Test 3: check that you fulfill an order if you can
    buy2 = Order("USD", "EUR", BUY, price = 120, quantity = 3, time = 2)
    book2.processOrder(buy2)
    # there should be no additional orders remaining in the book
    # as all of them are fulfilled
    assert(book2.bids.isEmpty() and book2.asks.isEmpty())
    assert(buy2.quantity == 0 and sell2.quantity == 0)

    # Test 4: fill as much of an order as you can (adding a buy second)
    book4 = OrderBook()
    sell4 = Order("USD", "EUR", SELL, price = 90, quantity = 3, time = 1)
    book4.processOrder(sell4)
    buy4 = Order("USD", "EUR", BUY, price = 100, quantity = 5, time = 2)
    book4.processOrder(buy4)
    assert(buy4.quantity == 2)   # still wants 2 more
    assert(sell4.quantity == 0)  # completely filled
    assert(buy4.fills == [(3, 90)])
    assert(book4.bids.peek() == buy4)
    assert(book4.asks.isEmpty())

    # Test 5: fill as much of an order as you can (adding a sell second)
    book5 = OrderBook()
    buy5 = Order("USD", "EUR", BUY, price = 95, quantity = 4, time = 1)
    book5.processOrder(buy5)
    sell5 = Order("USD", "EUR", SELL, price = 90, quantity = 6, time = 2)
    book5.processOrder(sell5)
    assert(sell5.quantity == 2)   # 2 left unfilled
    assert(buy5.quantity == 0)    # completely filled

    assert(buy5.fills == [(4, 95)])
    assert(book5.asks.peek() == sell5)

    # Test 6: the best price should win!
    book6 = OrderBook()
    buy6a = Order("USD", "EUR", BUY, price = 100, quantity = 1, time = 1)
    buy6b = Order("USD", "EUR", BUY, price = 110, quantity = 1, time = 2)
    book6.processOrder(buy6a)
    book6.processOrder(buy6b)
    sell6 = Order("USD", "EUR", SELL, price = 100, quantity = 1, time = 3)
    book6.processOrder(sell6)
    # the 110 bid should match first because it's higher and more advantageous
    assert(buy6b.quantity == 0)
    assert(sell6.quantity == 0)
    assert(buy6b.fills == [(1, 110)])
    assert(buy6a.quantity == 1)  # still waiting
    assert(book6.bids.peek() == buy6a)

    # Test 7: the earlier order at same price wins
    book7 = OrderBook()
    buy7a = Order("USD", "EUR", BUY, price = 100, quantity = 1, time = 1)
    buy7b = Order("USD", "EUR", BUY, price = 100, quantity = 1, time = 2)
    book7.processOrder(buy7a)
    book7.processOrder(buy7b)
    sell7 = Order("USD", "EUR", SELL, price = 100, quantity = 1, time = 3)
    book7.processOrder(sell7)
    assert(buy7a.quantity == 0)
    assert(buy7b.quantity == 1)  # still waiting
    assert(sell7.quantity == 0)
    assert(buy7a.fills == [(1, 100)])

    # Test 8: you can fill an order with multiple other orders
    book8 = OrderBook()
    book8.processOrder(Order("USD", "EUR", SELL, price = 90, quantity = 2, time = 1))
    book8.processOrder(Order("USD", "EUR", SELL, price = 95, quantity = 3, time = 2))
    buy8 = Order("USD", "EUR", BUY, price = 100, quantity = 5, time = 3)
    book8.processOrder(buy8)
    assert(buy8.quantity == 0)
    assert(buy8.fills == [(2, 90), (3, 95)])
    assert(book8.asks.isEmpty())
#-----------------------------------------------------------------------------------------------------------
def testExchangeAndBots():
    # CASE 1: a single buy order
    exchange = Exchange()
    buyOrder = Order(base = "USD", quote = "EUR", direction = BUY,
                      price = 0.85, quantity = 10, time = 0)
    # at time 0, place this order
    bot = HardcodedBot([[buyOrder]])
    exchange.addTrader(bot)
    exchange.performTradingRound()

    # the buy order should be added to the order book
    orderBook = exchange.orderBooks[("USD", "EUR")]
    assert((orderBook.bids.size()) == 1) 
    assert(orderBook.bids.peek() == buyOrder)

    # CASE 2: a matching buy and sell order
    exchange = Exchange()
    buyOrder = Order(base = "USD", quote = "EUR", direction = BUY,
                      price = 0.85, quantity = 5, time = 0)
    sellOrder = Order(base = "USD", quote = "EUR", direction = SELL,
                      price = 0.85, quantity = 5, time = 0)
    
    botA = HardcodedBot([[buyOrder]])
    botB = HardcodedBot([[sellOrder]])
    exchange.addTrader(botA)
    exchange.addTrader(botB)
    exchange.performTradingRound()  # execute trades first

    # the orders should be completely filled with nothing left over
    assert(buyOrder.quantity == 0)
    assert(sellOrder.quantity == 0)


    # CASE 3: a partially filled buy order
    exchange = Exchange()
    buyOrder = Order(base = "USD", quote = "EUR", direction = BUY,
                      price = 0.85, quantity = 10, time = 0)
    sellOrder1 = Order(base = "USD", quote = "EUR", direction = SELL,
                      price = 0.85, quantity = 5, time = 0)
    sellOrder2 = Order(base = "USD", quote = "EUR", direction = SELL,
                      price = 0.85, quantity = 5, time = 1)

    botA = HardcodedBot([[buyOrder], []])
    botB = HardcodedBot([[sellOrder1], [sellOrder2]])
    exchange.addTrader(botA)
    exchange.addTrader(botB)
    exchange.performTradingRound()
    
    assert(buyOrder.quantity == 5)  # still partially unfilled
    assert(sellOrder1.quantity == 0)
    assert(botA.positions == {'USD': 5, 'EUR': -4.25, 'JPY': 0, 'GBP': 0, 'AUD': 0})
    assert(botB.positions == {'USD': -5, 'EUR': 4.25, 'JPY': 0, 'GBP': 0, 'AUD': 0})
   
    # CASE 4 - if I can complete an existing order, I should!
    exchange.performTradingRound()
    assert(buyOrder.quantity == 0)
    assert(sellOrder2.quantity == 0)
    
    
    # CASE 5: price mismatch means no fills!
    exchange = Exchange()
    buyOrder = Order(base = "USD", quote = "EUR", direction = BUY,
                     price = 0.85, quantity = 5, time = 0)
    sellOrder = Order(base = "USD", quote = "EUR", direction = SELL,
                     price = 3, quantity = 5, time = 0)
    botA = HardcodedBot([[buyOrder]])
    botB = HardcodedBot([[sellOrder]])
    exchange.addTrader(botA)
    exchange.addTrader(botB)
    exchange.performTradingRound()
    
    # both orders should still be sitting in the book because nothing matches
    orderBook = exchange.orderBooks[("USD", "EUR")]
    assert(orderBook.bids.size() == 1)
    assert(orderBook.asks.size() == 1)
    assert(buyOrder.quantity == 5)
    assert(sellOrder.quantity == 5)
    assert(buyOrder.fills == [])
    assert(sellOrder.fills == [])
    
    # CASE 6: you should prioritize the better price first
    exchange = Exchange()
    sell1 = Order(base = "USD", quote = "EUR", direction = SELL,
                  price = 0.85, quantity = 5, time = 0)
    sell2 = Order(base = "USD", quote = "EUR", direction = SELL,
                  price = 0.75, quantity = 5, time = 0)
    buy = Order(base = "USD", quote = "EUR", direction = BUY,
                  price = 0.85, quantity = 5, time = 1)
    botA = HardcodedBot([[sell1, sell2], [buy]])
    exchange.addTrader(botA)
    exchange.performTradingRound()
    exchange.performTradingRound()
    
    # buy should match with cheaper sell2 first
    assert(sell2.quantity == 0)
    assert(buy.quantity == 0)
    assert(sell1.quantity == 5)
    
    # CASE 7: FIFO at same price
    exchange = Exchange()
    sell1 = Order(base = "USD", quote = "EUR", direction = SELL,
                  price = 0.85, quantity = 5, time = 0)
    sell2 = Order(base = "USD", quote = "EUR", direction = SELL,
                  price = 0.85, quantity = 5, time = 1)
    buy = Order(base = "USD", quote = "EUR", direction = BUY,
                  price = 0.85, quantity = 7, time = 1)
    botA = HardcodedBot([[sell1], [sell2, buy]])
    exchange.addTrader(botA)
    exchange.performTradingRound()
    exchange.performTradingRound()
    assert(sell1.quantity == 0)   # filled first
    assert(sell2.quantity == 3)   # and partially filled
    assert(buy.quantity == 0)
    
    # CASE 8: multiple different exchange currencies
    exchange = Exchange()
    sell = Order(base = "USD", quote = "EUR", direction = SELL,
                  price = 0.85, quantity = 5, time = 0)
    buy = Order(base = "USD", quote = "JPY", direction = BUY,
                  price = 0.85, quantity = 7, time = 1)
    botA = HardcodedBot([[sell], [buy]])
    exchange.addTrader(botA)
    exchange.performTradingRound()
    exchange.performTradingRound()
    assert(sell.quantity == 5)   # shouldn't fulfill the orders
    assert(buy.quantity == 7)
    assert(buy.fills == [])
    assert(sell.fills == [])
    
    ### TESTING calculateUSDValue
    
    # CASE A: bot with zero positions, value should be 0
    exchange = Exchange()
    bot = HardcodedBot([[]])
    exchange.addTrader(bot)
    assert(bot.calculateUSDValue(exchange.orderBooks) == 0)

    # CASE B: bot with filled USD position directly
    bot.positions['USD'] = 100
    assert(bot.calculateUSDValue(exchange.orderBooks) == 100)
    bot.positions['USD'] = 0

    # CASE C: bot with non-USD currency but order book is empty, so return None
    bot.positions['EUR'] = 50
    # USD/EUR order book empty (no bids or asks)
    assert(bot.calculateUSDValue(exchange.orderBooks) == None)

    # CASE D: add a reference order to USD/EUR to allow conversion
    orderBook = exchange.orderBooks[('USD', 'EUR')]
    sellOrder = Order(base = 'USD', quote = 'EUR', direction = SELL,
                      price = 0.8, quantity = 10, time = 0)
    bot = HardcodedBot([[sellOrder]])
    bot.positions['EUR'] = 50
    bot.positions['USD'] = 100
    exchange.addTrader(bot)
    exchange.performTradingRound()
    value = bot.calculateUSDValue(exchange.orderBooks)
    assert(value == 50/0.8 + 100)  # 50 Euros / 0.65. + 100 USD

#-----------------------------------------------------------------------------------------------------------
def testGetOrdersFromCycle():
    # First, we test that the positions are correct when manually passing in a
    # negative weight cycle. This means you do NOT have to implement the code to
    # find a negative weight cycle at first.

    order1 = Order(base='USD', quote='EUR', direction=BUY, price=0.88, quantity=10, time=0)
    order2 = Order(base='USD', quote='GBP', direction=SELL, price=0.74, quantity=8, time=0) 
    order3 = Order(base='EUR', quote='GBP', direction=BUY, price=0.9, quantity=5, time=0)

    person1 = HardcodedBot([[order1, order2, order3], []])
    exchange = Exchange()
    exchange.addTrader(person1)
    exchange.performTradingRound() # person1 will place all the orders that lead to arbitrage
    
    # Verify that ArbitrageBot.getOrdersFromCycle places the correct orders given specific negative weight cycles
    exchange1 = copy.deepcopy(exchange)
    cycle = ['USD', 'GBP', 'EUR', 'USD']
    ordersToPlace = {
        Order(base='USD', quote='EUR', direction=SELL, price=0.88, quantity=5.68, time=1),
        Order(base='EUR', quote='GBP', direction=SELL, price=0.90, quantity=5.00, time=1),
        Order(base='USD', quote='GBP',  direction=BUY, price=0.74, quantity=6.08, time=1),
    }
    ordersPlaced = set(ArbitrageBot.getOrdersFromCycle(cycle, exchange1.orderBooks, 1))
    assert(ordersPlaced == ordersToPlace)
    
    exchange2 = copy.deepcopy(exchange)
    cycle = ['GBP', 'EUR', 'USD', 'GBP']
    ordersToPlace = {
        Order(base='USD', quote='GBP',  direction=BUY, price=0.74, quantity=5.68, time=1),
        Order(base='USD', quote='EUR', direction=SELL, price=0.88, quantity=5.68, time=1),
        Order(base='EUR', quote='GBP', direction=SELL, price=0.90, quantity=5.00, time=1),
    }
    ordersPlaced = set(ArbitrageBot.getOrdersFromCycle(cycle, exchange2.orderBooks, 1))
    assert(ordersPlaced == ordersToPlace)

    exchange3 = copy.deepcopy(exchange)
    cycle = ['EUR', 'USD', 'GBP', 'EUR']
    ordersToPlace = {
        Order(base='EUR', quote='GBP', direction=SELL, price=0.90, quantity=5.00, time=1),
        Order(base='USD', quote='GBP',  direction=BUY, price=0.74, quantity=6.08, time=1),
        Order(base='USD', quote='EUR', direction=SELL, price=0.88, quantity=6.08, time=1),
    }
    ordersPlaced = set(ArbitrageBot.getOrdersFromCycle(cycle, exchange3.orderBooks, 1))
    assert(ordersPlaced == ordersToPlace)

@testFunction
def arbitrageBotTest1():
    order1 = Order(base='USD', quote='EUR', direction=BUY, price=0.88, quantity=10, time=0)
    order2 = Order(base='USD', quote='GBP', direction=SELL, price=0.74, quantity=8, time=0) 
    order3 = Order(base='EUR', quote='GBP', direction=BUY, price=0.9, quantity=5, time=0)

    person1 = HardcodedBot([[order1, order2, order3], []])
    person2 = ArbitrageBot()
    exchange = Exchange()
    exchange.addTrader(person1)
    exchange.addTrader(person2)
    exchange.performTradingRound() # person1 will place all the orders that lead to arbitrage
    exchange.performTradingRound() # person2 will find the arbitrage
    

    # There are multiple possible answers depending on the negative cycle found
    pos1 = {'USD': 0.399, 'EUR': 0, 'JPY': 0, 'GBP': 0, 'AUD': 0}   # Cycle: ['USD', 'GBP', 'EUR', 'USD']
    pos2 = {'USD': 0, 'EUR': 0, 'JPY': 0, 'GBP': 0.295, 'AUD': 0}   # Cycle: ['GBP', 'EUR', 'USD', 'GBP']
    pos3 = {'USD': 0, 'EUR': 0.351, 'JPY': 0, 'GBP': 0, 'AUD': 0}   # Cycle: ['EUR', 'USD', 'GBP', 'EUR']
    person2Position = person2.getPositions()
    assert(positionIsValid(person2Position, [pos1, pos2, pos3]))

    # Person 1's position should be the negation of person 2's position
    person1Position = person1.getPositions()
    for currency, val in person2Position.items():
        assert(almostEqual(val, -person1Position[currency]))

# This class is just for implementing the __eq__ method so it's easier
# to test if two positions are equal while ignoring rounding errors.
class Position:
    def __init__(self, position):
        self.position = position

    def __repr__(self):
        return str(self.position)
    
    def __eq__(self, other):
        if (not isinstance(other, Position)) or (self.position.keys() != other.position.keys()):
            return False
        for key, val in self.position.items():
            if not almostEqual(val, other.position[key]):
                return False
        return True

# This function is just used for testing.
def positionIsValid(position, validAnswers):
    validPositions = [Position(d) for d in validAnswers]
    return Position(position) in validPositions

def main():
    # part 1
    testOrderBooks()
    # part 2
    testExchangeAndBots()
    # part 3
    testGetOrdersFromCycle()
    arbitrageBotTest1()

main()
