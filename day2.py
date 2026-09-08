import yfinance as yf
"""
aapl = yf.Ticker("AAPL")
aapl_pnow = aapl.info["currentPrice"]
print(f"AAPL current price: ${aapl_pnow}")

nvda = yf.Ticker("NVDA")
nvda_pnow = nvda.info["currentPrice"]
print(f"NVDA current price: ${nvda_pnow}")

nvda_mcap = nvda.info["marketCap"]
nvda_mcap_tr = round(nvda_mcap/1_000_000_000_000, 2)
print(nvda_mcap_tr)
print(round(nvda_mcap/1_000_000_000_000, 2))
print(round(nvda.info["marketCap"]/1_000_000_000_000, 2))
print(round(yf.Ticker("NVDA").info["marketCap"]/1_000_000_000_000, 2))
"""