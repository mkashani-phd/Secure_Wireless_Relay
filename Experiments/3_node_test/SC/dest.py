ROLE = "destination"
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

import src

from  MAC import MAC_SC_RX


conf = src.CONFIG()

if conf.connectionString is None:
    print("No connection string provided")
    exit(1)

if conf.MQTT is None:
    print("No MQTT broker provided")
    exit(1)



while True:
    phase = 1
    rx = MAC_SC_RX(ROLE=ROLE, conf=conf)

    file = rx.record(phase=phase)
    if not file:
        print(f"failed synchronization {ROLE}, phase_{phase}")
        continue

    rx.process_all_frames(file=file, phase=phase)

    phase = 2

    file = rx.record(phase=phase)
    if not file:
        print(f"failed synchronization {ROLE}, phase_{phase}")
        continue

    rx.process_all_frames(file=file, phase=phase)




