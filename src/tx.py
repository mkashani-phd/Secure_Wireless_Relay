import uhd
import time
import numpy as np
import hmac
import config
import channelCoding as cc

conf = config.CONFIG()


class TX:

    def __init__(self, Role = "Source", usrp: uhd.usrp.MultiUSRP = None):
        self.tx_bits = None
        if Role not in ["Source", "Relay"]:
            raise ValueError("Role must be either 'Source' or 'Relay'")
        
        self.Role = Role
        if usrp is None:
            if self.Role == "Source":
                self.usrp = uhd.usrp.MultiUSRP(f"serial={conf.SOURCE}")
            else:
                self.usrp = uhd.usrp.MultiUSRP(f"serial={conf.RELAY}")
    
    def __del__(self):
        if self.usrp is not None:
            self.usrp = None
            del self.usrp


    def hex_to_binary_list(self,hex_string):
        binary_list = []
        for hex_char in hex_string:
            # Convert each hex character to a 4-bit binary string
            binary_list.extend([int(bit) for bit in format(int(hex_char, 16), '04b')])
        return binary_list

    def bits_to_symbols(self,bit_list):
        bit_array = np.array(bit_list)
        symbols = np.where(bit_array == 1, 9.5, -9.5).astype(np.float32)
        return symbols

    def string_to_bits(self,s):
        bits = []
        for char in s:
            bin_repr = format(ord(char), '08b')  # 8-bit binary
            bits.extend([int(b) for b in bin_repr])
        return bits

    def fsk_modulate(self, bits, mac, alpha, sps, preamble, postamble, scale = 1/2):
        preamble_symbols = self.bits_to_symbols(preamble)
        postamble_symbols = self.bits_to_symbols(postamble)
        payload_symbols = self.bits_to_symbols(bits)
        mac_symbols = self.bits_to_symbols(mac)

        preamble_upsampled = np.repeat(preamble_symbols, sps) / np.sqrt(sps)
        postamble_upsampled = np.repeat(postamble_symbols, sps) / np.sqrt(sps)
        payload_upsampled = np.repeat(payload_symbols, sps) / np.sqrt(sps)
        mac_upsampled = np.repeat(mac_symbols, sps) / np.sqrt(sps)

        preamble_phase = np.cumsum(preamble_upsampled)
        postamble_phase = np.cumsum(postamble_upsampled)
        payload_phase = np.cumsum(payload_upsampled)
        mac_phase = np.cumsum(mac_upsampled)

        preamble_signal = np.exp(1j * preamble_phase).astype(np.complex64)
        postamble_signal = np.exp(1j * postamble_phase).astype(np.complex64)
        payload_signal = np.sqrt(scale)* np.exp(1j * payload_phase).astype(np.complex64)
        mac_signal = np.sqrt(scale)* np.exp(1j * mac_phase).astype(np.complex64)

        ########### Superposition of MAC and Payload ###############################
        payload_signal = np.sqrt(alpha)*mac_signal + np.sqrt(1-alpha)*payload_signal
        ############################################################################

        return np.concatenate([preamble_signal, payload_signal, postamble_signal])

def test():
    global tx_bits
    tx = TX(Role = "Source")
    payload_bits = np.array(tx.string_to_bits(conf.PAYLOAD))
    MAC = hmac.new(conf.MAC_KEY.encode('utf-8'), msg=conf.PAYLOAD.encode('utf-8'), digestmod='sha256').hexdigest()
    MAC_bits = np.array(tx.hex_to_binary_list(MAC))


    # payload_bits = cc.generate_5g_codeword_bg2(payload_bits, conf.MSG_CODE_RATE)
    MAC_bits = cc.encode_LDPC(MAC_bits, 2048)

    payload_bits = payload_bits[:MAC_bits.shape[0]]
    print(payload_bits.shape, MAC_bits.shape)
    
    tx_bits = np.concatenate(
                                [ 
                                
                                list(payload_bits),
                                # MAC_bits,
 # 
                                ]
                            )
    # print(tx_bits.tolist())
    fsk_signal = tx.fsk_modulate(tx_bits, # sends with half the power,
                              mac = MAC_bits,
                              alpha = conf.ALPHA,
                              sps = conf.TX_SPS, 
                              preamble = np.concatenate([ [0 for _ in range(1000//conf.TX_SPS)] , conf.PREAMBLE]), 
                              postamble = np.concatenate([conf.PREAMBLE, [0 for _ in range(1000//conf.TX_SPS)]]),
                              scale = conf.TX_PAYLOAD_POWER_SCALE # send the payload with half the power of the preamble
                              )

    
    # Transmit signal
    for i in range(10):
        tx.usrp.send_waveform(fsk_signal, len(fsk_signal)/conf.TX_RATE  , conf.FREQ, conf.TX_RATE, conf.CHANNEL, conf.TX_GAIN)
        time.sleep(0.1)

    print("[TX] FSK signal transmitted.")
    tx = None

if __name__ == "__main__":
    test()
