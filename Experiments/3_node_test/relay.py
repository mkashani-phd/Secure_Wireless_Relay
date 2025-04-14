# %%
ROLE  = "relay"
import os,time, pymongo ,copy
import pymongo.collection
import matplotlib.pyplot as plt
import numpy as np
import hmac
from concurrent.futures import ProcessPoolExecutor


import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

import src

# %%
def record(conf, ROLE ,phase):
    if src.MQTT_RX(conf=conf, role=ROLE, phase=phase, verbose=1).send_ready_and_wait_for_begin():
        file = rx.record()
        return file
    else:
        print("failed synchronization")
        return None


def process_frame(i):
    myclient = pymongo.MongoClient(conf.connectionString)
    mydb = myclient["MAC_1D"]
    collection=mydb[f'{ROLE}, phase_{phase}']
    frame = pp.frameByNumber(i)
    hard_decision, rs, SNR = demod.decode(frame)
    index = demod.detect_message_indices(
        received=list(hard_decision),
        preamble=conf.PREAMBLE,
        postamble=conf.POSTAMBLE,
        repeat=conf.PREAMBLE_REPEAT
    )

    if index[0] is None or index[1] is None:
        print(f"[Frame {i}] No preamble detected!")
        return

    msg_hard_decision = hard_decision[index[0]:index[1]]
    message_str = pp.bits_to_string(msg_hard_decision[0:-256])
    mac_received = pp.binary_list_to_hex(msg_hard_decision[-256:])
    mac_expected = hmac.new(
        conf.MAC_KEY.encode('utf-8'),
        msg=message_str.encode('utf-8'),
        digestmod='sha256'
    ).hexdigest()

    integrity = (mac_received == mac_expected)
    snr_window = SNR[index[0]+10:index[1]-10]
    snr_mean = float(np.nanmean(snr_window))

    print(f"[Frame {i}] Message: {message_str}")
    print(f"[Frame {i}] Received MAC: {mac_received}")
    print(f"[Frame {i}] Expected MAC: {mac_expected}")
    print(f"[Frame {i}] Integrity: {'Good' if integrity else 'Bad'}")
    print(f"[Frame {i}] SNR: {snr_mean}")

    insert = {
        'SNR': snr_mean,
        'MAC': mac_received,
        'message': message_str,
        'integrity': integrity,
        'time': time.time(),
        'config': copy.deepcopy(conf.config)
    }
    collection.insert_one(insert)



def tx(conf:src.CONFIG, ROLE:str, phase:int = 2):
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
    if src.MQTT_TX(conf=conf, role=ROLE, phase=phase, verbose=1).wait_for_all_ready(sleep_time=1.5):
        for i in range(10):
            tx.send_waveform(fsk_signal)
            time.sleep(0.1)
        return True
    else:
        print("failed synchronization")
        return False






conf = src.CONFIG()

if conf.connectionString is None:
    print("No connection string provided")
    exit(1)

if conf.MQTT is None:
    print("No MQTT broker provided")
    exit(1)


rx = src.RX(role=ROLE,conf=conf)
myclient = pymongo.MongoClient(conf.connectionString)
demod = src.rx.Demodulation(conf=conf)

mydb = myclient["MAC_1D"]

while True:
    phase = 1
    file = record(conf=conf, ROLE=ROLE, phase=phase)
    if file is None:
        continue
    pp = src.PostProcessing(file=file, conf=conf, demod=demod, role=ROLE, plot=0)
    if pp.check():
        print("Recording is correct")
        with ProcessPoolExecutor() as executor:
            executor.map(process_frame, range(len(pp.Frames)))

    phase = 2
    
    if not tx(conf=conf, ROLE=ROLE, phase=phase):
        print(f"failed synchronization {ROLE}, phase_{phase}")
        continue



