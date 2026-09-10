import numpy as np
import scipy as sc
import yfinance as yf
from datetime import datetime

# ask user for a ticker
ticker = yf.Ticker(input("Enter the ticker symbol (Like AAPL): ").upper())

# show available expiratoin dates and let user pick one
expiration_dates = ticker.options
print(f"Available expiration dates: {expiration_dates}")

# outer loop: keep asking for an expiration date until we find a valid one with liquid options
while True:
    # inner loop: validate  the expiration date itself against the available list
    while True:
        exp_date = input("Choose one of the expiration dates (YYYY-MM-DD): ")
        if exp_date in expiration_dates:
            options_chain = ticker.option_chain(exp_date)
            opt_calls = options_chain.calls
            opt_puts = options_chain.puts
            break
        else:
            print("Invalid expiration date. Please choose from the available options.")

    # ask for call or put now that we have a valid expiration date
    while True:
        option_type = input("Call or Put? ").capitalize()
        if option_type in ("Call","Put"):
            break
        else:
            print("Invalid option type. Please choose 'Call' or 'Put'.")

    if option_type == "Call":
        chosen_df = opt_calls
        print(f"Available Calls for {ticker.ticker} on {exp_date}: \n{opt_calls.head()}")
    else:
        chosen_df = opt_puts
        print(f"Available Puts for {ticker.ticker} on {exp_date}: \n{opt_puts.head()}")

    # current stock price
    S = ticker.info["currentPrice"]

    # filter to liquid contracts only (volume > 0), then find a strike closest to current price
    # .copy() is used to avoid SettingWithCopyWarning
    liquid_options = chosen_df[chosen_df["volume"] > 0].copy()

    if liquid_options.empty:
        print("No liquid options available for this expiration date. Please choose another date.")
        continue # go back to the outer loop to ask for a new expiration date

    liquid_options["strike_diff"] = abs(liquid_options["strike"] - S)
    sorted_options = liquid_options.sort_values("strike_diff")
    print(sorted_options[["strike", "volume", "lastPrice", "bid", "ask", "impliedVolatility"]])
    break # found a valid expiration date with liquid options, exit the outer loop


def black_scholes_price(S, K, T, r, sigma, option_type):
    d1 = (np.log(S/K) + (r + (sigma**2)/2) * T) / (sigma * (T**0.5))
    d2 = d1 - sigma * (T**0.5)

    if option_type == "Call":
        price = S * sc.stats.norm.cdf(d1) - K * np.exp(-r * T) * sc.stats.norm.cdf(d2)
    elif option_type == "Put":
        price = K*np.exp(-r*T)*sc.stats.norm.cdf(-d2) - S*sc.stats.norm.cdf(-d1)
    else:
        return "Option Value Error"

    return price

closest_row = sorted_options.iloc[0]
strike = closest_row["strike"]
market_price = closest_row["lastPrice"]

# Calculating implied volatility (I tried to use the yfinance option but the implied volatility data is not reliable)
hist = yf.download(ticker.ticker, period="6mo", interval="1d")
closes = hist["Close"].values.flatten()

# calculate daily returns, then annualized standard deviation (252 = average trading days per year)
daily_returns = np.diff(closes) / closes[:-1]
historical_vol = np.std(daily_returns) * np.sqrt(252)

print(f"Selected strike (closest to current stock price ${S}): ${strike}")
print(f"Historical Volatility (annualized): {historical_vol:.4f}")

# time to expiration in years
today = datetime.now()  
expiration = datetime.strptime(exp_date, "%Y-%m-%d")
# .days just counts the number of days
T = (expiration - today).days / 365

# risk-free rate approximation (could be refined with a real current rate lookup)
r = 0.05

model_price = black_scholes_price(S, strike, T, r, historical_vol, option_type)
percentage_diff = ((market_price - model_price) / market_price) * 100

print(f"\nMarket Price: ${market_price}")
print(f"Model Price (Black-Scholes): ${model_price:.2f}")
print(f"Difference: ${market_price - model_price:.2f}")
print(f"Percentage Difference: {percentage_diff:.2f}%")