# Options Pricer GUI — Progress Update

Built a working tkinter GUI for the Black-Scholes options pricer.

## Working so far
- Ticker input with live validation (checks blank/invalid tickers via yfinance)
- Call/Put selection (Radiobuttons)
- Dynamic expiration dates dropdown, populated per ticker
- Contract fetching tied to expiration date selection
- Live stock price display (top-right corner)
- Fullscreen window, Escape to close and return focus to VS Code

## Environment fix
Old venv was built on macOS's Command Line Tools Python (Tk 8.5), which silently
failed to render widgets. Fixed by installing Python 3.11 + Tk 8.6 via Homebrew
and rebuilding the venv.

## Still to do
- Treeview table to display fetched contracts (strike, volume, lastPrice, bid,
  ask, impliedVolatility)
- Row selection for picking a specific contract
- Wiring in the Black-Scholes calculation/comparison
