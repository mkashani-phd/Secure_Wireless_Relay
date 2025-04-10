import unittest
import src
import numpy as np
import hmac
import matplotlib.pyplot as plt
import threading
import time

class PhaseOneThreeNodeTestSC(unittest.TestCase):
    def setUp(self):
        self.tx = src.TX(Role="Source")
        self.conf = self.tx.conf
        self.payload_bits = np.array(self.tx.string_to_bits(self.conf.PAYLOAD))
        self.MAC = hmac.new(self.conf.MAC_KEY.encode('utf-8'), msg=self.conf.PAYLOAD.encode('utf-8'), digestmod='sha256').hexdigest()
        self.MAC_bits = np.array(self.tx.hex_to_binary_list(self.MAC))
        self.payload_bits = self.payload_bits[:self.MAC_bits.shape[0]]
        self.tx_bits = np.concatenate(
                                    [ 
                                    
                                    list(self.payload_bits),
                                    # self.MAC_bits, #superpose instead of sending it separately
                                    ]
                                )
        
        self.fsk_signal_SC = self.tx.fsk_modulate(self.tx_bits, # sends with half the power,
                                    mac = self.MAC_bits,
                                    alpha = self.conf.ALPHA,
                                    sps = self.conf.TX_SPS, 
                                    preamble = np.concatenate([ [0 for _ in range(1000//self.conf.TX_SPS)] , self.conf.PREAMBLE]), 
                                    postamble = np.concatenate([self.conf.PREAMBLE, [0 for _ in range(1000//self.conf.TX_SPS)]]),
                                    scale = self.conf.TX_PAYLOAD_POWER_SCALE # send the payload with half the power of the preamble
                                    )
        
        self.rx_dest = src.RX(Role = "Destination")
        self.rx_relay = src.RX(Role = "Relay")
        self.pp = src.PostProcessing
        self.demod = src.Demodulation()
    
    def TestPhaseOne(self):#Branden
        def TxSource():
            try:
                self.tx.send_waveform(self.fsk_signal_SC)
            except Exception as e:
                self.fail(f"Failed to send waveform: {e}")
        def RxRelay():
            file_relay = self.rx_relay.record()
            pp_relay = self.pp(file_relay, self.rx_relay.conf)
            if(pp_relay.check()):
                print("Recording at relay is correct")
                for i in range(len(pp_relay.TotalFramesIndex)):
                    frame = pp_relay.frameByNumber(i)
                    hard_decision,rs, SNR = self.demod.decode(frame)
                    index = self.demod.detect_message_indices(received=list(hard_decision), preamble=self.conf.PREAMBLE, repeat=self.conf.PREAMBLE_REPEAT)
                    if index[0] is None or index[1] is None:
                        print("No preamble detected!")
                        continue

                    msg_hard_decision = hard_decision[index[0]:index[1]]
                    print("Message: ", pp_relay.bits_to_string(msg_hard_decision[0]))

                    ## add the message decoding using LDPC
                    
                    SNR = SNR[index[0]+10:index[1]-10]
                    print("SNR: ", np.nanmean(SNR))

                    # pull rs values of the signal from phase 1 from the database
                    rs_recovered = None
                    tag_llrs = self.demod.successive_cancellation(msg_hard_decision, rs_recovered)

                    Recovered_direct_tag = src.channelCoding.decode_LDPC(tag_llrs, 256)
                    expected_tag = hmac.new(self.conf.MAC_KEY.encode('utf-8'), msg=pp_relay.bits_to_string(msg_hard_decision).tobytes(), digestmod='sha256').hexdigest()

                    if self.pp.binary_list_to_hex(Recovered_direct_tag) == expected_tag:
                        print("MAC is correct")
                    else:
                        print("MAC is incorrect")
                    print("Recovered MAC: ", self.pp.binary_list_to_hex(Recovered_direct_tag))
                    print("Expected MAC: ", expected_tag)

        try:
            tx_thread = threading.Thread(target=TxSource)
            rx_thread = threading.Thread(target=RxRelay)
            rx_thread.start()
            time.sleep(1.7)  # wait for the transmission to start
            tx_thread.start()
            tx_thread.join()
            rx_thread.join()
        except Exception as e:
            self.fail(f"Failed to record waveform: {e}")
        def RxDest():
            file_dest = self.rx_dest.record()
            pp_dest = self.pp(file_dest, self.rx_dest.conf)
            if(pp_dest.check()):
                print("Recording at destination is correct")



class PhaseTwoThreeNodeTestSC(unittest.TestCase):
    def setUp(self):
        self.tx_relay = src.TX(Role = "Relay")
        self.rx_dest = src.RX(Role="Destination")
        self.pp = src.PostProcessing
        self.demod = src.rx.Demodulation()

        self.conf = self.tx_relay.conf
        self.payload_bits = np.array(self.tx_relay.string_to_bits(self.conf.PAYLOAD))
        self.MAC = hmac.new(self.conf.MAC_KEY.encode('utf-8'), msg=self.conf.PAYLOAD.encode('utf-8'), digestmod='sha256').hexdigest()
        self.MAC_bits = np.array(self.tx_relay.hex_to_binary_list(self.MAC))

    
    def TestPhaseTwo(self):
        def TxRelay():
            # must get the message from the RX_relay in phase 1
            fsk_signal = self.tx_relay.fsk_modulate(self.payload_bits, # sends with half the power,
                            # mac = self.MAC_bits,
                            # alpha = self.conf.ALPHA,
                            sps = self.conf.TX_SPS, 
                            preamble = np.concatenate([ [0 for _ in range(1000//self.conf.TX_SPS)] , self.conf.PREAMBLE]), 
                            postamble = np.concatenate([self.conf.PREAMBLE, [0 for _ in range(1000//self.conf.TX_SPS)]]),
                            scale = self.conf.TX_PAYLOAD_POWER_SCALE # send the payload with half the power of the preamble
                            )
            self.tx_relay.send_waveform(fsk_signal)
        def RxDest():
            file = self.rx_dest.record()
            
            pp = self.pp(file, self.rx_dest.conf, demod=self.demod, plot=True)
            if pp.check():
                print("Recording is correct")
                for i in range(len(pp.TotalFramesIndex)):
                    frame = pp.frameByNumber(i)
                    hard_decision,rs, SNR = self.demod.decode(frame)
                    index = self.demod.detect_message_indices(received=list(hard_decision), preamble=self.conf.PREAMBLE, repeat=self.conf.PREAMBLE_REPEAT)
                    if index[0] is None or index[1] is None:
                        print("No preamble detected!")
                        continue

                    msg_hard_decision = hard_decision[index[0]:index[1]]
                    print("Message: ", pp.bits_to_string(msg_hard_decision[0]))

                    ## add the message decoding using LDPC
                    
                    SNR = SNR[index[0]+10:index[1]-10]
                    print("SNR: ", np.nanmean(SNR))

                    # pull rs values of the signal from phase 1 from the database
                    rs_recovered = None
                    tag_llrs = self.demod.successive_cancellation(msg_hard_decision, rs_recovered)

                    Recovered_direct_tag = src.channelCoding.decode_LDPC(tag_llrs, 256)
                    expected_tag = hmac.new(self.conf.MAC_KEY.encode('utf-8'), msg=pp.bits_to_string(msg_hard_decision).tobytes(), digestmod='sha256').hexdigest()

                    if self.pp.binary_list_to_hex(Recovered_direct_tag) == expected_tag:
                        print("MAC is correct")
                    else:
                        print("MAC is incorrect")
                    print("Recovered MAC: ", self.pp.binary_list_to_hex(Recovered_direct_tag))
                    print("Expected MAC: ", expected_tag)

        try:
            tx_thread = threading.Thread(target=TxRelay)
            rx_thread = threading.Thread(target=RxDest)
            rx_thread.start()
            time.sleep(1.7)  # wait for the transmission to start
            tx_thread.start()
            tx_thread.join()
            rx_thread.join()
        except Exception as e:
            self.fail(f"Failed to record waveform: {e}")










class PhaseOneThreeNodeTestOrig(unittest.TestCase):
    def setUp(self):
        self.tx = src.TX(Role="Source")
        self.conf = self.tx.conf
        self.payload_bits = np.array(self.tx.string_to_bits(self.conf.PAYLOAD))
        self.MAC = hmac.new(self.conf.MAC_KEY.encode('utf-8'), msg=self.conf.PAYLOAD.encode('utf-8'), digestmod='sha256').hexdigest()
        self.MAC_bits = np.array(self.tx.hex_to_binary_list(self.MAC))
        self.payload_bits = self.payload_bits[:self.MAC_bits.shape[0]]
        self.tx_bits = np.concatenate(
                                    [ 
                                    
                                    list(self.payload_bits),
                                    # self.MAC_bits, #superpose instead of sending it separately
                                    ]
                                )
        
        self.fsk_signal = self.tx.fsk_modulate(self.tx_bits, # sends with half the power,
                                    # mac = self.MAC_bits,
                                    # alpha = self.conf.ALPHA,
                                    sps = self.conf.TX_SPS, 
                                    preamble = np.concatenate([ [0 for _ in range(1000//self.conf.TX_SPS)] , self.conf.PREAMBLE]), 
                                    postamble = np.concatenate([self.conf.PREAMBLE, [0 for _ in range(1000//self.conf.TX_SPS)]]),
                                    scale = self.conf.TX_PAYLOAD_POWER_SCALE # send the payload with half the power of the preamble
                                    )
        
        self.rx_dest = src.RX(Role = "Destination")
        self.rx_relay = src.RX(Role = "Relay")
        self.pp = src.PostProcessing
        self.demod = src.rx.Demodulation
    
    def TestPhaseOne(self):#Branden
        def TxSource():
            try:
                self.tx.send_waveform(self.fsk_signal)
            except Exception as e:
                self.fail(f"Failed to send waveform: {e}")
        def RxRelay():
            file_relay = self.rx_relay.record()
            pp_relay = self.pp(file_relay, self.rx_relay.conf)
            if(pp_relay.check()):
                print("Recording at relay is correct")
                for i in range(len(pp_relay.TotalFramesIndex)):
                    frame = pp_relay.frameByNumber(i)
                    hard_decision,rs, SNR = self.demod.decode(frame)
                    index = self.demod.detect_message_indices(received=list(hard_decision), preamble=self.conf.PREAMBLE, repeat=self.conf.PREAMBLE_REPEAT)
                    if index[0] is None or index[1] is None:
                        print("No preamble detected!")
                        continue

                    msg_hard_decision = hard_decision[index[0]:index[1]][0:-256]
                    MAC_hard_decision = hard_decision[index[0]:index[1]][-256:]
                    print("Message: ", pp_relay.bits_to_string(msg_hard_decision[0]))
                    print("MAC: ", pp_relay.binary_list_to_hex(MAC_hard_decision[0]))

                    SNR = SNR[index[0]+10:index[1]-10]
                    print("SNR: ", np.nanmean(SNR))



                    expected_tag = hmac.new(self.conf.MAC_KEY.encode('utf-8'), msg=pp_relay.bits_to_string(msg_hard_decision).tobytes(), digestmod='sha256').hexdigest()

                    if self.pp.binary_list_to_hex(MAC_hard_decision) == expected_tag:
                        print("MAC is correct")
                    else:
                        print("MAC is incorrect")
                    ## add the message and MAC decoding using LDPC

        try:
            tx_thread = threading.Thread(target=TxSource)
            rx_thread = threading.Thread(target=RxRelay)
            rx_thread.start()
            time.sleep(1.7)  # wait for the transmission to start
            tx_thread.start()
            tx_thread.join()
            rx_thread.join()
        except Exception as e:
            self.fail(f"Failed to record waveform: {e}")

            

        def RxDest():
            file_dest = self.rx_dest.record()
            pp_dest = self.pp(file_dest, self.rx_dest.conf)
            if(pp_dest.check()):
                print("Recording at destination is correct")


class PhaseTwoThreeNodeTestOrig(unittest.TestCase):
    def setUp(self):
        self.tx_relay = src.TX(Role = "Relay")
        self.rx_dest = src.RX(Role="Destination")
        self.pp = src.PostProcessing
        self.demod = src.rx.Demodulation()
        self.conf:src.CONFIG = self.rx_dest.conf

        self.payload_bits = np.array(self.tx.string_to_bits(self.conf.PAYLOAD))
        self.MAC = hmac.new(self.conf.MAC_KEY.encode('utf-8'), msg=self.conf.PAYLOAD.encode('utf-8'), digestmod='sha256').hexdigest()
        self.MAC_bits = np.array(self.tx.hex_to_binary_list(self.MAC))
        

    
    def TestPhaseTwo(self):
        def TxRelay():
            # must get the message from the RX_relay in phase 1
            fsk_signal = self.tx_relay.fsk_modulate(np.concatenate([self.payload_bits, self.MAC_bits]), # sends with half the power,
                            # mac = self.MAC_bits,
                            # alpha = self.conf.ALPHA,
                            sps = self.conf.TX_SPS, 
                            preamble = np.concatenate([ [0 for _ in range(1000//self.conf.TX_SPS)] , self.conf.PREAMBLE]), 
                            postamble = np.concatenate([self.conf.PREAMBLE, [0 for _ in range(1000//self.conf.TX_SPS)]]),
                            scale = self.conf.TX_PAYLOAD_POWER_SCALE # send the payload with half the power of the preamble
                            )
            self.tx_relay.send_waveform(fsk_signal)
        def RxDest():
            file = self.rx_dest.record()
            
            pp = self.pp(file, self.rx_dest.conf, demod=self.demod, plot=True)
            if pp.check():
                print("Recording is correct")
                for i in range(len(pp.TotalFramesIndex)):
                    frame = pp.frameByNumber(i)
                    hard_decision,rs, SNR = self.demod.decode(frame)
                    index = self.demod.detect_message_indices(received=list(hard_decision), preamble=self.conf.PREAMBLE, repeat=self.conf.PREAMBLE_REPEAT)
                    if index[0] is None or index[1] is None:
                        print("No preamble detected!")
                        continue

                    msg_hard_decision = hard_decision[index[0]:index[1]][0:-256]
                    MAC_hard_decision = hard_decision[index[0]:index[1]][-256:]
                    print("Message: ", pp.bits_to_string(msg_hard_decision[0]))
                    print("MAC: ", pp.binary_list_to_hex(MAC_hard_decision[0]))

                    SNR = SNR[index[0]+10:index[1]-10]
                    print("SNR: ", np.nanmean(SNR))



                    expected_tag = hmac.new(self.conf.MAC_KEY.encode('utf-8'), msg=pp.bits_to_string(msg_hard_decision).tobytes(), digestmod='sha256').hexdigest()

                    if self.pp.binary_list_to_hex(MAC_hard_decision) == expected_tag:
                        print("MAC is correct")
                    else:
                        print("MAC is incorrect")
                    ## add the message and MAC decoding using LDPC

        try:
            tx_thread = threading.Thread(target=TxRelay)
            rx_thread = threading.Thread(target=RxDest)
            rx_thread.start()
            time.sleep(1.7)  # wait for the transmission to start
            tx_thread.start()
            tx_thread.join()
            rx_thread.join()
        except Exception as e:
            self.fail(f"Failed to record waveform: {e}")
            