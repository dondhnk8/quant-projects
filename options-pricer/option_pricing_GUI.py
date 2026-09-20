import tkinter as tk
import yfinance as yf
from tkinter import ttk
import subprocess
import os
from black_scholes import black_scholes_price
from market_data import get_historical_volatility, get_risk_free_rate, get_time_to_expiration


# ============================================================
# Standalone helper functions
# These don't depend on any particular app instance (no `self`),
# so they live outside the class and just take plain arguments in,
# plain values out.
# ============================================================

def get_price_history(ticker_symbol, period="5d", interval="30m"):
    """
    Fetches recent closing prices for the sparkline chart. 30-minute
    intervals over 5 days gives a reasonably smooth line without
    pulling an excessive number of data points.
    """
    hist = yf.download(ticker_symbol, period=period, interval=interval, progress=False)
    closes = hist["Close"].values.flatten()
    return closes


# --- Dark theme palette, defined once so every color reference below stays
# consistent. Changing a color here updates it everywhere it's used. ---
BG = "#12141a"          # main window background
PANEL_BG = "#1a1d26"    # slightly lighter panels (entries, table, results card)
ROW_ALT_BG = "#20242f"  # alternating table row color
ACCENT = "#4f8cff"      # blue accent (selection highlight, button)
ACCENT_DIM = "#2a3550"  # dimmer accent, used for subtle borders
TEXT = "#e6e8ef"        # primary text color
TEXT_DIM = "#8c92a4"    # secondary/muted text (labels, captions)
ERROR = "#ff5c5c"       # red, used for errors and negative differences
GOOD = "#3ddc84"        # green, used for positive differences
GRID = "#333846"        # faint gridlines on the sparkline chart
FONT = ("Helvetica Neue", 13)
FONT_BOLD = ("Helvetica Neue", 13, "bold")
FONT_LARGE = ("Helvetica Neue", 22, "bold")
FONT_HEADING = ("Helvetica Neue", 12, "bold")
FONT_SMALL = ("Helvetica Neue", 8)


class OptionsPricerApp:
    def __init__(self, root):
        # save a reference to the window itself, in case other methods need it later
        self.root = root
        self.root.title("Options Pricer")   # text shown in the window's title bar

        # launch the window in true fullscreen mode (no title bar, covers the whole screen)
        self.root.attributes("-fullscreen", True)
        # pressing Escape closes the app entirely (see close_app below)
        self.root.bind("<Escape>", self.close_app)
        self.root.configure(bg=BG)

        # configures every ttk widget's colors/fonts before we build any of them
        self._setup_style()

        # ============================================================
        # Top control bar: ticker entry, Call/Put, expiration, stock price + sparkline
        # ============================================================
        control_frame = tk.Frame(root, bg=BG)
        control_frame.pack(fill="x", padx=30, pady=(24, 16))

        ttk.Label(control_frame, text="Ticker", style="Muted.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 8))

        # StringVar acts as a shared "box" between this variable and the Entry widget below.
        # When the user types into the Entry, self.ticker_var updates automatically,
        # and we can read it later with self.ticker_var.get()
        self.ticker_var = tk.StringVar()
        self.ticker_var.trace_add("write", self.on_ticker_change)  # whenever the user types, call on_ticker_change()

        # the actual text box the user types into.
        # textvariable=self.ticker_var links this widget to the StringVar above
        self.ticker_entry = ttk.Entry(control_frame, textvariable=self.ticker_var, width=12, font=FONT_BOLD)
        self.ticker_entry.grid(row=0, column=1, sticky="w", padx=(0, 28), ipady=4)
        self.ticker_entry.bind("<FocusOut>", lambda event: self.show_stock_price())  # show price when the user clicks away
        self.ticker_entry.bind("<Return>", self.on_ticker_enter)  # show price when the user presses Enter

        # StringVar for the Call/Put selection, same syncing purpose as ticker_var above
        self.option_type = tk.StringVar()
        # both Radiobuttons share self.option_type, making them mutually exclusive;
        # command= calls show_expiration_dates() whenever the user clicks either button
        ttk.Radiobutton(control_frame, text="Call", value="Call", variable=self.option_type,
                         command=self.show_expiration_dates, style="TRadiobutton").grid(row=0, column=2, padx=(0, 16))
        ttk.Radiobutton(control_frame, text="Put", value="Put", variable=self.option_type,
                         command=self.show_expiration_dates, style="TRadiobutton").grid(row=0, column=3, padx=(0, 28))

        ttk.Label(control_frame, text="Expiration", style="Muted.TLabel").grid(row=0, column=4, sticky="w", padx=(0, 8))

        self.expiration_var = tk.StringVar()
        self.expiration_dates_combo = ttk.Combobox(control_frame, textvariable=self.expiration_var, values=(),
                                                     width=13, font=FONT, state="readonly")
        self.expiration_dates_combo.grid(row=0, column=5, sticky="w")
        self.expiration_dates_combo.bind("<<ComboboxSelected>>", lambda event: self.fetch_contracts())

        # price_frame holds the sparkline (with its own "5D" caption above it)
        # and the current price label together, right-aligned as one unit.
        # grid_columnconfigure(..., weight=1) on column 6 makes that column
        # absorb all the extra horizontal space, which is what pushes the
        # whole group to the right edge of the control bar
        price_frame = tk.Frame(control_frame, bg=BG)
        price_frame.grid(row=0, column=6, sticky="e")
        control_frame.grid_columnconfigure(6, weight=1)

        # a small vertical container so the "5D" caption sits above the
        # canvas instead of overlapping the drawn chart
        sparkline_container = tk.Frame(price_frame, bg=BG)
        sparkline_container.pack(side="left", padx=(0, 12))

        ttk.Label(sparkline_container, text="5D", style="Muted.TLabel", font=FONT_SMALL).pack(anchor="w")

        self.sparkline_canvas = tk.Canvas(sparkline_container, width=170, height=50, bg=PANEL_BG, highlightthickness=0)
        self.sparkline_canvas.pack()

        self.stock_price_var = tk.StringVar()
        ttk.Label(price_frame, textvariable=self.stock_price_var, style="PriceHeader.TLabel").pack(side="left")

        self.ticker_error_var = tk.StringVar()
        ttk.Label(control_frame, textvariable=self.ticker_error_var, style="Error.TLabel")\
            .grid(row=1, column=1, sticky="w", pady=(4, 0))

        # ============================================================
        # Contracts table
        # ============================================================
        table_frame = tk.Frame(root, bg=BG)
        table_frame.pack(fill="both", expand=True, padx=30, pady=(0, 16))

        self.sort_reverse = {}  # tracks ascending/descending sort state per column
        columns = ("strike", "lastPrice", "bid", "ask", "volume", "impliedVolatility")
        # separate display text from the internal column names, so the table
        # can show friendlier headings ("Implied Vol") while the underlying
        # data still uses yfinance's original field names
        headings = {
            "strike": "Strike", "lastPrice": "Last", "bid": "Bid", "ask": "Ask",
            "volume": "Volume", "impliedVolatility": "Implied Vol",
        }

        self.contracts_tree = ttk.Treeview(table_frame, columns=columns, show="headings",
                                            style="Dark.Treeview", height=14)
        for col in columns:
            # command= makes each heading clickable, triggering sort_by_column for that column
            self.contracts_tree.heading(col, text=headings[col], command=lambda c=col: self.sort_by_column(c))
            self.contracts_tree.column(col, width=140, anchor="center", stretch=True)

        # tags let us apply different background colors to alternating rows;
        # fetch_contracts() assigns "evenrow"/"oddrow" to each inserted row
        self.contracts_tree.tag_configure("oddrow", background=ROW_ALT_BG)
        self.contracts_tree.tag_configure("evenrow", background=PANEL_BG)

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.contracts_tree.yview)
        self.contracts_tree.configure(yscrollcommand=vsb.set)

        self.contracts_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        # whenever the user clicks a row, call on_contract_select
        self.contracts_tree.bind("<<TreeviewSelect>>", self.on_contract_select)

        # ============================================================
        # Bottom action / results panel
        # ============================================================
        # a bordered card (via highlightbackground/highlightthickness) to
        # visually separate the button + results from the table above it
        results_frame = tk.Frame(root, bg=PANEL_BG, highlightbackground=ACCENT_DIM, highlightthickness=1)
        results_frame.pack(fill="x", padx=30, pady=(0, 24))

        # an inner frame just to control padding inside the bordered card
        # without affecting the border itself
        inner = tk.Frame(results_frame, bg=PANEL_BG)
        inner.pack(fill="x", padx=24, pady=20)

        # plain tk.Button instead of ttk.Button here, since ttk buttons don't
        # give easy control over background color on macOS — tk's does
        self.calculate_button = tk.Button(
            inner, text="Calculate Model Price", command=self.calculate_model_price,
            bg=ACCENT, fg="#0a0a0a", activebackground="#6ea1ff", activeforeground="#0a0a0a",
            font=FONT_BOLD, relief="flat", cursor="hand2", padx=18, pady=10, bd=0,
        )
        self.calculate_button.grid(row=0, column=0, rowspan=3, sticky="w", padx=(0, 40))

        self.model_error_var = tk.StringVar()
        ttk.Label(inner, textvariable=self.model_error_var, style="Error.TLabel")\
            .grid(row=0, column=0, rowspan=3, sticky="w", padx=(220, 0))

        # column headers for the three result values
        ttk.Label(inner, text="MODEL PRICE", style="ResultLabel.TLabel").grid(row=0, column=1, sticky="w", padx=(0, 60))
        ttk.Label(inner, text="MARKET PRICE", style="ResultLabel.TLabel").grid(row=0, column=2, sticky="w", padx=(0, 60))
        ttk.Label(inner, text="DIFFERENCE", style="ResultLabel.TLabel").grid(row=0, column=3, sticky="w")

        # "—" as a placeholder before any calculation has run, instead of a blank label
        self.model_price_var = tk.StringVar(value="—")
        self.market_price_var = tk.StringVar(value="—")
        self.difference_var = tk.StringVar(value="—")

        ttk.Label(inner, textvariable=self.model_price_var, style="ResultValue.TLabel").grid(row=1, column=1, sticky="w", padx=(0, 60))
        ttk.Label(inner, textvariable=self.market_price_var, style="ResultValue.TLabel").grid(row=1, column=2, sticky="w", padx=(0, 60))
        # kept as its own variable (self.difference_label) rather than an anonymous
        # widget, because calculate_model_price needs to change its color later
        self.difference_label = ttk.Label(inner, textvariable=self.difference_var, style="ResultValue.TLabel")
        self.difference_label.grid(row=1, column=3, sticky="w")

        self.delta_var = tk.StringVar(value="—")
        self.gamma_var = tk.StringVar(value="—")
        self.vega_var = tk.StringVar(value="—")
        self.theta_var = tk.StringVar(value="—")
        self.rho_var = tk.StringVar(value="—")

        inner.grid_columnconfigure(4, weight=1)

        ttk.Label(inner, text="Δ", style="ResultLabel.TLabel").grid(row=0, column=5, sticky="w", padx=(0, 24))
        ttk.Label(inner, text="Γ", style="ResultLabel.TLabel").grid(row=0, column=6, sticky="w", padx=(0, 24))
        ttk.Label(inner, text="V", style="ResultLabel.TLabel").grid(row=0, column=7, sticky="w", padx=(0, 24))
        ttk.Label(inner, text="Θ", style="ResultLabel.TLabel").grid(row=0, column=8, sticky="w", padx=(0, 24))
        ttk.Label(inner, text="ρ", style="ResultLabel.TLabel").grid(row=0, column=9, sticky="w")

        ttk.Label(inner, textvariable=self.delta_var, style="ResultValue.TLabel").grid(row=1, column=5, sticky="e", padx=(0, 24))
        ttk.Label(inner, textvariable=self.gamma_var, style="ResultValue.TLabel").grid(row=1, column=6, sticky="e", padx=(0, 24))
        ttk.Label(inner, textvariable=self.vega_var, style="ResultValue.TLabel").grid(row=1, column=7, sticky="e", padx=(0, 24))
        ttk.Label(inner, textvariable=self.theta_var, style="ResultValue.TLabel").grid(row=1, column=8, sticky="e", padx=(0, 24))
        ttk.Label(inner, textvariable=self.rho_var, style="ResultValue.TLabel").grid(row=1, column=9, sticky="e")

        # these three lines force the window to the front and grab focus on launch,
        # then release "always on top" so it doesn't stay pinned above everything forever
        root.lift()
        root.attributes("-topmost", True)
        root.after_idle(root.attributes, "-topmost", False)

    def _setup_style(self):
        """
        Configures the dark theme applied to every ttk widget in the app.
        ttk widgets don't take simple bg="..." like plain tk widgets do —
        they're styled through this ttk.Style object using named styles
        that widgets reference via their `style=` argument (or inherit
        by default if they don't specify one).
        """
        style = ttk.Style()
        # "clam" is the theme that actually honors custom colors; the
        # default macOS theme mostly ignores color overrides
        style.theme_use("clam")

        # "." is the fallback default for any widget that doesn't have
        # its own more specific style rule below
        style.configure(".", background=BG, foreground=TEXT, font=FONT)
        style.configure("TFrame", background=BG)

        style.configure("TLabel", background=BG, foreground=TEXT, font=FONT)
        style.configure("Muted.TLabel", background=BG, foreground=TEXT_DIM, font=FONT)
        style.configure("Error.TLabel", background=BG, foreground=ERROR, font=FONT_BOLD)
        style.configure("PriceHeader.TLabel", background=BG, foreground=TEXT, font=FONT_LARGE)
        style.configure("ResultLabel.TLabel", background=PANEL_BG, foreground=TEXT_DIM, font=("Helvetica Neue", 11, "bold"))
        style.configure("ResultValue.TLabel", background=PANEL_BG, foreground=TEXT, font=FONT_LARGE)

        # fieldbackground is the actual typing area color for an Entry,
        # separate from its border color
        style.configure("TEntry", fieldbackground=PANEL_BG, foreground=TEXT,
                         insertcolor=TEXT, bordercolor=ACCENT_DIM, lightcolor=PANEL_BG, darkcolor=PANEL_BG)

        style.configure("TRadiobutton", background=BG, foreground=TEXT, font=FONT)
        # style.map sets different colors depending on widget *state* —
        # here, the selected radio button's text turns accent-colored
        style.map("TRadiobutton", background=[("active", BG)], foreground=[("selected", ACCENT)])

        style.configure("TCombobox", fieldbackground=PANEL_BG, background=PANEL_BG, foreground=TEXT,
                         arrowcolor=TEXT, bordercolor=ACCENT_DIM)
        style.map("TCombobox", fieldbackground=[("readonly", PANEL_BG)], foreground=[("readonly", TEXT)])
        # the combobox's dropdown list is a plain tk Listbox under the hood and isn't
        # reachable through ttk.Style at all — option_add is the only way to theme it
        self.root.option_add("*TCombobox*Listbox.background", PANEL_BG)
        self.root.option_add("*TCombobox*Listbox.foreground", TEXT)
        self.root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
        self.root.option_add("*TCombobox*Listbox.font", FONT)

        style.configure("Dark.Treeview", background=PANEL_BG, fieldbackground=PANEL_BG, foreground=TEXT,
                         rowheight=30, font=FONT, borderwidth=0)
        style.configure("Dark.Treeview.Heading", background="#242836", foreground=TEXT_DIM,
                         font=FONT_HEADING, relief="flat", borderwidth=0)
        style.map("Dark.Treeview.Heading", background=[("active", "#2c3140")])
        # selected-row coloring: accent background with dark text for contrast
        style.map("Dark.Treeview", background=[("selected", ACCENT)], foreground=[("selected", "#0a0a0a")])

        style.configure("Vertical.TScrollbar", background=PANEL_BG, troughcolor=BG, bordercolor=BG, arrowcolor=TEXT_DIM)

    def on_ticker_enter(self, event=None):
        self.root.focus_set()  # remove focus from the ticker entry box, so the price label updates visibly
        self.show_stock_price()

    def is_ticker_valid(self):
        """
        Validates whatever's currently in the ticker box by attempting to
        fetch its option expiration dates from yfinance. If the ticker is
        empty or yfinance returns no expiration dates at all, it's treated
        as invalid and an appropriate error message is shown.
        """
        ticker_symbol = self.ticker_var.get().strip().upper()

        if ticker_symbol == "":
            self.ticker_error_var.set("Please enter a ticker symbol.")
            return False
        else:
            self.ticker = yf.Ticker(ticker_symbol)
            self.expiration_dates = self.ticker.options
            if self.expiration_dates == ():
                self.ticker_error_var.set("Please enter a valid ticker symbol.")
                return False
            else:
                self.ticker_error_var.set("")
                return True

    def show_stock_price(self):
        if self.is_ticker_valid():
            self.s = self.ticker.info.get("currentPrice", None)
            if self.s is not None:
                self.stock_price_var.set(f"${self.s:.2f}")
            else:
                self.stock_price_var.set("")

            prices = get_price_history(self.ticker_var.get())
            self.draw_sparkline(prices)
        else:
            self.stock_price_var.set("")
            self.sparkline_canvas.delete("all")

    def draw_sparkline(self, prices):
        """
        Draws a simple line chart on self.sparkline_canvas from a list of
        prices, with faint horizontal reference lines at the period's high
        and low, each labeled with its price.
        """
        self.sparkline_canvas.delete("all")  # clear any previously drawn chart

        if len(prices) < 2:
            return  # can't draw a meaningful line with 0 or 1 points

        width = int(self.sparkline_canvas["width"])
        height = int(self.sparkline_canvas["height"])
        label_width = 42  # reserved space on the left for the high/low price labels
        padding_x = 4     # keeps the line from touching the right edge
        padding_y = 8     # keeps the line off the very top/bottom edges

        low, high = min(prices), max(prices)
        price_range = high - low if high != low else 1  # avoid divide-by-zero if price was flat

        # the chart area is shifted right by label_width, leaving room on
        # the left for the high/low price text
        chart_left = label_width
        chart_width = width - label_width - padding_x

        def to_xy(i, price):
            """Converts a (index, price) pair into an (x, y) pixel coordinate on the canvas."""
            x = chart_left + (i / (len(prices) - 1)) * chart_width
            # canvas y=0 is the TOP, so higher prices need to map to smaller y values
            y = height - padding_y - ((price - low) / price_range) * (height - 2 * padding_y)
            return x, y

        # --- background: faint horizontal gridlines at the high and low, with labels ---
        # feeding high/low straight into to_xy always lands them at the very
        # top/bottom of the chart area, since they ARE the max/min
        _, high_y = to_xy(0, high)
        _, low_y = to_xy(0, low)

        self.sparkline_canvas.create_line(chart_left, high_y, width, high_y, fill=GRID, width=1)
        self.sparkline_canvas.create_line(chart_left, low_y, width, low_y, fill=GRID, width=1)

        # anchor="w" anchors the text's left edge (not center) to the given
        # point, so x=0 puts each label flush against the canvas's left edge
        self.sparkline_canvas.create_text(0, high_y, text=f"{high:.1f}", fill=TEXT_DIM, font=FONT_SMALL, anchor="w")
        self.sparkline_canvas.create_text(0, low_y, text=f"{low:.1f}", fill=TEXT_DIM, font=FONT_SMALL, anchor="w")

        # --- foreground: the actual price line, drawn on top of the gridlines ---
        # color the line green if price went up over the period, red if down
        line_color = GOOD if prices[-1] >= prices[0] else ERROR
        points = [to_xy(i, price) for i, price in enumerate(prices)]
        # flatten [(x1,y1), (x2,y2), ...] into [x1,y1,x2,y2,...], the format create_line expects
        flat_points = [coord for point in points for coord in point]
        self.sparkline_canvas.create_line(*flat_points, fill=line_color, width=2, smooth=True)

    def on_ticker_change(self, *args):
        # *args catches tkinter's automatic arguments for trace callbacks, which we don't need here

        # force whatever the user typed to uppercase as they type.
        # Setting self.ticker_var re-triggers this same trace (since setting
        # a StringVar counts as a "write"), so without the early return below
        # this would loop forever: set uppercase -> trace fires -> set uppercase -> ...
        # Returning here lets the *next* automatic call (now already uppercase)
        # fall through and run the rest of this method instead.
        current = self.ticker_var.get()
        upper = current.upper()
        if current != upper:
            self.ticker_var.set(upper)
            return

        self.option_type.set("")  # clear the Call/Put selection whenever the ticker changes
        self.expiration_var.set("")  # clear whatever's shown in the combobox's text field
        self.expiration_dates_combo["values"] = ()  # clear the combobox's dropdown list of expiration dates
        self.ticker_error_var.set("")  # clear any previous error messages
        self.clear_contract_selection()

    def show_expiration_dates(self):
        if self.is_ticker_valid():
            self.expiration_dates_combo["values"] = self.expiration_dates
        else:
            self.expiration_dates_combo["values"] = ()

        self.expiration_var.set("")  # clear the combobox's text field so the user can pick a new date
        self.clear_contract_selection()

    def fetch_contracts(self):
        """
        Pulls the option chain for the currently selected ticker + expiration
        date, keeps either the calls or puts side depending on option_type,
        cleans up the volume column, and populates the table with the result.
        """
        contracts = self.ticker.option_chain(self.expiration_var.get())

        if self.option_type.get() == "Call":
            self.chosen_contract = contracts.calls
        else:
            self.chosen_contract = contracts.puts

        # .copy() avoids a "SettingWithCopyWarning" from pandas when we modify
        # the volume column below, since self.chosen_contract is a slice of
        # a larger dataframe returned by option_chain()
        self.chosen_contract = self.chosen_contract.copy()
        # "no volume" and "zero volume" mean the same real-world thing, so
        # it's safe to fill missing volume with 0 (unlike price/IV columns,
        # where a missing value and an actual zero mean very different things)
        self.chosen_contract["volume"] = self.chosen_contract["volume"].fillna(0)

        # clears the table and any previously selected contract, since we're
        # about to replace the table's contents entirely
        self.clear_contract_selection()

        # walk through each row of the dataframe and insert it as a table row,
        # alternating the "evenrow"/"oddrow" tag for the alternating-color effect
        for i, (_, row) in enumerate(self.chosen_contract.iterrows()):
            tag = "evenrow" if i % 2 == 0 else "oddrow"
            self.contracts_tree.insert("", "end", values=(
                row["strike"], row["lastPrice"], row["bid"],
                row["ask"], row["volume"], row["impliedVolatility"]
            ), tags=(tag,))

    def on_contract_select(self, event=None):
        """
        Fires when the user clicks a row in the table. Reads that row's
        displayed values back out of the Treeview and stores them on self,
        so calculate_model_price can use them later.
        """
        selected = self.contracts_tree.selection()
        if not selected:
            return  # nothing selected (e.g. the selection was cleared)

        item_id = selected[0]  # only one row can be selected at a time here
        values = self.contracts_tree.item(item_id, "values")

        # Treeview values come back as strings, not their original numeric
        # types, so each one needs converting back to a float
        self.selected_strike = float(values[0])
        self.selected_last_price = float(values[1])
        self.selected_bid = float(values[2])
        self.selected_ask = float(values[3])
        self.selected_volume = float(values[4])
        self.selected_implied_volatility = float(values[5])

    def clear_contract_selection(self):
        """
        Wipes the table and any stored selection, plus resets the result
        labels back to their placeholder state. Called whenever the ticker,
        option type, or expiration date changes, so a stale selection or
        stale results can never linger after the underlying data changes.
        """
        self.contracts_tree.delete(*self.contracts_tree.get_children())
        for attr in ("selected_strike", "selected_last_price", "selected_bid",
                     "selected_ask", "selected_volume", "selected_implied_volatility"):
            if hasattr(self, attr):
                delattr(self, attr)

        self.model_price_var.set("—")
        self.market_price_var.set("—")
        self.difference_var.set("—")
        self.model_error_var.set("")
        self.delta_var.set("—")
        self.gamma_var.set("—")
        self.vega_var.set("—")
        self.theta_var.set("—")
        self.rho_var.set("—")

    def sort_by_column(self, col):
        """
        Sorts the table's rows by the clicked column, toggling between
        ascending/descending on repeated clicks of the same heading.
        """
        # self.contracts_tree.set(item_id, col) reads back the value in that
        # column for a given row without changing anything, building a list
        # of (value, item_id) pairs to sort
        items = [(self.contracts_tree.set(item_id, col), item_id)
                 for item_id in self.contracts_tree.get_children("")]
        # values come back as strings, so float(...) is needed — sorting as
        # strings would put "9" after "10" alphabetically
        items.sort(key=lambda pair: float(pair[0]), reverse=self.sort_reverse.get(col, False))

        # .move(item_id, "", index) physically reorders the rows in the table
        # to match the sorted order
        for index, (_, item_id) in enumerate(items):
            self.contracts_tree.move(item_id, "", index)

        # remembers per-column ascending/descending state, so clicking the
        # same heading twice flips the order
        self.sort_reverse[col] = not self.sort_reverse.get(col, False)

    def calculate_model_price(self):
        """
        Runs Black-Scholes on the currently selected contract and displays
        the model price, the market price (bid-ask midpoint), and the
        difference between them (in both dollar and percentage terms).
        """
        if not hasattr(self, "selected_strike"):
            self.model_error_var.set("No contract selected.")
            return

        self.model_error_var.set("")

        S = self.s                                               # current stock price
        K = self.selected_strike                                 # strike price of the selected contract
        T = get_time_to_expiration(self.expiration_var.get())     # time to expiration, in years
        r = get_risk_free_rate()                                  # current risk-free rate
        option_type = self.option_type.get()                      # "Call" or "Put"

        # yfinance's implied volatility is sometimes unreliable (as low as 0
        # for some tickers/contracts), which would break the Black-Scholes
        # math entirely (division by zero). Below a 5% threshold, fall back
        # to a historical volatility calculation instead of trusting it.
        if self.selected_implied_volatility < 0.05:
            sigma = get_historical_volatility(self.ticker_var.get())
        else:
            sigma = self.selected_implied_volatility

        calculations = black_scholes_price(S, K, T, r, sigma, option_type)
        self.model_price_var.set(f"${calculations.price:.2f}")
        self.delta_var.set(f"{calculations.delta:.2f}")
        self.gamma_var.set(f"{calculations.gamma:.4f}")
        self.vega_var.set(f"${calculations.vega:.2f}")
        self.theta_var.set(f"{(calculations.theta / 365):.2f}")
        self.rho_var.set(f"${calculations.rho:.1f}")

        # market price is approximated as the midpoint between bid and ask,
        # since it's a more reliable live estimate than lastPrice (which can
        # be stale if the contract hasn't traded recently)
        market_price = (self.selected_bid + self.selected_ask) / 2
        difference = calculations.price - market_price
        percent_difference = (difference / market_price) * 100

        # sign is computed once and used for both the dollar and percent
        # figures, so they always agree with each other
        sign = "+" if difference >= 0 else "-"

        self.market_price_var.set(f"${market_price:.2f}")
        # abs(...) strips the sign from the raw numbers so `sign` (already
        # applied out front) is the only minus/plus shown — without abs()
        # here, a negative difference would double up as "-$-0.28"
        self.difference_var.set(f"{sign}${abs(difference):.2f} ({sign}{abs(percent_difference):.1f}%)")
        # colors the difference green if the model thinks the contract is
        # underpriced (model > market), red if overpriced
        self.difference_label.configure(foreground=GOOD if difference >= 0 else ERROR)


    def close_app(self, event=None):
        self.root.destroy()
        # macOS-specific: brings VS Code back to the front after the GUI closes
        subprocess.call(["osascript", "-e", 'tell application "Visual Studio Code" to activate'])


if __name__ == "__main__":
    root = tk.Tk()                 # create the actual window object
    app = OptionsPricerApp(root)   # this runs __init__, building all the widgets above

    # macOS-specific workaround: forces this script's window to become the frontmost,
    # focused window on launch (without this, it can open behind other apps/tabs)
    subprocess.call([
        "osascript", "-e",
        f'tell application "System Events" to set frontmost of the first process whose unix id is {os.getpid()} to true'
    ])

    root.mainloop()             # keeps the window open and listening for events (clicks, typing, etc.)