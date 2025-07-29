
import numpy as np
import tensorflow as tf
from sionna.phy.fec.ldpc import LDPC5GEncoder, LDPC5GDecoder


def encdoe(msg:list|np.ndarray, codeword_length):
    K = len(msg)
    encoder = LDPC5GEncoder(K ,codeword_length)
    msg = tf.constant(msg, dtype=tf.float32)[None, :]
    codeword = encoder.call(msg)
    return codeword.numpy().ravel().astype(np.int8)

def decode(codeword_llr:list|np.ndarray , msg_length):
    N_LDPC = len(codeword_llr)
    encoder = LDPC5GEncoder(msg_length ,N_LDPC)
    decoder = LDPC5GDecoder(encoder=encoder,num_iter=20)
    llr = tf.constant(codeword_llr, dtype=tf.float32)
    
    decoded = decoder.call(llr)

    return decoded.numpy().astype(np.int8)



R = 1/2
msg_len = 256
msg = np.random.randint(0,2, int(np.round(msg_len/R)))

codeword  = encdoe(msg, 2000)

llr = [10 if i else -10 for i in codeword]

decoded = decode(llr, len(msg))

print(msg.tolist()==decoded.tolist())
