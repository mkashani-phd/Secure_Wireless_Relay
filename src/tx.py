import uhd
import time
import numpy as np
import hmac
from . import config
from . import channelCoding as cc




class TX:

    def __init__(self, conf = config.CONFIG(), usrp: uhd.usrp.MultiUSRP = None,  role = "source"):
        if role.lower() not in ["source", "relay"]:
            raise ValueError("Role must be either 'source' or 'relay'")
        
        self.role = role.lower()
        self.conf = conf
        self.usrp = usrp
        if usrp is None:
            if self.role == "source":
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

    def fsk_modulate(self, bits, sps, preamble, postamble, scale = 1/2,  mac = None, alpha = 0):
        preamble_symbols = self.bits_to_symbols(preamble)
        postamble_symbols = self.bits_to_symbols(postamble)
        payload_symbols = self.bits_to_symbols(bits)
        mac_symbols = self.bits_to_symbols(mac) if mac is not None else None

        preamble_upsampled = np.repeat(preamble_symbols, sps) / np.sqrt(sps)
        postamble_upsampled = np.repeat(postamble_symbols, sps) / np.sqrt(sps)
        payload_upsampled = np.repeat(payload_symbols, sps) / np.sqrt(sps)
        mac_upsampled = np.repeat(mac_symbols, sps) / np.sqrt(sps) if mac_symbols is not None else None

        preamble_phase = np.cumsum(preamble_upsampled)
        postamble_phase = np.cumsum(postamble_upsampled)
        payload_phase = np.cumsum(payload_upsampled)
        mac_phase = np.cumsum(mac_upsampled) if mac_upsampled is not None else None

        preamble_signal = np.exp(1j * preamble_phase).astype(np.complex64)
        postamble_signal = np.exp(1j * postamble_phase).astype(np.complex64)
        payload_signal = np.sqrt(scale)* np.exp(1j * payload_phase).astype(np.complex64)
        mac_signal = np.sqrt(scale)* np.exp(1j * mac_phase).astype(np.complex64) if mac_phase is not None else None

        ########### Superposition of MAC and Payload ###############################
        if mac_signal is not None and alpha is not None:
            payload_signal = np.sqrt(alpha)*mac_signal + np.sqrt(1-alpha)*payload_signal
        else:
            payload_signal = payload_signal
        ############################################################################

        return np.concatenate([preamble_signal, payload_signal, postamble_signal])
    
    def send_waveform(self, waveform):
        self.usrp.send_waveform(waveform, len(waveform)/self.conf.TX_RATE  , self.conf.FREQ, self.conf.TX_RATE, self.conf.CHANNEL, self.conf.TX_GAIN)


