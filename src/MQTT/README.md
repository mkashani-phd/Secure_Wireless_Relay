## 📡 MQTT 2-Phase Synchronization System

This project implements a **2-phase MQTT synchronization protocol** between three distributed Python processes:

- **Source** (TX)
- **Relay** (RX)
- **destination** (RX)

It ensures all nodes are synchronized before starting an experiment, regardless of their startup order.

---

### 🧩 Architecture

#### 🟦 MQTT Topics

- **`ready`** – RX nodes (Relay, destination) publish `"ready"` messages to signal readiness.
- **`begin`** – TX node (Source) publishes `"begin"` to trigger RX nodes to start recording while it start transmitting maybe after a small delay.

---

### 🔄 Workflow

#### ✅ Phase 1: Synchronization

1. **RX nodes** (`relay`, `destination`):
   - Connect to the broker.
   - Publish `"ready"` to the topic `ready` with `retain=True`.
   - Subscribe to `begin`, and wait.

2. **TX node** (`source`):
   - Connects to the broker and subscribes to `ready`.
   - Receives retained `"ready"` messages from RX nodes.
   - Once both `"relay"` and `"destination"` are ready:
     - Publishes `"begin"` to `begin`.
     - Clears the retained `"ready"` state to prepare for the next experiment.

#### ✅ Phase 2 (Optional or repeated):
- Same process can be repeated with fresh `"ready"` signals, but only the `"destination"`-`"ready"` is required to begin.

---

### 🛠️ Running the Code

#### 🔹 RX Node (Relay or destination)

```python
from mqtt_sync import MQTT_RX
import config

rx = MQTT_RX(config, role='relay')  # or 'destination'
rx.send_ready()
rx.wait_for_begin()
# Proceed to record or receive
```

#### 🔹 TX Node (Source)

```python
from mqtt_sync import MQTT_TX
import config

tx = MQTT_TX(config)
tx.wait_for_all_ready()
tx.send_begin()
# Proceed to transmit
```

---

### 🧼 Reset Behavior

After sending `"begin"`, the TX node clears the retained `"ready"` state so that the MQTT broker is clean for the next experiment round.

---

### 🔐 Broker Notes

- This code assumes you are using a broker like **Adafruit IO** or **Mosquitto** that supports:
  - Retained messages
  - Basic authentication (username/password)

Ensure the broker details are set in `config.py`.

---

Let me know if you'd like a diagram, Docker setup, or deployment script added!