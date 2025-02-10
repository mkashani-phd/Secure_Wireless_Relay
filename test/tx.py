import uhd
import time
import numpy as np
import hmac
import config
import channelCoding as cc

conf = config.CONFIG()



def hex_to_binary_list(hex_string):
    binary_list = []
    for hex_char in hex_string:
        # Convert each hex character to a 4-bit binary string
        binary_list.extend([int(bit) for bit in format(int(hex_char, 16), '04b')])
    return binary_list

def bits_to_symbols(bit_list):
    bit_array = np.array(bit_list)
    symbols = np.where(bit_array == 1, 9.5, -9.5).astype(np.float32)
    return symbols

def string_to_bits(s):
    bits = []
    for char in s:
        bin_repr = format(ord(char), '08b')  # 8-bit binary
        bits.extend([int(b) for b in bin_repr])
    return bits

def fsk_modulate(bits, sps):
    symbols = bits_to_symbols(bits)
    upsampled = np.repeat(symbols, sps) / np.sqrt(sps)
    phase =  np.cumsum(upsampled) 
    fsk_signal = np.exp(1j * phase).astype(np.complex64)
    return fsk_signal

def test():
    global tx_bits

    payload_bits = np.array(string_to_bits(conf.PAYLOAD))
    MAC = hmac.new(conf.MAC_KEY.encode('utf-8'), msg=conf.PAYLOAD.encode('utf-8'), digestmod='sha256').hexdigest()
    MAC_bits = np.array(hex_to_binary_list(MAC))


    payload_bits = cc.generate_5g_codeword_bg2(payload_bits, conf.MSG_CODE_RATE)
    MAC_bits = cc.generate_5g_codeword_bg2(MAC_bits, conf.MAC_CODE_RATE)
    print(payload_bits.shape, MAC_bits.shape)
    
    tx_bits = np.concatenate(
                                [ 
                                conf.PREAMBLE ,
                                list(payload_bits),
                                MAC_bits,
                                conf.PREAMBLE[::-1]
                                ]
                            )
    fsk_signal = fsk_modulate(tx_bits, conf.TX_SPS)

    usrp = uhd.usrp.MultiUSRP("serial=8000169")  # Replace with your USRP's serial or remove parameter for default
    # Transmit signal
    for i in range(10):
        usrp.send_waveform(fsk_signal, len(fsk_signal)/conf.TX_RATE  , conf.FREQ, conf.TX_RATE, conf.CHANNEL, conf.TX_GAIN)
        time.sleep(0.1)

    print("[TX] FSK signal transmitted.")

if __name__ == "__main__":
    test()
