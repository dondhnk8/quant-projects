import numpy as np
from scipy.stats import norm
from black_scholes import black_scholes_price

def probability_of_profits(S, K, T, r, sigma, premium, option_type):
    if S <= 0 or K <= 0 or sigma <= 0 or T <= 0 or premium < 0:
        return None
    elif option_type != "Call" and option_type != "Put":
        return None
    elif option_type == "Call":
        breakeven = K + premium
    else:
        if premium >= K:
            return None
        else:
            breakeven = K - premium

    d2s = (np.log(S/breakeven) + (r - (sigma**2)/2)*T)/(sigma*(T**0.5))

    if option_type == "Call":
        prob = norm.cdf(d2s)
    else:
        prob = 1 - norm.cdf(d2s)

    xprof = black_scholes_price(S, K, T, r, sigma, option_type).price - premium

    return prob, xprof

