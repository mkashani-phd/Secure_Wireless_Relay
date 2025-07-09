import tkinter as tk
from tkinter import messagebox
from pymongo import MongoClient

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["config"]  # ← replace with your DB name
collection = db["config"]  # ← replace with your collection name

# Fields to edit with sliders and their (min, max, resolution) settings
slider_fields = {
    'TX_REPEAT': (1, 50, 1),
    'TX_GAIN': (0, 89.8, 1),
    'TX_RELAY_GAIN': (0, 89.8, 1),
    'RX_GAIN': (0, 71, 1),
    'RX_RELAY_GAIN': (0, 71, 1),
    'RX_MAX_MAGNITUDE_THRESHOLD_SCALE': (0.0, 1.0, 0.01),
    "TX_PAYLOAD_POWER_SCALE" : (0.0, 1.0, 0.0001),
    'FREQ': (.5e9, 6.0e9, 1e8),
    'FREQ_DEV': (25e3, 250e3, 25e3),
    'TX_SPS': (1, 200, 1),
    'TX_RATE': (1e6, 50e6, 1e5),
    'RX_RATE': (1e6, 50e6, 1e5),
    'LPF_CUTOFF': (1e5, 1e6, 1e4),
    'ALPHA': (0.0, 1.0, 0.01),
    'ACQ_TIME': (1.0, 10.0, 0.1),
    'PREAMBLE_REPEAT': (1, 30, 1),

}

linked_pairs = {
    'TX_GAIN': 'TX_RELAY_GAIN',
    'RX_GAIN': 'RX_RELAY_GAIN'
}

class ConfigSliderEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("MongoDB Config Editor (Linked Sliders + Input)")

        self.config = collection.find_one() or {}
        self.config.pop('_id', None)

        self.vars = {}      # DoubleVars
        self.entries = {}   # Entry widgets

        for key, (min_val, max_val, step) in slider_fields.items():
            self.create_slider_row(key, min_val, max_val, step)

    def create_slider_row(self, key, min_val, max_val, step):
        frame = tk.Frame(self.root)
        frame.pack(fill='x', padx=10, pady=5)

        tk.Label(frame, text=key, width=18, anchor='w').pack(side='left')

        var = tk.DoubleVar()
        var.set(self.config.get(key, min_val))
        self.vars[key] = var

        slider = tk.Scale(frame,
                          from_=min_val,
                          to=max_val,
                          resolution=step,
                          variable=var,
                          orient='horizontal',
                          length=250,
                          command=lambda val, k=key: self.update_from_slider(k, float(val)))
        slider.pack(side='left')

        entry = tk.Entry(frame, width=10)
        entry.insert(0, f"{var.get():.3g}")
        entry.pack(side='left', padx=5)
        self.entries[key] = entry

        # Update entry when slider moves
        def sync_entry(*args):
            entry.delete(0, tk.END)
            entry.insert(0, f"{var.get():.3g}")
        var.trace_add('write', sync_entry)

        # Update from entry to slider + DB
        def on_entry_change(event, k=key, v=var):
            try:
                val = float(entry.get())
                v.set(val)  # this will trigger trace, slider, and DB update
                self.update_mongo(k, val)
                if k in linked_pairs:
                    self.set_linked_value(k, val)
            except ValueError:
                entry.delete(0, tk.END)
                entry.insert(0, f"{v.get():.3g}")
        entry.bind("<Return>", on_entry_change)
        entry.bind("<FocusOut>", on_entry_change)

    def update_from_slider(self, key, value):
        self.update_mongo(key, value)
        if key in linked_pairs:
            self.set_linked_value(key, value)

    def set_linked_value(self, key, value):
        linked_key = linked_pairs[key]
        if linked_key in self.vars:
            self.vars[linked_key].set(value)
            self.update_mongo(linked_key, value)

    def update_mongo(self, key, value):
        if key not in ['ALPHA', 'ACQ_TIME', 'RX_MAX_MAGNITUDE_THRESHOLD_SCALE', 'TX_PAYLOAD_POWER_SCALE']:
            value = int(value)  # Cast to int for all keys except 'ALPHA' and 'ACQ_TIME'
        collection.update_one({}, {"$set": {key: value}}, upsert=True)


# Run it
root = tk.Tk()
app = ConfigSliderEditor(root)
root.mainloop()