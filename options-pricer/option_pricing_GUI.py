import tkinter as tk
import yfinance as yf
from tkinter import ttk
import subprocess
import os

class OptionsPricerApp:
    def __init__(self, root):
        # save a reference to the window itself, in case other methods need it later
        self.root = root

        self.root.title("Options Pricer")   # text shown in the window's title bar

        # launch the window in true fullscreen mode (no title bar, covers the whole screen)
        self.root.attributes("-fullscreen", True)
        # pressing Escape closes the app entirely (see close_app below)
        self.root.bind("<Escape>", self.close_app)

        # StringVar acts as a shared "box" between this variable and the Entry widget below.
        # When the user types into the Entry, self.ticker_var updates automatically,
        # and we can read it later with self.ticker_var.get()
        self.ticker_var = tk.StringVar()
        self.ticker_var.trace_add("write", self.on_ticker_change)  # whenever the user types, call on_ticker_change() to clear the Call/Put selection and expiration date

        # a plain text label, just for display — the user can't type into this
        ttk.Label(root, text="Ticker:").grid(row=0, column=0)

        # the actual text box the user types into.
        # textvariable=self.ticker_var links this widget to the StringVar above
        self.ticker_entry = ttk.Entry(root, textvariable=self.ticker_var)
        self.ticker_entry.grid(row=0, column=1)
        self.ticker_entry.bind("<FocusOut>", lambda event: self.show_stock_price()) #when the user clicks away from the ticker entry box, call show_stock_price() to display the current stock price
        self.ticker_entry.bind("<Return>", self.on_ticker_enter) #when the user presses Enter while in the ticker entry box, call show_stock_price() to display the current stock price

        self.ticker_error_var = tk.StringVar()
        ttk.Label(root, textvariable=self.ticker_error_var, foreground="red").grid(row=1, column=1)

        # StringVar for the Call/Put selection, same syncing purpose as ticker_var above
        self.option_type = tk.StringVar()
        # both Radiobuttons share self.option_type, making them mutually exclusive;
        # command= calls show_expiration_dates() whenever the user clicks either button, so we can validate the ticker immediately and show and get the expiration dates for the chosen ticker
        ttk.Radiobutton(root, text="Call", value="Call", variable=self.option_type, command=self.show_expiration_dates).grid(row=0, column=2)
        ttk.Radiobutton(root, text="Put", value="Put", variable=self.option_type, command=self.show_expiration_dates).grid(row=0, column=3)

        self.expiration_var = tk.StringVar()
        self.expiration_dates_combo = ttk.Combobox(root, textvariable=self.expiration_var, values=())
        self.expiration_dates_combo.grid(row=0, column=4)
        self.expiration_dates_combo.bind("<<ComboboxSelected>>", lambda event: self.fetch_contracts())  

        self.stock_price_var = tk.StringVar()
        ttk.Label(root, textvariable=self.stock_price_var).place(relx=0.98, rely=0.02, anchor="ne")  # place the stock price label in the top-right corner of the window


        # these three lines force the window to the front and grab focus on launch,
        # then release "always on top" so it doesn't stay pinned above everything forever
        root.lift()
        root.attributes("-topmost", True)
        root.after_idle(root.attributes, "-topmost", False)

    def on_ticker_enter(self, event=None):
        self.root.focus_set()  # remove focus from the ticker entry box, so the user can see the stock price label update immediately:
        self.show_stock_price()

    def is_ticker_valid(self):
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
                self.stock_price_var.set(f"Current Price: ${self.s:.2f}")
            else:
                self.stock_price_var.set("")
        else:
            self.stock_price_var.set("")

    def on_ticker_change(self, *args):
        # *args catches tkinter's automatic arguments for trace callbacks, which we don't need here
        self.option_type.set("")  # clear the Call/Put selection whenever the ticker changes
        self.expiration_var.set("")  # clear whatever's shown in the combobox's text field
        self.expiration_dates_combo["values"] = ()  # clear the combobox's dropdown list of expiration dates
        self.ticker_error_var.set("")  # clear any previous error messages

    def show_expiration_dates(self):
        if self.is_ticker_valid():
            self.expiration_dates_combo["values"] = self.expiration_dates
        else:
            self.expiration_dates_combo["values"] = ()

        self.expiration_var.set("")  # clear the combobox's text field so the user can pick a new date

    def fetch_contracts(self):
        contracts = self.ticker.option_chain(self.expiration_var.get())

        if self.option_type.get() == "Call":
            self.chosen_contract = contracts.calls
        else:
            self.chosen_contract = contracts.puts

        

    def close_app(self, event=None):
        self.root.destroy()
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