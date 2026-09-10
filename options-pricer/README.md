# Options Pricer (Black-Scholes)

A command-line tool that prices options using the Black-Scholes model and compares the result against real market prices pulled from Yahoo Finance.

## What it does

1. Takes a stock ticker, expiration date, and option type (call or put) from the user
2. Pulls the live options chain for that expiration using `yfinance`
3. Filters for liquid contracts (nonzero trading volume) and selects the strike closest to the current stock price (at-the-money)
4. Calculates historical volatility from 6 months of daily closing prices
5. Prices the selected option using the Black-Scholes formula
6. Compares the model price against the actual market price and reports the difference

## Why historical volatility instead of implied volatility

Black-Scholes requires a volatility input (sigma). The natural choice would be the market's own implied volatility, which Yahoo Finance provides in its options data. In practice, this field was unreliable during development: it frequently returned near-zero placeholder values (0.00001) regardless of the actual option, a known issue with Yahoo's data feed rather than a bug in this script.

To work around this, the model calculates its own historical volatility from the stock's trailing 6-month daily returns, annualized using the standard `sqrt(252)` convention. This has a real tradeoff: historical volatility is backward-looking, while the market's pricing reflects forward-looking expectations. The comparison this script produces is therefore not "is my formula right" in isolation, but "how well does trailing historical volatility approximate the market's actual pricing."

## Why liquidity filtering matters

Options with zero trading volume often have stale `lastPrice` values, sometimes from trades days old, that don't reflect current fair value. Comparing a model price against a stale market price produces a meaningless gap that looks like model error but isn't. The script filters to contracts with nonzero volume before selecting a strike, and prompts for a different expiration date if none are found.

This distinction showed up clearly during testing. On Take-Two Interactive (TTWO), an underlying name with a thin options market, model-to-market gaps of 30%+ persisted even after filtering, and every available contract showed a zero bid and zero ask, indicating no active market maker quote at all. On Apple (AAPL), a heavily-traded name, the same approach produced a gap of roughly 1-3% depending on the expiration chosen. The difference is not a flaw in the model; it reflects how much weight a "market price" comparison can actually bear given the underlying liquidity.

## Results

Example run, AAPL, near-term liquid call option:

- Market price: $9.95
- Model price (Black-Scholes, historical volatility): $10.30
- Difference: -3.51%

Example run, AAPL, November expiration:

- Difference: 1.19%

## Known limitations

- Black-Scholes assumes European-style exercise (exercisable only at expiration). US equity options are American-style (exercisable anytime), which can cause small pricing discrepancies, particularly for puts and dividend-paying stocks.
- The risk-free rate is currently a fixed approximation (5%) rather than pulled from a live source.
- Historical volatility is calculated over a fixed 6-month window regardless of the option's time to expiration; a closer match between the volatility lookback period and the option's remaining life would likely improve accuracy.
- Volatility skew (the tendency for implied volatility to vary by strike, rather than stay constant as Black-Scholes assumes) is visible in the data but not modeled here.

## Requirements

```
pip install numpy scipy yfinance
```

## Usage

```
python options_pricer.py
```

Follow the prompts: enter a ticker, choose an expiration date from the printed list, choose call or put. The script validates each input and will re-prompt on invalid entries or expirations with no liquid contracts.

## Next steps

A GUI version of this tool, built with tkinter, is in progress to replace the terminal-based input/output with an interactive window.
