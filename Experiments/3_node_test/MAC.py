
import os,time, pymongo ,copy
import pymongo.collection
import matplotlib.pyplot as plt
import numpy as np
import hmac
import tensorflow as tf

from tensorflow.keras import backend
import gc

import concurrent.futures
from concurrent.futures import ProcessPoolExecutor


import sys
import os

import src.channelCoding
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

import src
import src.utils as utils
from src import encryption_config
import src.encryption_config
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

        if len(self.payload) < self.conf.MSG_SIZE:
            raise ValueError(f"Payload size {len(self.payload)} is smaller than the configured MSG_SIZE {self.conf.MSG_SIZE}")
        else:
            self.payload = self.payload[0:self.conf.MSG_SIZE]
        
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

        self.payload = src.channelCoding.encode_LDPC(self.payload, np.ceil(len(self.payload)/self.conf.MSG_CODE_RATE))
        self.MAC_bits = src.channelCoding.encode_LDPC(self.MAC_bits, np.ceil(len(self.MAC_bits)/self.conf.MSG_CODE_RATE))
        self.fsk_signal = self.tx.fsk_modulate(np.concatenate([self.payload, self.MAC_bits]), # sends with half the power,
                # mac = self.encoded_MAC,
                # alpha = self.conf.ALPHA,
                sps = self.conf.TX_SPS, 
                preamble = np.concatenate([ [0 for _ in range(10000//self.conf.TX_SPS)] , self.conf.PREAMBLE]), 
                postamble = np.concatenate([self.conf.POSTAMBLE, [0 for _ in range(1000//self.conf.TX_SPS)]]),
                scale = self.conf.TX_PAYLOAD_POWER_SCALE, # send the payload with half the power of the preamble
                )
        

class MAC_TX_SC(MAC_TX):
    def __init__(self, ROLE:str, conf: Optional[src.CONFIG] = None, Encryption:src.encryption_config.ENC_CONFIG = None):
        super().__init__(ROLE, conf)
        self._Encryption = Encryption

        if ROLE == "source":
            print(self.conf.MAC_SIZE_ENCODED)

            if self._Encryption is not None:
                self.payload = src.channelCoding.encode_LDPC(utils.string_to_bits(self._Encryption.PAYLOAD), int(np.ceil(len(self.payload)/self.conf.MSG_CODE_RATE)))
                print("Payload length", len(self.payload))
                hex_rand, _ = src.AESCTRAligned.get_range(
                                                            key = bytes.fromhex(self._Encryption.KEY),
                                                            iv = bytes.fromhex(self._Encryption.IV),
                                                            chunk_bits=len(self.payload),
                                                            index=self._Encryption.COUNTER,
                                                            return_int=False)
                
                
                self._Encryption.update_config(['COUNTER', self._Encryption.COUNTER+1])
                self.encoded_MAC = utils.hex_to_bits(hex_rand.hex())



            else:

                self.payload = src.channelCoding.encode_LDPC(self.payload, self.conf.MAC_SIZE_ENCODED)

                self.encoded_MAC = src.channelCoding.encode_LDPC(self.MAC_bits, int(len(self.MAC_bits)/self.conf.MAC_LDPC))
                self.encoded_MAC = np.repeat(self.encoded_MAC, 1/self.conf.MAC_REP)
            

            if len(self.payload) != len(self.encoded_MAC):
                raise ValueError(f"Payload size {len(self.payload)} is not equal to the MAC size {len(self.encoded_MAC)}")
            
            self.fsk_signal = self.tx.fsk_modulate(self.payload, # sends with half the power,
                    mac = self.encoded_MAC,
                    alpha = self.conf.ALPHA if self._Encryption is None else 0.5,
                    sps = self.conf.TX_SPS, 
                    preamble = np.concatenate([ [0 for _ in range(10000//self.conf.TX_SPS)] , self.conf.PREAMBLE]), 
                    postamble = np.concatenate([ self.conf.POSTAMBLE, [0 for _ in range(1000//self.conf.TX_SPS)]]),
                    scale = self.conf.TX_PAYLOAD_POWER_SCALE, # send the payload with half the power of the preamble
                    )
            

            

            # self.fsk_signal = self.tx.fsk_modulate(np.zeros_like(self.encoded_MAC), # sends with half the power,
            #         mac = self.encoded_MAC,
            #         alpha = self.conf.ALPHA,
            #         sps = self.conf.TX_SPS, 
            #         preamble = np.concatenate([ [0 for _ in range(10000//self.conf.TX_SPS)] , self.conf.PREAMBLE]), 
            #         postamble = np.concatenate([ self.conf.POSTAMBLE, [0 for _ in range(1000//self.conf.TX_SPS)]]),
            #         scale = self.conf.TX_PAYLOAD_POWER_SCALE, # send the payload with half the power of the preamble
            #         )
        else:
            self.payload = src.channelCoding.encode_LDPC(self.payload, self.conf.MAC_SIZE_ENCODED)

            self.fsk_signal = self.tx.fsk_modulate(self.payload, # sends with half the power,
                    # mac = self.encoded_MAC,
                    # alpha = self.conf.ALPHA,
                    sps = self.conf.TX_SPS, 
                    preamble = np.concatenate([ [0 for _ in range(10000//self.conf.TX_SPS)] , self.conf.PREAMBLE]), 
                    postamble = np.concatenate([self.conf.POSTAMBLE, [0 for _ in range(1000//self.conf.TX_SPS)]]),
                    scale = self.conf.TX_PAYLOAD_POWER_SCALE, # send the payload with half the power of the preamble
                    )
        




class MAC_RX(MAC):
    def __init__(self, ROLE:str, conf: Optional[src.CONFIG] = None):
        super().__init__(ROLE, conf)
        self.demod = src.rx.Demodulation(conf=self.conf)
        self.rx = src.RX(role=ROLE, conf=self.conf)
        self.msg = None
        self.tag = None
       
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
        hard_decision, rs, llr = self.demod.decode(frame)
    
        index = self.demod.detect_message_indices(
            received=list(hard_decision),
            preamble=self.conf.PREAMBLE,
            postamble=self.conf.POSTAMBLE,
            repeat=self.conf.PREAMBLE_REPEAT
        )


        snr_lin, sigma_n2 = self.demod.get_SNR(frame_raw=frame[index[0]*self.conf.WINDOW:index[1]*self.conf.WINDOW], noise_raw=self.pp.IQsamples[index[0]*self.conf.WINDOW:index[1]*self.conf.WINDOW], dB=False)

        if index[0] is None or index[1] is None:
            print(f"[Frame {i}] No preamble detected!")
            return None

        msg_hard_decision = hard_decision[index[0]:index[1]]


        r0 ,r1 = rs
        r0 =        r0[index[0]:index[1]]
        r1 =        r1[index[0]:index[1]]
   

        return msg_hard_decision, llr[index[0]:index[1]], [r0, r1],snr_lin, sigma_n2

    def process_frame(self, i, phase:int = 1):

        msg_hard_decision, llr, rs, snr_lin, sigma_n2 = self.primary_process(i)
        pass


    def process_all_frames(self, file, phase:int = 1):
        self.pp = src.PostProcessing(file=file, conf=self.conf, demod=self.demod, role=self.ROLE, plot=False)
        if self.pp.check():
            print("Recording is correct")
            # with ProcessPoolExecutor() as executor:
            #     executor.map(lambda args: self.process_frame(*args), zip(range(len(self.pp.Frames)), [phase]*len(self.pp.Frames)))
            
            
            # with concurrent.futures.ThreadPoolExecutor() as executor:
            #     executor.map(lambda args: self.process_frame(*args), zip(range(len(self.pp.Frames)), [phase]*len(self.pp.Frames)))
        
            for i in range(len(self.pp.Frames)):
                
                self.process_frame(i, phase)
                




class MAC_RX_1D(MAC_RX):


    def __init__(self, ROLE:str, conf: Optional[src.CONFIG] = None):
        super().__init__(ROLE, conf)
        m = utils.string_to_bits(self.conf.PAYLOAD)
        self.msg = src.channelCoding.encode_LDPC(m, int(np.round(len(m)/self.conf.MSG_CODE_RATE)))
        self.msg = np.array(self.msg)
        self.tag_hex = hmac.new(self.conf.MAC_KEY.encode(), self.conf.PAYLOAD.encode(), 'sha256').hexdigest()
        n = utils.hex_to_bits(self.tag_hex)
        self.tag = src.channelCoding.encode_LDPC(n, int(np.round(len(n)/self.conf.MSG_CODE_RATE)))
        self.tag = np.array(self.tag)




    def process_frame(self, i, phase:int = 1):
        # try:
        msg_hard_decision, llr, rs, snr_lin, sigma_n2 = self.primary_process(i)
        # except:
        #     return None

        myclient = pymongo.MongoClient(self.conf.connectionString)
        mydb = myclient[f"{self.conf.MongoDB_Collection_name}_1D_R={np.round(self.conf.MSG_CODE_RATE,3)}".replace(".", "_")]
        collection=mydb[f'{self.ROLE}, phase_{phase}']
        

        
        MAC_encoded_size = int(np.ceil(self.conf.TAG_SIZE//self.conf.MSG_CODE_RATE))



        llr_msg = tf.constant(llr[:-1*MAC_encoded_size], dtype=tf.float32)   # shape (N,)
        llr_mac = tf.constant(llr[-1*MAC_encoded_size:], dtype=tf.float32)   # shape (N,)



        msg_LDPC = src.channelCoding.decode_LDPC(codeword_llr=-1*llr_msg, message_length=self.conf.MSG_SIZE)
        mac_LDPC = src.channelCoding.decode_LDPC(codeword_llr=-1*llr_mac, message_length=self.conf.TAG_SIZE)



        message_str = utils.bits_to_string(msg_LDPC)
        mac_hex = utils.bits_to_hex(mac_LDPC)
    


        m_hat = np.array(llr[:-1*MAC_encoded_size])>0
        n_hat = np.array(llr[-1*MAC_encoded_size:])>0



        # Count errors
        errors_n = np.sum(self.tag != n_hat)
        errors_m = np.sum(self.msg != np.array(m_hat))

        # BER
        ber_n = errors_n / len(self.tag)
        ber_m = errors_m / len(self.msg)


        insert = {
            'Decoded_tag_success': self.tag_hex == mac_hex,
            'Decoded_msg_success': message_str == self.conf.PAYLOAD,
            'BER_msg': ber_m,
            'BER_tag': ber_n,
            'message_hard_desicion': msg_hard_decision,
            'SNR': snr_lin,
            'sigma_n2' : sigma_n2,
            'message': message_str,
            'MAC': mac_hex,
            'time': time.time(),
            'r0': list(map(float, rs[0])),
            'r1': list(map(float, rs[1])),
            'llr': list(map(float, llr)),
            'decoded_phase_2': False,
            'config': copy.deepcopy(self.conf.config)
        }


        print(f"[Frame {i}] Message: {message_str}")
        print(f"[Frame {i}] MAC: ", mac_hex)
        print(f"[Frame {i}] SNR: {10*np.log10(snr_lin)}")
        print(f"[Frame {i}] BER_m, BER_n: {ber_m}, {ber_n}")
        print(f"[Frame {i}] Message: \033[92mGood\033[0m" if message_str == self.conf.PAYLOAD else f"[Frame {i}] Message: \033[91mBad\033[0m")
        print(f"[Frame {i}] Tag: \033[92mGood\033[0m" if self.tag_hex == mac_hex else f"[Frame {i}] Tag: \033[91mBad\033[0m")



        collection.insert_one(insert)

        #remove from GPU memory
        r0_mac = r0_mac = llr_mac=  r0_msg = r1_msg = r1_mac = msg_LDPC = mac_LDPC = None
        backend.clear_session()
        gc.collect()

class MAC_RX_SC(MAC_RX):
    def __init__(self, ROLE:str, conf: Optional[src.CONFIG] = None):
        super().__init__(ROLE, conf)
        self.enc_conf = src.encryption_config.ENC_CONFIG()

        m = utils.string_to_bits(self.conf.PAYLOAD)
        self.msg = src.channelCoding.encode_LDPC(m,self.conf.MAC_SIZE_ENCODED)
        self.msg = np.array(self.msg)

        self.tag_hex = hmac.new(self.conf.MAC_KEY.encode(), self.conf.PAYLOAD.encode(), 'sha256').hexdigest()
        n = utils.hex_to_bits(self.tag_hex)
        self.tag_LDPC = src.channelCoding.encode_LDPC(n, int(np.round(len(n)/self.conf.MAC_LDPC)))
        self.tag_REP = np.repeat(self.tag_LDPC, int(np.round(1/self.conf.MAC_REP)))
        self.tag = np.array(self.tag_REP)



    def process_frame(self, i, phase:int = 1):
        myclient = pymongo.MongoClient(self.conf.connectionString)
        mydb = myclient[f"{self.conf.MongoDB_Collection_name}_SC_alpha_{self.conf.ALPHA}_R={np.round(self.conf.MSG_CODE_RATE,3)}_Encryption".replace(".", "_")]
        collection=mydb[f'{self.ROLE}, phase_{phase}']

        if self.ROLE == "relay":
            try:
               msg_hard_decision, llr, rs, snr_lin, sigma_n2 = self.primary_process(i)
            except:
                return None
            
            # errors_m = np.sum(self.msg != np.array(msg_hard_decision))


            # ber_m = errors_m / len(self.msg)

            r0 ,r1  = rs

            insert = {
                'time_stamp': time.time(),
                'r0': list(r0),
                'r1': list(r1),
                # 'BER_msg': ber_m,
                'SNR': 10*np.log10(snr_lin),
                'sigma_n2': sigma_n2,
                'config': copy.deepcopy(self.conf.config),
                'enc_conf': copy.deepcopy(self.enc_conf.enc_config),
            }

            print(f"[Frame {i}] SNR: {10*np.log10(snr_lin)}")
            print(f"[Frame {i}] ENC COUNTER: {self.enc_conf.COUNTER}")

            # print(f"[Frame {i}] BER_m:  {np.round(ber_m,5)}")
            collection.insert_one(insert)
            return


            r0 ,r1  = rs
            r0_msg = tf.constant(r0, dtype=tf.float32)   # shape (N,)
            r1_msg = tf.constant(r1, dtype=tf.float32)
            llr_msg = tf.math.log(r0_msg / r1_msg)
            

            msg_LDPC = src.channelCoding.decode_LDPC(codeword_llr=llr_msg, message_length=self.conf.MSG_SIZE)
            message_str = utils.bits_to_string(msg_LDPC)


            print(f"[Frame {i}] Message: {message_str}")
            print(f"[Frame {i}] SNR: {10*np.log10(snr_lin)}")
            print(f"[Frame {i}] Correctly decode message at relay: \033[92mGood\033[0m" if message_str == self.conf.PAYLOAD else f"Correctly decode message at relay: \033[91mBad\033[0m")

            insert = {
                'Correctly decode message at relay':message_str == self.conf.PAYLOAD,
                'SNR': snr_lin,
                'sigma_n2': sigma_n2,
                'message': message_str,
                'message_hard': utils.bits_to_string(msg_hard_decision),
                'time': time.time(),
                'config': copy.deepcopy(self.conf.config)
            }
            collection.insert_one(insert)
            return
        
        else:
            if phase == 1:
                try:
                    msg_hard_decision, llr, rs, snr_lin, sigma_n2 = self.primary_process(i)
                except:
                    return None






                
                r0 ,r1 = rs
                # r0_msg = tf.constant(r0, dtype=tf.float32)   # shape (N,)
                # r1_msg = tf.constant(r1, dtype=tf.float32)
                # llr_msg = tf.math.log(r0_msg / r1_msg)
                # msg_LDPC = src.channelCoding.decode_LDPC(codeword_llr=llr_msg, message_length=self.conf.MSG_SIZE)
                # message_str = utils.bits_to_string(msg_LDPC)



                #################################################
                # n_hat_llr = self.demod.successive_cancellation(msg_decoded_bits=msg_hard_decision, rs=rs, snr_linear=snr_lin)
                # n_hat = n_hat_llr <0
                # n_hat_llr = n_hat_llr.reshape(-1, int(np.round(1/self.conf.MAC_REP))).sum(axis=1)/5
                # tag_LDPC = n_hat_llr.copy()

                # plt.figure(figsize=(10,5), dpi=100)
                # plt.stem(n_hat_llr[0:100])
                # plt.stem(np.repeat(n_hat_llr/2, 10)[0:100], 'r')
                # plt.show()
                #############################################################

                n_hat = self.demod.joint_detection(llrs= llr , snr_linear=snr_lin, plot=False)
                # errors_n = np.sum(self.tag != n_hat)
                # errors_m = np.sum(self.msg != np.array(msg_hard_decision))

                # ber_n = errors_n / len(n_hat)
                # ber_m = errors_m / len(n_hat)


                insert = {
                    'time_stamp': time.time(),
                    'BER_tag': 0,
                    'BER_msg': 0,
                    'r0':  list(r0),
                    'r1':  list(r1),
                    'SNR': 10*np.log10(snr_lin),
                    'sigma_n2': sigma_n2,
                    'config': copy.deepcopy(self.conf.config),
                    'enc_conf': copy.deepcopy(self.enc_conf.enc_config)
                }

                print(f"[Frame {i}] SNR: {10*np.log10(snr_lin)}")
                # print(f"[Frame {i}] BER_n:  {np.round(ber_n,5)}")
                # print(f"[Frame {i}] BER_m:  {np.round(ber_m,5)}")
                print(f"[Frame {i}] ENC_COUNTER: {self.enc_conf.COUNTER}")
               

                collection.insert_one(insert)
                return


                n_hat_llr = np.array([-2.5 if i==1 else 2.5 for i in n_hat])
                n_hat_llr = n_hat_llr.reshape(-1,int(np.round(1/self.conf.MAC_REP))).sum(axis=1)
                tag_LDPC =  n_hat_llr
                n_hat_llr_tf = tf.constant(n_hat_llr, dtype=tf.float32)
                mac_decoded = src.channelCoding.decode_LDPC(n_hat_llr_tf, message_length=self.conf.TAG_SIZE)
                mac_hex = utils.bits_to_hex(mac_decoded) 

                # plt.figure(figsize=(10,5), dpi=100)
                # plt.stem(n_hat_llr[0:100])
                # n_hat = n_hat_llr <0
                # # n_hat_llr = np.array([-5 if i else 5 for i in n_hat])
                # n_hat_llr = n_hat_llr.reshape(-1, 10).sum(axis=1)/5

                # plt.figure(figsize=(10,5), dpi=100)
                # plt.stem((n_hat[0:100]-.5)*5)
                # plt.stem(np.repeat(-1*n_hat_llr/2, int(np.round(1/self.conf.MAC_REP)))[0:100], 'r')
                # plt.show()
                ############################################################


         
                
                




                # Count errors
                errors_n = np.sum(self.tag != n_hat)                
                error_n_after_repetitioncode = np.sum((tag_LDPC<0) != self.tag_LDPC)
                error_n_after_LDPC = np.sum(mac_decoded != utils.hex_to_bits(self.tag_hex))

                errors_m = np.sum(self.msg != np.array(msg_hard_decision))
                total_bits = len(self.msg)

                # print(list(tag_LDPC),list(self.tag_LDPC ))
                # BER
                
                ber_n = errors_n / total_bits
                ber_n_after_rep = error_n_after_repetitioncode/ len(tag_LDPC)
                ber_n_after_LDPC = error_n_after_LDPC/ len(utils.hex_to_bits(self.tag_hex))

                ber_m = errors_m / total_bits


                insert = {
                    'Decoded_tag_success': self.tag_hex == mac_hex,
                    'Decoded_msg_success': message_str == self.conf.PAYLOAD,
                    'BER_msg': ber_m,
                    'BER_tag': ber_n,
                    'ber_t_after_rep': ber_n_after_rep,
                    'message_hard_desicion': msg_hard_decision,
                    'SNR': snr_lin,
                    'sigma_n2':sigma_n2,
                    'message': message_str,
                    'MAC': mac_hex,
                    'time': time.time(),
                    'r0': list(map(float, rs[0])),
                    'r1': list(map(float, rs[1])),
                    'llr': list(map(float, llr)),
                    'decoded_phase_2': False,
                    'config': copy.deepcopy(self.conf.config)
                }


                print(f"[Frame {i}] Message: {message_str}")
                print(f"[Frame {i}] MAC: ", mac_hex)
                print(f"[Frame {i}] SNR: {snr_lin}")
                print(f"[Frame {i}] BER_m, BER_n, BER_n_afer_rep, BER_n_afer_LDPC,: {np.round(ber_m,5)}, {np.round(ber_n,5)}, {np.round(ber_n_after_rep,5)}, {np.round(ber_n_after_LDPC,5)}")
                print(f"[Frame {i}] Message: \033[92mGood\033[0m" if message_str == self.conf.PAYLOAD else f"[Frame {i}] Message: \033[91mBad\033[0m")
                print(f"[Frame {i}] Tag: \033[92mGood\033[0m" if self.tag_hex == mac_hex else f"[Frame {i}] Tag: \033[91mBad\033[0m")
                collection.insert_one(insert)
                return
                # except:
                #     return None

            elif phase == 2:

                # collection_phase1 = mydb[f'{self.ROLE}, phase_1']
                # doc = collection_phase1.find_one_and_update(
                #                                     {'decoded_phase_2': False},
                #                                     {'$set': {'decoded_phase_2': True}},
                #                                     sort=[('_id', -1)]  # Sort by _id descending (latest first)
                #                                 )

                # if doc is None:
                #     insert = {'error': 'No phase 1 document found!'}
                #     print(f"[Frame {i}] \033[91mError\033[0m: No phase 1 document found!")
                #     collection.insert_one(insert)
                #     return
                

                # mydb = myclient[f"{self.conf.MongoDB_Collection_name}_SC_R={np.round(self.conf.MSG_CODE_RATE,3)}".replace(".", "_")]
                # collection=mydb[f'{self.ROLE}, phase_{phase}']
                # try:
                #     msg_hard_decision, snr_mean, rs = self.primary_process(i)
                # except:
                #     return None
                
                # r0 ,r1, _ = rs
                # r0_msg = tf.constant(r0, dtype=tf.float32)   # shape (N,)
                # r1_msg = tf.constant(r1, dtype=tf.float32)
                # llr_msg = tf.math.log(r0_msg / r1_msg)

                # msg_LDPC = src.channelCoding.decode_LDPC(codeword_llr=llr_msg, message_length=self.conf.MSG_SIZE)
                # message_str = utils.bits_to_string(msg_LDPC)
                
                # rs = [doc['r0'], doc['r1'], doc['r_half']]
                # doc['decoded_phase_2'] = True
                # collection_phase1.update_one({'_id': doc['_id']}, {'$set': doc})
                # try:
                #     msg_encoded = src.channelCoding.encode_LDPC(msg_LDPC, self.conf.MAC_SIZE_ENCODED)
                #     Successive_Cancellation_llr = self.demod.successive_cancellation(msg_encoded, rs)
                #     Successive_Cancellation_llr = tf.constant(Successive_Cancellation_llr, dtype=tf.float32)
                # except:
                #     insert = {'error': 'successive cancellation failed!'}
                #     print(f"[Frame {i}] \033[91mError\033[0m: successive cancellation failed!")
                #     collection.insert_one(insert)
                #     return
                # try:
                #     mac = src.channelCoding.decode_LDPC(Successive_Cancellation_llr, message_length=self.conf.TAG_SIZE*3)

                #     llr_inner = [-10 if i else 10 for i in mac]
                #     llr_inner = tf.constant(llr_inner, dtype=tf.float32)
                #     mac = src.channelCoding.decode_LDPC(llr_inner, message_length=self.conf.TAG_SIZE)
                #     mac_hex = utils.bits_to_hex(mac)
                # except:
                #     insert = {'error': 'ldpc decoding failed!'}
                #     print(f"[Frame {i}] \033[91mError\033[0m: ldpc decoding failed!")
                #     collection.insert_one(insert)
                #     return

                # if mac is not None:
                #     expected_mac = hmac.new(
                #                             self.conf.MAC_KEY.encode('utf-8'),
                #                             msg=message_str.encode('utf-8'),
                #                             digestmod='sha256'
                #                         ).hexdigest()

                #     insert = {
                #         'phase1_document_id': doc['_id'],
                #         'SNR': snr_mean,
                #         'MAC': mac_hex,
                #         'message': message_str,
                #         'message_hard': utils.bits_to_string(msg_hard_decision),
                #         'integrity': expected_mac == mac_hex,
                #         'time': time.time(),
                #         'config': copy.deepcopy(self.conf.config),
                #     }

                #     print(f"[Frame {i}] Message: {message_str}")
                #     print(f"[Frame {i}] Received MAC: {mac_hex}")
                #     print(f"[Frame {i}] Expected MAC: {expected_mac}")
                #     print(f"[Frame {i}] Integrity: \033[92mGood\033[0m" if expected_mac == mac_hex else f"\033[91mBad\033[0m")
                #     print(f"[Frame {i}] SNR: {np.round(snr_mean,2)}, Phase1 SNR: {np.round(doc['SNR'],2)}")

                #     collection.insert_one(insert)
                    return

        









    