# importing the necessary libraries
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

ticker = input("Enter the stock ticker (e.g. AAPL): ").upper()
period = input("Enter the period (e.g. 1wk, 1mo, 3mo, 1y): ")

# fetching data of apple prices
data = yf.download(ticker, period=period, interval="1d")

# pull out the actual price numbers as plain array
# flatten function is because the new version of yfinance returns .values as an array, even if its only one element, and we want it to be a number
closes = data["Close"].values.flatten()
# the corresponding dates
dates = data.index

# calculate the percent change between each consecutive day
pct_changes = [(closes[i+1] - closes[i])/closes[i] for i in range(len(closes)-1)]

# find the largest percentage change, used to normalize the color intensity
max_change = max(abs(i) for i in pct_changes)

# plt.subplots() creates a figure and gives us back two objects:
# fig = the whole window/canvas (used for overall settings, saving the image, etc.)
# ax = the actual plot area where lines, labels, and ticks live
# using these explicitely instead of plt.plot() lets us control details directly
fig, ax = plt.subplots()
# add a gray background
ax.set_facecolor("#504848")

for i in range(len(closes)-1):
    change = pct_changes[i]

    # normalise this change to 0 to 1 scale, relative to the biggest move in the dataset
    strength = abs(change) / max_change

    if change > 0:
        #interpolate between gray (0,0,0 gray = 0.5,0.5,0.5) and green (0,1,0)
        #strength = 0 -> pure gray, strength = 1 -> pure green
        r = 0.5 * (1 - strength)
        g = 0.5 * (1 + strength)
        b = 0.5 * (1 - strength)
    else:
        #interpolate between gray and red (1,0,0)
        r = 0.5 * (1 + strength)
        g = 0.5 * (1 - strength)
        b = 0.5 * (1 - strength)

    color = (r, g, b)
    ax.plot(dates[i:i+2], closes[i:i+2], color = color, linewidth = 3)


# basically telling how to structure the x axis based on the time period requested

num_days = len(dates)
if num_days <= 14:
    locator = mdates.DayLocator()
    date_format = '%m-%d'
elif num_days <= 90:
    locator = mdates.WeekdayLocator(interval=1)
    date_format = '%m-%d'
elif num_days <= 365:
    locator = mdates.MonthLocator()
    date_format = '%Y-%m'
elif num_days <= 365*10:
    locator = mdates.MonthLocator(interval=4)
    date_format = '%Y-%m'
else:
    locator = mdates.YearLocator()
    date_format = '%Y'

ax.xaxis.set_major_locator(locator)
ax.xaxis.set_major_formatter(mdates.DateFormatter(date_format))
fig.autofmt_xdate()
ax.grid(True, linestyle='--', alpha=0.4, linewidth = 0.7, color = 'black')

plt.title(f"{ticker} Closing Prices - {period}")
plt.xlabel("Date")
plt.ylabel("Price")
plt.show()