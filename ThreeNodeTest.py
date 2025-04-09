import unittest
import src
import numpy as np
import hmac
import matplotlib.pyplot as plt

class PhaseOneThreeNodeTestSC(unittest.TestCase):
    def setUp(self):
        
        return super().setUp()
    
    def TestPhaseOne(self):#Branden
        def TxSource():
            pass
        def RxRelay():
            pass
        def RxDest():
            pass

class PhaseOneThreeNodeTestOrig(unittest.TestCase):
    def setUp(self):
        
        return super().setUp()
    
    def TestPhaseOne(self):#Branden
        def TxSource():
            pass
        def RxRelay():
            pass
        def RxDest():
            pass

class PhaseTwoThreeNodeTestSC(unittest.TestCase):
    def setUp(self):
        self.tx = src.TX(Role = "Source")
        self.conf = self.tx.conf
        self.payload_bits = np.array(self.tx.string_to_bits(self.conf.PAYLOAD))
        self.MAC = hmac.new(self.conf.MAC_KEY.encode('utf-8'), msg=self.conf.PAYLOAD.encode('utf-8'), digestmod='sha256').hexdigest()
        self.MAC_bits = np.array(self.tx.hex_to_binary_list(self.MAC))


        
        
        self.fsk_signal = self.tx.fsk_modulate(np.concatenate([self.payload_bits, self.MAC_bits]), # sends with half the power,
                                    # mac = self.MAC_bits,
                                    # alpha = self.conf.ALPHA,
                                    sps = self.conf.TX_SPS, 
                                    preamble = np.concatenate([ [0 for _ in range(1000//self.conf.TX_SPS)] , self.conf.PREAMBLE]), 
                                    postamble = np.concatenate([self.conf.PREAMBLE, [0 for _ in range(1000//self.conf.TX_SPS)]]),
                                    scale = self.conf.TX_PAYLOAD_POWER_SCALE # send the payload with half the power of the preamble
                                    )

        self.MAC_bits = src.encode_LDPC(self.MAC_bits, 2048) # just to get the actual dimensions of the MAC bits
        self.payload_bit = self.payload_bits[:self.MAC_bits.shape[0]]
        self.MAC_bits = hmac.new(self.conf.MAC_KEY.encode('utf-8'), msg=self.payload_bit.tobytes(), digestmod='sha256').hexdigest()
        self.MAC_bits = src.encode_LDPC(self.tx.hex_to_binary_list(self.MAC_bits), 2048)
        self.fsk_signal_SC = self.tx.fsk_modulate(self.payload_bit, # sends with half the power,
                                    mac = self.MAC_bits,
                                    alpha = self.conf.ALPHA,
                                    sps = self.conf.TX_SPS, 
                                    preamble = np.concatenate([ [0 for _ in range(1000//self.conf.TX_SPS)] , self.conf.PREAMBLE]), 
                                    postamble = np.concatenate([self.conf.PREAMBLE, [0 for _ in range(1000//self.conf.TX_SPS)]]),
                                    scale = self.conf.TX_PAYLOAD_POWER_SCALE # send the payload with half the power of the preamble
                                    )
        
        # create a RX instance to demodulate the signal
        self.rx_dest = src.RX(Role="Destination")
        self.rx_relay = src.RX(Role="Relay")
        self.pp = src.PostProcessing
        self.demod = src.rx.Demodulation()
    
    def TestPhaseTwo(self):
        def TxRelay():
            self.tx.send_waveform(self.fsk_signal_SC)
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
                    expected_tag = hmac.new(self.conf.MAC_KEY.encode('utf-8'), msg=msg_hard_decision.tobytes(), digestmod='sha256').hexdigest()

                    if self.pp.binary_list_to_hex(Recovered_direct_tag) == expected_tag:
                        print("MAC is correct")
                    else:
                        print("MAC is incorrect")
                    print("Recovered MAC: ", self.pp.binary_list_to_hex(Recovered_direct_tag))
                    print("Expected MAC: ", expected_tag)

class PhaseTwoThreeNodeTestOrig(unittest.TestCase):
    def setUp(self):
        
        return super().setUp()
    
    def TestPhaseTwo(self):
        def TxRelay():
            pass
        def RxDest():
            pass