import unittest
import src
import numpy as np
import hmac
import matplotlib.pyplot as plt



class TestWithSrcOnDifferentPC(unittest.TestCase):
    def setUp(self):
        self.rx_dest = src.RX(Role="Destination")
        self.rx_relay = src.RX(Role="Relay")
        self.conf = self.rx_relay.conf
        self.pp = src.PostProcessing



        

    def test_demodulation_original_dest(self):
        import threading
        import time

        def run_rx():
            file = self.rx_dest.record()
            demod = src.rx.Demodulation()
            pp = self.pp(file, self.rx_dest.conf, demod=demod, plot=True)
            MAC = hmac.new(self.conf.MAC_KEY.encode('utf-8'), msg=self.conf.PAYLOAD.encode('utf-8'), digestmod='sha256').hexdigest()
            MAC_bits = np.array(self.pp.hex_to_binary_list(self.MAC))
            if pp.check():
                print("Recording is correct")
                for i in range(len(pp.Frames)):
                    frame = pp.frameByNumber(i)
                    hard_decision,rs, SNR = demod.decode(frame)
                    index = demod.detect_message_indices(received=list(hard_decision), preamble=self.conf.PREAMBLE, repeat=self.conf.PREAMBLE_REPEAT)
                    if index[0] is None or index[1] is None:
                        print("No preamble detected!")
                        continue

                    msg_hard_decision = hard_decision[index[0]:index[1]]
                    print("Message: ", pp.bits_to_string(msg_hard_decision[0:-256]))
                    print("recieved MAC: ", pp.binary_list_to_hex(msg_hard_decision[-256:]))
                    expected_MAC = hmac.new(self.conf.MAC_KEY.encode('utf-8'), msg=pp.bits_to_string(msg_hard_decision[0:-256]).encode('utf-8'), digestmod='sha256').hexdigest()
                    if pp.binary_list_to_hex(msg_hard_decision[-256:]) == expected_MAC:
                        print("Good MAC")
                    else:
                        print("MAC is not correct")

                    SNR = SNR[index[0]+10:index[1]-10]
                    print("SNR: ", np.nanmean(SNR))
            else:
                raise Exception("Recording is not correct")
                


        def run_tx():
            fsk_signal = self.tx.fsk_modulate(np.concatenate([self.payload_bits, self.MAC_bits]), # sends with half the power,
                            # mac = self.MAC_bits,
                            # alpha = self.conf.ALPHA,
                            sps = self.conf.TX_SPS, 
                            preamble = np.concatenate([ [0 for _ in range(1000//self.conf.TX_SPS)] , self.conf.PREAMBLE]), 
                            postamble = np.concatenate([self.conf.PREAMBLE, [0 for _ in range(1000//self.conf.TX_SPS)]]),
                            scale = self.conf.TX_PAYLOAD_POWER_SCALE # send the payload with half the power of the preamble
                            )
            for i in range(5):
                time.sleep(0.1)
                self.tx.send_waveform(fsk_signal)
        
        try:
            tx_thread = threading.Thread(target=run_tx)
            rx_thread = threading.Thread(target=run_rx)
            rx_thread.start()
            time.sleep(1.7)  # wait for the transmission to start
            tx_thread.start()
            tx_thread.join()
            rx_thread.join()
        except Exception as e:
            self.fail(f"Failed to record waveform: {e}")
