# Algorithmic Trading Engine: Multi-Asset Exchange Simulator with Arbitrage Bots

## Project Overview
This project models a simplified currency exchange where multiple bots submit buy and sell orders across different currency pairs. The long-term goal is to simulate an exchange environment in which bots apply different trading strategies, including arbitrage detection and execution.

The system is built incrementally, starting from the core market mechanics and extending to bot-driven trading and arbitrage logic.

---

## Core Components

### `Order`
The `Order` class represents a single instruction to buy or sell a currency pair.

Each order contains:
- **base currency** and **quote currency**
- **direction**: `BUY` or `SELL`
- **price**: amount of quote currency per 1 unit of base currency
- **quantity**: units of base currency to trade
- **time**: integer timestamp indicating when the order was placed

The class also supports equality and hashing for testing and comparison.

---

### `OrderBook`
The `OrderBook` class manages outstanding orders for a single currency pair.

Its responsibilities include:
- storing current buy and sell orders
- matching incoming orders efficiently
- supporting **FIFO matching**
- handling **partial fills**

Matching rules:
- incoming **buy** orders match against the **lowest-priced sell** orders first
- incoming **sell** orders match against the **highest-priced buy** orders first

This design makes priority-queue-based order storage a natural fit.

---

### `Exchange`
The `Exchange` class represents the simulated currency exchange itself.

It coordinates:
- multiple order books
- order submission and execution
- interaction between trading bots and the market

---

## Trading Bots

### `TradingBot`
`TradingBot` is the base class for all bot strategies.

It provides shared functionality for:
- updating positions after filled orders
- tracking inventory
- computing portfolio value in USD
- converting currencies to USD through a shared utility method

The base `placeOrders()` method returns an empty list and is intended to be overridden by subclasses implementing specific strategies.

#### `getPositions()`
For easier debugging and testing, `TradingBot` includes a helper method that returns positions rounded to three decimal places.

---

### `HardcodedBot`
`HardcodedBot` is a simple testing bot that submits predefined orders.

It takes a 2D list of orders and, at trading round `i`, places the orders stored at index `i`. This bot is mainly used for validation and controlled test scenarios.

---

### `ArbitrageBot`
`ArbitrageBot` detects and executes arbitrage opportunities across multiple currency pairs.

Its implementation includes:
- constructing a graph of exchange rates
- transforming prices using log weights
- detecting arbitrage via **Bellman-Ford negative-cycle detection**
- generating executable orders from detected cycles
- submitting trades to capture mispricing opportunities

A key helper method is:

#### `getOrdersFromCycle(negCycle, orderBooks, tradingRound)`
This static method converts a detected negative cycle into a set of executable orders. It can be tested independently before integrating the full arbitrage strategy.

---

## Global Constants
The project uses two global constants:

- `BUY`
- `SELL`

These are intentionally defined as globals because:
- they are **constant throughout the program**
- they are used across many functions and classes
- they reduce bugs compared with repeatedly using raw strings like `"Buy"` and `"Sell"`

Using named constants also improves readability and helps catch spelling errors early through runtime exceptions.

---

## Documentation Style
The codebase uses **docstrings** to document classes and methods.

Docstrings describe:
- the purpose of each method
- expected inputs
- return values
- intended behavior

Most implementation details are specified through docstrings and test cases rather than extensive external writeups.

---

## Testing Notes
The project relies heavily on unit tests to validate matching logic, order generation, and bot behavior.

Notable testing-related additions include:

### `Order.__eq__` and `Order.__hash__`
These methods allow order objects to be compared reliably in the test suite.

### Regression coverage
Later project stages are expected to preserve functionality implemented earlier, so earlier tests remain relevant even when omitted from starter files for readability.

---

## Features Implemented
- Multi-currency limit order book exchange simulator
- FIFO matching and partial fill support
- Priority-queue bid/ask handling
- Portfolio and P&L tracking
- USD valuation across currency holdings
- Hardcoded test bot for deterministic scenarios
- Arbitrage bot using Bellman-Ford negative-cycle detection

---

## Learning Goals
This project demonstrates practical applications of:
- market microstructure fundamentals
- order book mechanics
- graph algorithms in finance
- arbitrage detection
- object-oriented system design
- testing and debugging of trading systems

---

## Notes
- The arbitrage strategy depends on correct negative-cycle recovery in Bellman-Ford.
- An earlier lecture version of Bellman-Ford had a bug for disconnected graphs; the corrected version from the course materials should be used.

---
