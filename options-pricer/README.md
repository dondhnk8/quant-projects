# Options Pricer

A Black-Scholes options pricer with a live tkinter GUI. Pulls real option chains from Yahoo Finance, compares the model price against the current market price, and displays the full set of Greeks for the selected contract.

## Features

- **Live data**: fetches the current stock price, option chains, and expiration dates for any valid ticker via `yfinance`.
- **Call/Put selection**: toggle between calls and puts, with expiration dates and the contracts table updating accordingly.
- **Sortable contracts table**: strike, last price, bid, ask, volume, and implied volatility for every contract in the selected expiration, sortable by column.
- **Black-Scholes pricing**: computes the model price for the selected contract using the current risk-free rate (13-week Treasury yield, `^IRX`) and either implied volatility or, when implied volatility is unreliable (below 5%), a 6-month historical volatility fallback.
- **Full Greeks**: Delta, Gamma, Vega, Theta, and Rho, computed alongside price and returned together as a single `BSResult` object.
- **Market comparison**: shows the model price, the bid-ask midpoint as the market price estimate, and the dollar/percent difference between them, color-coded by whether the model considers the contract under- or overpriced.
- **5-day sparkline**: a small chart of recent price action next to the current stock price.
- **Dark trading-terminal theme**: custom `ttk` styling across all widgets.

## How it works

1. Enter a ticker and select Call or Put.
2. Choose an expiration date; the contracts table populates automatically.
3. Select a contract row, then click **Calculate Model Price**.
4. The app computes:
   - `d1` and `d2` from the Black-Scholes formula
   - Model price (Call or Put, depending on selection)
   - Delta, Gamma, Vega, Theta, Rho
5. Results are displayed in the results panel: price/market/difference on the left, Greeks (Δ, Γ, V, Θ, ρ) right-aligned.

## Requirements

- Python 3.11+
- `numpy`
- `scipy`
- `yfinance`
- `tkinter` (on macOS, the system Python's bundled Tk can be too old to render widgets correctly — install via `brew install python-tk@3.11` if the GUI fails to display)

## Notes

- Theta is displayed as decay per day (raw formula output, which is per year, divided by 365).
- Vega and Rho are dollar-denominated (price sensitivity per 1% change in volatility or interest rates); Delta and Gamma are shown as plain ratios.
- Model vs. market difference is not itself a trading signal; it reflects deviation from the Black-Scholes assumptions, not mispricing in a strict sense.

## Roadmap

- Link the model-vs-market price difference to a probability-of-profit estimate for a given contract, potentially using Delta as an ITM-probability proxy.
- Weight/discount that estimate by contract liquidity (volume, bid-ask spread).