import unittest
import src
import numpy as np
import hmac
import matplotlib.pyplot as plt

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
        def RxDest():
            file_dest = self.rx_dest.record()
            pp_dest = self.pp(file_dest, self.rx_dest.conf)
            if(pp_dest.check()):
                print("Recording at destination is correct")

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

            #decode lines

        def RxDest():
            file_dest = self.rx_dest.record()
            pp_dest = self.pp(file_dest, self.rx_dest.conf)
            if(pp_dest.check()):
                print("Recording at destination is correct")

class PhaseTwoThreeNodeTestSC(unittest.TestCase):
    def setUp(self):
        
        return super().setUp()
    
    def TestPhaseTwo(self):
        def TxRelay():
            pass
        def RxDest():
            pass

class PhaseTwoThreeNodeTestOrig(unittest.TestCase):
    def setUp(self):
        
        return super().setUp()
    
    def TestPhaseTwo(self):
        def TxRelay():
            pass
        def RxDest():
            pass