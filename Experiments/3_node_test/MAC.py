
import os,time, pymongo ,copy
import pymongo.collection
import matplotlib.pyplot as plt
import numpy as np
import hmac

import concurrent.futures
from concurrent.futures import ProcessPoolExecutor


import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

import src
import src.utils as utils
import src.channelCoding as cc
from typing import Optional






class MAC():
    def __init__(self, ROLE:str, conf: Optional[src.CONFIG] = None):
        self.ROLE = ROLE
        self.conf = src.CONFIG() if conf is None else conf
    def reload_config(self):
        self.conf = src.CONFIG()



class MAC_TX(MAC):
    def __init__(self, ROLE:str, conf: Optional[src.CONFIG] = None):
        super().__init__(ROLE, conf)
        self.payload = utils.string_to_bits(self.conf.PAYLOAD)
        self.MAC_bits = utils.hex_to_bits(hmac.new(self.conf.MAC_KEY.encode(), self.conf.PAYLOAD.encode(), 'sha256').hexdigest())
        self.tx = src.TX(role=ROLE, conf=self.conf)

        self.fsk_signal = None

    def transmit(self):
        phase = 1 if self.ROLE == "source" else 2
        if src.MQTT_TX(conf=self.conf, role=self.ROLE, phase=phase, verbose=1).wait_for_all_ready(sleep_time=1):
            for i in range(self.conf.TX_REPEAT):
                self.tx.send_waveform(self.fsk_signal)
                time.sleep(0.1)
            return True
        else:
            print("failed synchronization")
            return False


class MAC_TX_1D(MAC_TX):
    def __init__(self, ROLE:str, conf: Optional[src.CONFIG] = None):
        super().__init__(ROLE, conf)
        if ROLE != "source":
            raise ValueError("ROLE must be source for MAC_TX_1D")
            
        self.fsk_signal = self.tx.fsk_modulate(np.concatenate([self.payload, self.MAC_bits]), # sends with half the power,
                # mac = self.encoded_MAC,
                # alpha = self.conf.ALPHA,
                sps = self.conf.TX_SPS, 
                preamble = np.concatenate([ [0 for _ in range(1000//self.conf.TX_SPS)] , self.conf.PREAMBLE]), 
                postamble = np.concatenate([self.conf.POSTAMBLE, [0 for _ in range(1000//self.conf.TX_SPS)]]),
                scale = conf.TX_PAYLOAD_POWER_SCALE, # send the payload with half the power of the preamble
                )
        

class MAC_TX_SC(MAC_TX):
    def __init__(self, ROLE:str, conf: Optional[src.CONFIG] = None):
        super().__init__(ROLE, conf)


        if ROLE == "source":
            self.encoded_MAC = cc.encode_LDPC(self.MAC_bits, 2048)

            self.fsk_signal = self.tx.fsk_modulate(self.payload, # sends with half the power,
                    mac = self.encoded_MAC,
                    alpha = self.conf.ALPHA,
                    sps = self.conf.TX_SPS, 
                    preamble = np.concatenate([ [0 for _ in range(1000//self.conf.TX_SPS)] , self.conf.PREAMBLE]), 
                    postamble = np.concatenate([ self.conf.POSTAMBLE, [0 for _ in range(1000//self.conf.TX_SPS)]]),
                    scale = self.conf.TX_PAYLOAD_POWER_SCALE, # send the payload with half the power of the preamble
                    )
        else:
            self.fsk_signal = self.tx.fsk_modulate(self.payload, # sends with half the power,
                    # mac = self.encoded_MAC,
                    # alpha = self.conf.ALPHA,
                    sps = self.conf.TX_SPS, 
                    preamble = np.concatenate([ [0 for _ in range(1000//self.conf.TX_SPS)] , self.conf.PREAMBLE]), 
                    postamble = np.concatenate([self.conf.POSTAMBLE, [0 for _ in range(1000//self.conf.TX_SPS)]]),
                    scale = self.conf.TX_PAYLOAD_POWER_SCALE, # send the payload with half the power of the preamble
                    )
        




class MAC_RX(MAC):
    def __init__(self, ROLE:str, conf: Optional[src.CONFIG] = None):
        super().__init__(ROLE, conf)
        self.demod = src.rx.Demodulation(conf=self.conf)
        self.rx = src.RX(role=ROLE, conf=self.conf)
        self.pp = None

    def record(self, phase:int = 1):
        if src.MQTT_RX(conf=self.conf, role=self.ROLE, phase=phase, verbose=1).send_ready_and_wait_for_begin():
            file = self.rx.record()
            return file
        else:
            print("failed synchronization")
            return None
        
    def primary_process(self, i):
        frame = self.pp.frameByNumber(i)
        hard_decision, rs, SNR = self.demod.decode(frame)
        index = self.demod.detect_message_indices(
            received=list(hard_decision),
            preamble=self.conf.PREAMBLE,
            postamble=self.conf.POSTAMBLE,
            repeat=self.conf.PREAMBLE_REPEAT
        )

        if index[0] is None or index[1] is None:
            print(f"[Frame {i}] No preamble detected!")
            return None

        msg_hard_decision = hard_decision[index[0]:index[1]]
        snr_window = SNR[index[0]+10:index[1]-10]
        snr_mean = float(np.nanmean(snr_window))

        r0 ,r1, r_half = rs
        r0 =        r0[index[0]:index[1]]
        r1 =        r1[index[0]:index[1]]
        r_half =    r_half[index[0]:index[1]]

        return msg_hard_decision, snr_mean, [r0, r1, r_half]

    def process_frame(self, i, phase:int = 1):
        msg_hard_decision, snr_mean, rs = self.primary_process(i)
        pass


    def process_all_frames(self, file, phase:int = 1):
        self.pp = src.PostProcessing(file=file, conf=self.conf, demod=self.demod, role=self.ROLE, plot=False)
        if self.pp.check():
            print("Recording is correct")
            # with ProcessPoolExecutor() as executor:
            #     executor.map(lambda args: self.process_frame(*args), zip(range(len(self.pp.Frames)), [phase]*len(self.pp.Frames)))
            
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                executor.map(lambda args: self.process_frame(*args), zip(range(len(self.pp.Frames)), [phase]*len(self.pp.Frames)))
        
            # for i in range(len(self.pp.Frames)):
            #     self.process_frame(i, phase)




class MAC_RX_1D(MAC_RX):


    def __init__(self, ROLE:str, conf: Optional[src.CONFIG] = None):
        super().__init__(ROLE, conf)



    def process_frame(self, i, phase:int = 1):
        try:
            msg_hard_decision, snr_mean, rs = self.primary_process(i)
        except:
            return None

        myclient = pymongo.MongoClient(self.conf.connectionString)
        mydb = myclient["MAC_1D"]
        collection=mydb[f'{self.ROLE}, phase_{phase}']


        

        message_str = utils.bits_to_string(msg_hard_decision[0:-256])
        mac_received = utils.bits_to_hex(msg_hard_decision[-256:])
        mac_expected = hmac.new(
            self.conf.MAC_KEY.encode('utf-8'),
            msg=message_str.encode('utf-8'),
            digestmod='sha256'
        ).hexdigest()

        integrity = (mac_received == mac_expected)


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
            'config': copy.deepcopy(self.conf.config)
        }
        collection.insert_one(insert)

class MAC_RX_SC(MAC_RX):
    def __init__(self, ROLE:str, conf: Optional[src.CONFIG] = None):
        super().__init__(ROLE, conf)



    def process_frame(self, i, phase:int = 1):
        myclient = pymongo.MongoClient(self.conf.connectionString)
        mydb = myclient["MAC_SC"]
        collection=mydb[f'{self.ROLE}, phase_{phase}']

        if self.ROLE == "relay":
            try:
                msg_hard_decision, snr_mean, rs = self.primary_process(i)
            except:
                return None
            message_str = utils.bits_to_string(msg_hard_decision)


            print(f"[Frame {i}] Message: {message_str}")
            print(f"[Frame {i}] SNR: {snr_mean}")

            insert = {
                'SNR': snr_mean,
                'message': message_str,
                'time': time.time(),
                'config': copy.deepcopy(self.conf.config)
            }
            collection.insert_one(insert)
            return
        
        else:
            if phase == 1:
                try:
                    msg_hard_decision, snr_mean, rs = self.primary_process(i)
                except:
                    return None
                message_str = utils.bits_to_string(msg_hard_decision)

                insert = {
                    'SNR': snr_mean,
                    'message': message_str,
                    'time': time.time(),
                    'r0': list(map(float, rs[0])),
                    'r1': list(map(float, rs[1])),
                    'r_half': list(map(float, rs[2])),
                    'decoded_phase_2': False,
                    'config': copy.deepcopy(self.conf.config)
                }


                print(f"[Frame {i}] Message: {message_str}")
                print(f"[Frame {i}] SNR: {snr_mean}")
                collection.insert_one(insert)
                return

            elif phase == 2:

                collection_phase1 = mydb[f'{self.ROLE}, phase_1']
                doc = collection_phase1.find_one_and_update(
                                                    {'decoded_phase_2': False},
                                                    {'$set': {'decoded_phase_2': True}},
                                                    sort=[('_id', -1)]  # Sort by _id descending (latest first)
                                                )

                if doc is None:
                    insert = {'error': 'No phase 1 document found!'}
                    print(f"[Frame {i}] \033[91mError\033[0m: No phase 1 document found!")
                    collection.insert_one(insert)
                    return
                

                mydb = myclient["MAC_SC"]
                collection=mydb[f'{self.ROLE}, phase_{phase}']
                try:
                    msg_hard_decision, snr_mean, rs = self.primary_process(i)
                except:
                    return None
                message_str = utils.bits_to_string(msg_hard_decision)
                
                rs = [doc['r0'], doc['r1'], doc['r_half']]
                doc['decoded_phase_2'] = True
                collection_phase1.update_one({'_id': doc['_id']}, {'$set': doc})
                try:
                    Successive_Cancellation_llr = self.demod.successive_cancellation(msg_hard_decision, rs)
                except:
                    insert = {'error': 'successive cancellation failed!'}
                    print(f"[Frame {i}] \033[91mError\033[0m: successive cancellation failed!")
                    collection.insert_one(insert)
                    return
                try:
                    mac = cc.decode_LDPC(Successive_Cancellation_llr, message_length=256)
                    mac_hex = utils.bits_to_hex(mac)
                except:
                    insert = {'error': 'ldpc decoding failed!'}
                    print(f"[Frame {i}] \033[91mError\033[0m: ldpc decoding failed!")
                    collection.insert_one(insert)
                    return

                if mac is not None:
                    expected_mac = hmac.new(
                                            self.conf.MAC_KEY.encode('utf-8'),
                                            msg=message_str.encode('utf-8'),
                                            digestmod='sha256'
                                        ).hexdigest()

                    insert = {
                        'phase1_document_id': doc['_id'],
                        'SNR': snr_mean,
                        'MAC': mac_hex,
                        'message': message_str,
                        'integrity': expected_mac == mac_hex,
                        'time': time.time(),
                        'config': copy.deepcopy(self.conf.config),
                    }

                    print(f"[Frame {i}] Message: {message_str}")
                    print(f"[Frame {i}] Received MAC: {mac_hex}")
                    print(f"[Frame {i}] Expected MAC: {expected_mac}")
                    print(f"[Frame {i}] Integrity: \033[92mGood\033[0m" if expected_mac == mac_hex else f"\033[91mBad\033[0m")
                    print(f"[Frame {i}] SNR: {snr_mean}")

                    collection.insert_one(insert)
                    return

        









    