# %%
ROLE = "source"

import numpy as np
import matplotlib.pyplot as plt
import hmac

import sys
sys.path.append('../../')

import src

conf = src.CONFIG()
tx = src.TX(role=ROLE, conf=conf)

MAC_bits = tx.hex_to_binary_list(hmac.new(tx.conf.MAC_KEY.encode(), conf.PAYLOAD.encode(), 'sha256').hexdigest())
payload = tx.string_to_bits(tx.conf.PAYLOAD)
fsk_signal = tx.fsk_modulate(np.concatenate([payload, MAC_bits]), # sends with half the power,
                # mac = self.MAC_bits,
                # alpha = self.conf.ALPHA,
                sps = tx.conf.TX_SPS, 
                preamble = np.concatenate([ [0 for _ in range(1000//conf.TX_SPS)] , conf.PREAMBLE]), 
                postamble = np.concatenate([conf.POSTAMBLE, [0 for _ in range(1000//conf.TX_SPS)]]),
                scale = conf.TX_PAYLOAD_POWER_SCALE # send the payload with half the power of the preamble
                )

# %%
import os

while True:
    src.MQTT_TX(conf=conf, role=ROLE, phase=1,verbose=1).wait_for_all_ready(sleep_time=1.5)
    import time
    for i in range(10):
        tx.send_waveform(fsk_signal)
        time.sleep(0.1)


