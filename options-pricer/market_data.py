import yfinance as yf
import numpy as np
from datetime import datetime

def get_risk_free_rate():
    """
    Fetches the current 13-week Treasury bill yield (^IRX) as a proxy
    for the risk-free rate used in Black-Scholes. yfinance returns this
    as a percentage (e.g. 5.3 meaning 5.3%), so we divide by 100 to get
    the decimal form the formula expects (0.053). If the fetch fails for
    any reason, fall back to a reasonable constant instead of crashing.
    """
    irx = yf.Ticker("^IRX")
    rate = irx.info.get("regularMarketPrice", None)
    return rate / 100 if rate is not None else 0.05

def get_time_to_expiration(expiration_date_str):
    """
    Converts an expiration date string (e.g. "2026-09-25") into the
    number of years remaining until that date — the "T" input Black-Scholes
    expects. strptime parses the string into a real datetime using the
    format that matches how yfinance formats its dates. Subtracting two
    datetimes gives a timedelta, and .days pulls the whole number of days
    out of it. Dividing by 365 converts days into fractional years.
    """
    expiration_date = datetime.strptime(expiration_date_str, "%Y-%m-%d")
    days_remaining = (expiration_date - datetime.now()).days
    return days_remaining / 365

def get_historical_volatility(ticker_symbol):
    """
    Fallback volatility calculation, used when yfinance's implied
    volatility is too low/unreliable to trust (see calculate_model_price).
    Pulls 6 months of daily closing prices, computes daily percentage
    returns, then annualizes the standard deviation of those returns
    (252 = average number of trading days in a year) to get a volatility
    figure comparable to implied volatility.
    """
    hist = yf.download(ticker_symbol, period="6mo", interval="1d")
    closes = hist["Close"].values.flatten()

    daily_returns = np.diff(closes) / closes[:-1]
    historical_volatility = np.std(daily_returns) * np.sqrt(252)

    return historical_volatility

