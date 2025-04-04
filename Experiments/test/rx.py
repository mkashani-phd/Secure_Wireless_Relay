import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))
import src

import matplotlib.pyplot as plt
import pymongo.collection
import numpy as np
import datetime
import copy
import bson

def push_to_db( collection: pymongo.collection.Collection, conf:src.config.CONFIG , demod:src.Demodulation , pp:src.PostProcessing ):
        for indx in range(len(pp.TotalFramesIndex)):
            print("\nProcessing frame: ", indx)

            insert_data = copy.deepcopy(conf.config)
            insert_data["TIME"] =  datetime.datetime.now()

            frame = pp.frameByNumber(indx)

            # I = np.array(np.real(frame)).tobytes()
            # Q = np.array(np.imag(frame)).tobytes()
            # insert_data['I'], insert_data['Q'] = bson.binary.Binary(I), bson.binary.Binary(Q)
            # insert_data['frame_dtype'] = 'float'
            # insert_data['frame_shape'] = list(frame.shape)
 

            
            # calculate the frame power avoiding the preamble
            payload = frame[int(len(conf.PREAMBLE)*conf.PREAMBLE_REPEAT*conf.TX_SPS * 1.2) : int(-1*len(conf.PREAMBLE)*conf.PREAMBLE_REPEAT*conf.TX_SPS * 1.2)]
            if len(payload) == 0:
                print("problem with the frame")
                continue
            # 


            hard_decision,rs, SNR = demod.decode(frame)
            insert_data['SNR'] = np.average(SNR)
            print("SNR: ", insert_data['SNR'])
            
            index = demod.detect_message_indices(received=list(hard_decision), preamble=conf.PREAMBLE, repeat=conf.PREAMBLE_REPEAT)
            if index[0] is None or index[1] is None:
                print("preamble not found!")
                insert_data['error'] = 'premable not found!'
                collection.insert_one(insert_data)
                continue


            msg_hard_decision = hard_decision[index[0]:index[1]]
            Successive_Cancellation_llr = demod.successive_cancellation(hard_decision, rs, index)
            try:
                mac = cc.decode_LDPC(Successive_Cancellation_llr, message_length=256)
            except:
                # it is the message from the realy with no superposition
                # the MAC is the last 256 bits of the message
                mac = hard_decision[-256:]
                # msg_hard_decision = hard_decision[:-256]
            

            insert_data['msg_hard_decision'] = pp.bits_to_string(msg_hard_decision)
            print("msg: ", insert_data['msg_hard_decision'])

            if mac is None:
                print("ldpc decoding failed!")
                insert_data['error'] = 'ldpc decoding failed!'
                collection.insert_one(insert_data)
                continue
            insert_data['rceived_mac_ldpc_hex'] = pp.binary_list_to_hex(mac)
            insert_data['ldpc_success_verification'] = insert_data['rceived_mac_ldpc_hex'] == '3776b3b21e2b54891a0731a27165ff9fbfed670657998d1d37acec5b41daedb2'
            
            print('')
            print(insert_data['rceived_mac_ldpc_hex'])
            print(insert_data['rceived_mac_ldpc_hex'] == '3776b3b21e2b54891a0731a27165ff9fbfed670657998d1d37acec5b41daedb2')

            print('')

            collection.insert_one(insert_data)



        print("\nData pushed to the database ...")

### tests
def test():

    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    mydb = myclient["MAC_SUPERPOSITION"]

    conf = config.CONFIG()
    rx = RX(conf=conf, Role="Destination")
    files = rx.record()

    demod = Demodulation()
    pp = PostProcessing(file=files, conf=rx.conf, demod=demod)

    if(pp.check()):
        push_to_db(collection = mydb['1D_SC'], conf=rx.conf, demod=demod, pp=pp)

