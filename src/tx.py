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

    def bits_to_symbols(self, bit_list):
        bit_array = np.array(bit_list)
        symbols = np.where(bit_array == 1, 1, -1).astype(np.float32) 
        return symbols

    def fsk_modulate(self, bits, sps, preamble, postamble, scale = 1/2,  mac = None, alpha = 0):
 

        payload_bits= np.concatenate([preamble, bits, postamble])
        indx = slice(len(preamble)*sps, (len(preamble) + len(bits))*sps)

        payload_symbols = self.bits_to_symbols(payload_bits)
        mac_symbols = self.bits_to_symbols(mac) if mac is not None else None

        payload_upsampled = np.repeat(payload_symbols, sps)
        mac_upsampled = np.repeat(mac_symbols, sps)  if mac_symbols is not None else None


        phase_step = 2*np.pi *  self.conf.FREQ_DEV/self.conf.TX_RATE    # = 2π·25 000/1 000 000 = 0.1571


        payload_phase = np.cumsum(payload_upsampled* phase_step)
        mac_phase = np.cumsum(mac_upsampled* phase_step) if mac_upsampled is not None else None


        payload_signal = np.exp(1j * payload_phase).astype(np.complex64)
        payload_signal[indx] = np.sqrt(scale)*payload_signal[indx]
        mac_signal = np.sqrt(scale)* np.exp(1j * mac_phase).astype(np.complex64) if mac_phase is not None else None

        ########### Superposition of MAC and Payload ###############################
        if mac_signal is not None and alpha is not None:
            payload_signal[indx] = np.sqrt(alpha)*mac_signal + np.sqrt(1-alpha)*payload_signal[indx]
        else:
            payload_signal = payload_signal
        ############################################################################

        return payload_signal
    
    def send_waveform(self, waveform):
        self.usrp.send_waveform(waveform, len(waveform)/self.conf.TX_RATE  , self.conf.FREQ, self.conf.TX_RATE, self.conf.CHANNEL, self.conf.TX_GAIN)


