import numpy as np
import scipy as sc
from collections import namedtuple

def black_scholes_price(S, K, T, r, sigma, option_type):
    """
    The Black-Scholes formula itself.
    S = current stock price, K = strike price, T = time to expiration
    (in years), r = risk-free rate, sigma = volatility, option_type =
    "Call" or "Put". d1/d2 are intermediate values the formula is built
    from; norm.cdf is the cumulative distribution function of the
    standard normal distribution, which is what turns d1/d2 into
    probabilities the formula uses to arrive at a price.
    """
    d1 = (np.log(S/K) + (r + (sigma**2)/2) * T) / (sigma * (T**0.5))
    d2 = d1 - sigma * (T**0.5)

    gamma = sc.stats.norm.pdf(d1) / (S * sigma * (T**0.5))
    vega = S * sc.stats.norm.pdf(d1) * (T**0.5)

    if option_type == "Call":
        price = S * sc.stats.norm.cdf(d1) - K * np.exp(-r * T) * sc.stats.norm.cdf(d2)
        delta = sc.stats.norm.cdf(d1)
        theta = -(S * sc.stats.norm.pdf(d1) * sigma) / (2 * (T**0.5)) - r * K * np.exp(-r*T) * sc.stats.norm.cdf(d2)
        rho = K * T * np.exp(-r*T) * sc.stats.norm.cdf(d2)
    elif option_type == "Put":
        price = K*np.exp(-r*T)*sc.stats.norm.cdf(-d2) - S*sc.stats.norm.cdf(-d1)
        delta = sc.stats.norm.cdf(d1) - 1
        theta = -(S * sc.stats.norm.pdf(d1) * sigma) / (2 * (T**0.5)) + r * K * np.exp(-r*T) * sc.stats.norm.cdf(-d2)
        rho = -K * T * np.exp(-r*T) * sc.stats.norm.cdf(-d2)
    else:
        return "Option Value Error"

    calculations = BSResult(price=price, delta=delta, gamma=gamma, vega=vega, theta=theta, rho=rho)
    return calculations

BSResult = namedtuple("BSResult", ["price", "delta", "gamma", "vega", "theta", "rho"])