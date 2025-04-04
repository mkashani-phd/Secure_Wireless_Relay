import unittest
import src
import numpy as np
import hmac
import matplotlib.pyplot as plt

# test the modulation and demodulation of the FSK signal

class TestFSKModulation(unittest.TestCase):
    def setUp(self):
        
        self.tx = src.TX(Role = "Source")
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

        self.fsk_signal_SC = self.tx.fsk_modulate(self.tx_bits, # sends with half the power,
                                    mac = self.MAC_bits,
                                    alpha = self.conf.ALPHA,
                                    sps = self.conf.TX_SPS, 
                                    preamble = np.concatenate([ [0 for _ in range(1000//self.conf.TX_SPS)] , self.conf.PREAMBLE]), 
                                    postamble = np.concatenate([self.conf.PREAMBLE, [0 for _ in range(1000//self.conf.TX_SPS)]]),
                                    scale = self.conf.TX_PAYLOAD_POWER_SCALE # send the payload with half the power of the preamble
                                    )

    def test_modulation(self):
        self.assertTrue(len(self.fsk_signal) > 0, "Modulated signal is empty")
        plt.plot(np.gradient(np.unwrap(np.angle(self.fsk_signal))))
        plt.title("Modulated FSK Signal")
        plt.xlabel("Sample Index")
        plt.ylabel("Amplitude")
        plt.show()

    def test_modulation_SuperPosition_Code(self):  

        self.assertTrue(len(self.fsk_signal_SC) > 0, "Modulated signal is empty")
        plt.plot(np.gradient(np.unwrap(np.angle(self.fsk_signal_SC))))
        plt.title("Modulated superposed FSK Signal")
        plt.xlabel("Sample Index")
        plt.ylabel("Amplitude")
        plt.show()

    def test_transmission(self):
        try:
            self.tx.send_waveform(self.fsk_signal)
        except Exception as e:
            self.fail(f"Failed to send waveform: {e}")


class TestFSKDemodulation(unittest.TestCase):
    def setUp(self):
        self.tx = src.TX(Role = "Source")
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




    def test_record(self):
        import threading
        import time

        def run_rx():
            self.rx_dest.record(self.fsk_signal)

        def run_tx():
            self.tx.send_waveform(self.fsk_signal)
        try:
            tx_thread = threading.Thread(target=run_tx)
            rx_thread = threading.Thread(target=run_rx)
            rx_thread.start()
            time.sleep(1)  # wait for the transmission to start
            rx_thread.start()
            tx_thread.join()
            rx_thread.join()
        except Exception as e:
            self.fail(f"Failed to record waveform: {e}")
        
        
        


if __name__ == '__main__':
    unittest.main()

