ROLE = "source"
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

import src
from  MAC import MAC_TX


conf = src.CONFIG()

if conf.connectionString is None:
    print("No connection string provided")
    exit(1)

if conf.MQTT is None:
    print("No MQTT broker provided")
    exit(1)



while True:
    phase = 1
    tx = MAC_TX(ROLE=ROLE, conf=conf, SC=True)
    if tx.transmit(repeat = 10):
        print(f"transmission {ROLE}, phase_{phase} done")
    else:
        print(f"failed synchronization {ROLE}, phase_{phase}")
        continue



