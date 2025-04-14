# %%
ROLE = "Destination"
import paho.mqtt.client as mqtt
import time
import numpy as np
import matplotlib.pyplot as plt
import hmac
import pymongo
import pymongo.collection
import copy
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






conf = src.CONFIG()

if conf.connectionString is None:
    print("No connection string provided")
    exit(1)

if conf.MQTT is None:
    print("No MQTT broker provided")
    exit(1)


rx = src.RX(role=ROLE,conf=conf)

demod = src.rx.Demodulation(conf=conf)



while True:
    phase = 1
    file = record(conf=conf, ROLE=ROLE, phase=1)
    if file is None: 
        continue
    pp = src.PostProcessing(file=file, conf=conf, demod=demod, role=ROLE, plot=0)
    if pp.check():
        # for i in range(len(pp.Frames)):
        #     process_frame(i)
        print("Recording is correct")
        with ProcessPoolExecutor() as executor:
            executor.map(process_frame, range(len(pp.Frames)))

    phase = 2
    file = record(conf=conf, ROLE=ROLE, phase=2)
    if file is None:
        continue
    pp = src.PostProcessing(file=file, conf=conf, demod=demod, role=ROLE, plot=0)
    if pp.check():
        print("Recording is correct")
        with ProcessPoolExecutor() as executor:
            executor.map(process_frame, range(len(pp.Frames)))



