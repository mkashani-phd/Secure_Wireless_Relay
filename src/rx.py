import pymongo.collection
import uhd, time, os
from operator import itemgetter
from itertools import groupby
import scipy.signal 
from scipy.special import i0
import numpy as np
import pymongo
import datetime 
import copy


import matplotlib.pyplot as plt

from . import config
from . import channelCoding as cc


class RX:
    def __init__(self, conf:config.CONFIG = config.CONFIG(), usrp:uhd.usrp.MultiUSRP = None, Role:str = "Destination"):
        self.conf = conf
        if usrp is None:
            self.usrp = uhd.usrp.MultiUSRP(f"serial={conf.DESTINATION}")
        else:
            self.usrp = usrp
        if Role not in ["Destination", "Relay"]:
            raise ValueError("Role must be either 'Destination' or 'Relay'")
            exit(1)
        self.Role = Role
    
    #decunstruct the USRP object
    def __del__(self):
        self.usrp = None 

    def _config_streamer(self,chnls,spp = None):
        st_args = uhd.usrp.StreamArgs("fc32", "sc16")
        st_args.channels = chnls
        # st_args.args = "spp="+str(spp)
        streamer = self.usrp.get_rx_stream(st_args)
        return streamer

    def _batch_init(self,streamer,batch_size = None):
        if batch_size is None:
            batch_size = streamer.get_max_num_samps()
        nr_batches= int(self.conf.ACQ_TIME * self.conf.RX_RATE / batch_size)
        return batch_size, nr_batches

    def _start_stream(self,streamer,batch_size):
        stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.start_cont)
        stream_cmd.num_samps = batch_size
        stream_cmd.stream_now = False  
        stream_cmd.time_spec = uhd.types.TimeSpec(self.usrp.get_time_now().get_real_secs() + 0.05)   
        streamer.issue_stream_cmd(stream_cmd)

    def _stop_stream(self,streamer,recv_buffer):
        metadata = uhd.types.RXMetadata()
        stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.stop_cont)
        streamer.issue_stream_cmd(stream_cmd)
        while streamer.recv(recv_buffer, metadata):
            pass



    def record(self):
        self.usrp.set_time_now(uhd.types.TimeSpec(0.0)) # this should work well for syncing the MIMO channel

        streamer = self._config_streamer( chnls=self.conf.CHANNEL,spp=None)
        batch_size, nr_batches = self._batch_init(streamer=  streamer, batch_size= 1920)
        recv_buffer = np.zeros((len(self.conf.CHANNEL), batch_size), dtype=np.complex64)
        metadata = uhd.types.RXMetadata()

        for chnl in self.conf.CHANNEL:
            self.usrp.set_rx_rate(self.conf.RX_RATE, chnl)
            self.usrp.set_rx_freq(uhd.libpyuhd.types.tune_request(self.conf.FREQ), chnl)
            
            if self.Role == "Destination":
                if self.conf.RX_GAIN != "agc":
                    self.usrp.set_rx_gain(self.conf.RX_GAIN, chnl)
                else:
                    self.usrp.set_rx_agc(True, 0)
                    print("AGC is enabled")
            elif self.Role == "Relay":
                if self.conf.RX_RELAY_GAIN != "agc":
                    self.usrp.set_rx_gain(self.conf.RX_RELAY_GAIN, chnl)
                else:
                    self.usrp.set_rx_agc(True, 0)
                    print("AGC is enabled")
            
            

        self._start_stream(streamer = streamer,batch_size= batch_size)
        

        
        os.makedirs(os.path.join(os.path.dirname(__file__),"__recording_cache__"), exist_ok=True)
        file = os.path.join(os.path.dirname(__file__),"__recording_cache__", f"{self.Role}_"+str(np.round(self.usrp.get_rx_freq(),2))+"_"+str(np.round(self.usrp.get_rx_rate(),2))+"_"+str(self.conf.RX_GAIN)+"_"+str(self.conf.ACQ_TIME) + "_"+ str(self.conf.IN_CHAMBER)+"_.iq")
        f = open(file, "wb")
        start = time.time()
        cnt = 4
        
        # Record 100 samples and calculate the average power as normal power
        for i in range(100):
            streamer.recv(recv_buffer, metadata)

        Noise = 0
        cnt = 0
        for i in range(1000):
            Noise += np.mean(np.abs(recv_buffer[0]))
            cnt += 1
        Noise /= cnt


        linient_counter = 0  # Counter to track leniency
        for i in range(nr_batches):
            streamer.recv(recv_buffer, metadata)
            power = np.mean(np.abs(recv_buffer[0]))
            
            if power > 1.1 * Noise:
                recv_buffer[0].tofile(f)
                linient_counter = self.conf.LINIENT  # Reset leniency counter
            else:
                if linient_counter > 0:
                    recv_buffer[0].tofile(f)  # Keep saving the buffer
                    linient_counter -= 1
                else:
                    recv_buffer[0].tofile(f)  # Save zeros if leniency is exhausted

            
        duration = time.time() - start
        print("\n Recorded Time: " + str(duration))
        # Stop Stream
        self._stop_stream(streamer=streamer, recv_buffer=recv_buffer)
        f.close()
        return file
    
    def butter(self,input):
        fltr = scipy.signal.butter(30, self.conf.LPF_CUTOFF, 'low', analog=False, output='sos',fs=self.conf.RX_RATE)
        return scipy.signal.sosfilt(fltr, input) 

    


class Demodulation:
    def __init__(self, conf:config.CONFIG = config.CONFIG()):
        self.conf = conf
        
    def butter(self,input):
        fltr = scipy.signal.butter(30, self.conf.LPF_CUTOFF, 'low', analog=False, output='sos',fs=self.conf.RX_RATE)
        return scipy.signal.sosfilt(fltr, input) 

    def fft_max_peak(self, frame,window):
        fft = np.fft.fftshift(np.fft.fft(frame[:window]))
        peak = np.argmax(np.abs(fft))
        return peak,fft
    
    def decision(self, peak, threshold):
        return 0 if peak < threshold else 1
    
    def find_best_offset(self, signal, symbol_length, tone_bins):
    
        best_offset = 0
        best_energy = -np.inf
        energies = []
        
        # Try different offsets in the range [0, max_offset)
        for offset in range(self.conf.WINDOW):
            # Compute how many complete symbols we have given the offset.
            n_symbols = (len(signal) - offset) // symbol_length
            if n_symbols <= 0:
                energies.append(0)
                continue
            
            # Extract symbols using the candidate offset.
            symbols = signal[offset : offset + n_symbols * symbol_length].reshape(n_symbols, symbol_length)
            
            # Compute the FFT for each symbol.
            fft_symbols = np.fft.fft(symbols, axis=1)
            
            # For each symbol, sum the energy in the bins corresponding to the FSK tones.
            # We use np.abs()**2 to get the energy.
            symbol_energies = np.sum(np.abs(fft_symbols[:, tone_bins])**2, axis=1)
            avg_energy = np.mean(symbol_energies)
            energies.append(avg_energy)
            
            # Keep track of the offset with the maximum average energy.
            if avg_energy > best_energy:
                best_energy = avg_energy
                best_offset = offset
        
        return best_offset
    
    def llr_from_fft(self, fft, noise):
        E_f1 = np.sum(np.power(np.abs(fft[len(fft)//2 - int(len(fft)*self.conf.FREQ_DEVIATION_PRECENTAGE)]),2))
        E_f2 = np.sum(np.power(np.abs(fft[len(fft)//2 + int(len(fft)*self.conf.FREQ_DEVIATION_PRECENTAGE)]),2))
        # llr for BFSK modulation is given by the following formula
        return ( np.average(np.power(np.abs(fft),2)) / noise )(E_f1-E_f2)
    
    def hex_to_binary_list(self, hex_string):
        binary_list = []
        for hex_char in hex_string:
            # Convert each hex character to a 4-bit binary string
            binary_list.extend([int(bit) for bit in format(int(hex_char, 16), '04b')])
        return binary_list
    
    

    def compute_hard_desicion_and_rs(self, signal, symbol_length, tone_bins, message_bits_for_sure=None):
        if message_bits_for_sure is None:
            message_bits_for_sure = self.string_to_bits(self.conf.PAYLOAD)

        offset = self.find_best_offset(signal, symbol_length, tone_bins)
        # print("offset: ", offset)

        n_symbols = (len(signal) - offset) // symbol_length
        symbols = signal[offset:n_symbols * symbol_length + offset]

        # Compute hard decision
        hard_decision = []
        for i in range(0, len(symbols), symbol_length):
            peak, fft_peak = self.fft_max_peak(symbols[i:i + symbol_length], symbol_length)
            hard_decision.append(self.decision(peak=peak, threshold=symbol_length // 2))

        # Compute FFT and power spectrum
        fft_symbols = np.fft.fft(symbols.reshape(n_symbols, symbol_length), axis=1)


        # For legacy return values
        fft_symbols = np.array(np.power(np.abs(np.fft.fft(symbols.reshape(n_symbols, symbol_length), axis=1)),2), dtype=np.float32)
        r0 = 0
        for i in range(-2,3):
            r0 += fft_symbols[:, tone_bins[1] + i] 

        r1 = 0
        for i in range(-2,3):
            r1 += fft_symbols[:, tone_bins[0] + i]
        
        ffSize = fft_symbols.shape[1]
        r_half = 0
        for i in range(-2,3):
            r_half += fft_symbols[:, ffSize//2 + i]

        noise_r = (r_half/5)*symbol_length
        signal = np.sum(np.power(np.abs(fft_symbols),2), axis=1)
        SNR = 10*np.log10(signal/noise_r -1)
        

        return hard_decision, [r0, r1, r_half], SNR
    
    
    



    def successive_cancellation(self, msg_decoded_bits,  rs , index):
        r0,r1,r_half = rs
        SC_llr = []
        for i in range(index[0],index[1]):            
            if msg_decoded_bits[i] == 0:                

                if r1[i] > self.conf.ALPHA * r0[i]:
                    SC_llr.append(np.log(r_half[i]/r1[i] ))
                else:
                    SC_llr.append(np.log(r0[i]/(self.conf.ALPHA * r1[i]) ))
            else:
                if r0[i] > self.conf.ALPHA * r1[i]:
                    SC_llr.append(np.log(r0[i]/r_half[i]))
                else:
                    SC_llr.append(np.log((self.conf.ALPHA * r0[i])/r1[i]))
        
        return SC_llr

    def binary_list_to_hex(self, binary_list):
        # Ensure the length of the list is a multiple of 4
        if len(binary_list) % 4 != 0:
            raise ValueError("The length of the binary list must be a multiple of 4.")
        
        # Group into chunks of 4 bits and convert to hex
        hex_string = ''.join(
            hex(int(''.join(map(str, binary_list[i:i+4])), 2))[2:]  # Convert binary to hex and remove "0x"
            for i in range(0, len(binary_list), 4)
        )
        return hex_string.lower()  # Convert to uppercase if desired

    def decode(self, frame):
    # compute sliding fft of the signal every 40 samples where the peak is 1 and the rest 0
        # lpf
        frame = self.butter(frame)
        return self.compute_hard_desicion_and_rs(frame, self.conf.WINDOW, [10,190])
        

    






    def decode_repetition_code(self, received, repeat):
        """
        Decodes a repetition-coded sequence by applying majority voting and calculates vote scores.
        """
        decoded = []
        scores = []
        for i in range(0, len(received), repeat):
            chunk = received[i:i+repeat]
            if len(chunk) == repeat:
                vote_score = max(chunk.count(0), chunk.count(1))  # Majority vote score
                decoded.append(int(np.round(np.mean(chunk))))
                scores.append(vote_score)
        return decoded, scores

    def find_best_sequence(self, received, known_seq, repeat):
        """
        Finds the best matching sequence in the received repetition-coded data based on the highest vote score.
        """
        best_index = -1
        best_score = -1
        best_match = []
        cnt = 0
        while len(received) >= repeat * len(known_seq):
            decoded, scores = self.decode_repetition_code(received, repeat)
            window = decoded[:len(known_seq)]
            avg_score = np.mean(scores[:len(known_seq)])
            
            if window == known_seq and avg_score > best_score:
                best_index = cnt
                best_score = avg_score
                best_match = window
            
            received = received[1:]  # Slide one step forward
            cnt += 1
        
        if best_index != -1:
            # print(f"Best match found at index {best_index} with average vote score {best_score}")
            return best_index
        else:
            # print("Known sequence not found")
            return None

    def detect_message_indices(self,received, preamble, repeat, cooefficient=2):
        preamble = preamble
        received_start = self.find_best_sequence(received[:len(preamble)*cooefficient], preamble[::repeat], repeat)
        received_end = self.find_best_sequence(received[-cooefficient*len(preamble):], preamble[::repeat], repeat)
        if received_start is None or received_end is None:
            return None, None
        return received_start + len(preamble), received_end + len(received)-(cooefficient*len(preamble))


    
    def ldpc_decode(self, llr_msg, llr_mac):
        msg_H_param = cc.get_5G_ldpc_params("msg: 1024 code_rate: "+str(np.round(self.conf.MSG_CODE_RATE,2))+".txt")
        mac_H_param = cc.get_5G_ldpc_params("msg: 256 code_rate: "+str(np.round(self.conf.MAC_CODE_RATE,2))+".txt")

        msg = self.soft_decision(llr_msg, H_param=msg_H_param)
        mac = self.soft_decision(llr_mac, H_param=mac_H_param)

        return msg, mac
    
    def bits_to_symbols(self, bit_list):
        bit_array = np.array(bit_list)
        slope = 9.5 * self.conf.TX_SPS/self.conf.WINDOW
        symbols = np.where(bit_array == 1, slope, -1*slope).astype(np.float32)
        return symbols
    
    def fsk_modulate(self, bits):

        bits_symbols = self.bits_to_symbols(bits)
        bits_upsampled = np.repeat(bits_symbols, self.conf.WINDOW) / np.sqrt(self.conf.WINDOW)
        bits_phase = np.cumsum(bits_upsampled)

        return np.exp(1j * bits_phase).astype(np.complex64)
    
    def string_to_bits(self, s):
        bits = []
        for char in s:
            bin_repr = format(ord(char), '08b')  # 8-bit binary
            bits.extend([int(b) for b in bin_repr])
        return bits






class PostProcessing:
    def __init__(self,  file:str, conf:config.CONFIG = config.CONFIG(), demod:Demodulation = Demodulation(), plot:bool = False):
        self.file = file
        self.conf = conf
        self.demod = demod

        self.IQsamples = np.fromfile(file, np.complex64)
        if plot:
            import matplotlib.pyplot as plt
            plt.figure(figsize=(20,10), dpi=80)
            plt.xticks(fontsize=30)
            plt.yticks(fontsize=30)
            plt.xlabel('Samples', fontsize=30)
            plt.ylabel('|IQ|^2', fontsize=30)
            plt.plot(np.abs(self.IQsamples)**2)
            plt.title("destination signal t0", fontsize=30)
            plt.show()

        self.TotalFramesIndex= self.frameFinder(self.IQsamples)


    def __len__(self):
        return len(self.TotalFramesIndex)


    def frameByIndex(self,index):
        return self.IQsamples[int(index[0]):int(index[1])]
    def frameByNumber(self,frame_nr:int):
        return self.frameByIndex(self.TotalFramesIndex[frame_nr])
        

    def frameFinder(self, samples):
        test_list = np.nonzero(np.abs(samples)**2)
        framesIndex = []
        for k, g in groupby(enumerate(test_list[0]), lambda ix: ix[0]-ix[1]):
            temp = list(map(itemgetter(1), g))
            if len(temp)< self.conf.MIN_FRAME_SIZE:
                print(temp[0],temp[-1], "diff:", temp[-1]-temp[0])
                continue 
            framesIndex.append([temp[0],temp[-1]])
        return np.array(framesIndex)
        


    def check(self): 
        #check minimum number of the frames
        ok = True
        nr_frame = len(self.TotalFramesIndex)
        print("\nnumber of frames: " + str(nr_frame))
        if  nr_frame < self.conf._minFrames or  nr_frame > self.conf._maxFrames:
            print("# Frame check failed ...")
            ok = False
        else:
            print("# Frame OK ...")
        # Check the file size
        size = os.path.getsize(self.file)
        print("\nfile size is: " + str(os.path.getsize(self.file)))
        if size < self.conf._minSize or size > self.conf._maxSize:
            print("Size check failed ...    ")
        else:
            print("Size OK .")
        return ok
    

    def bits_to_string(self, bit_list):
        chars = []
        for i in range(0, len(bit_list), 8):
            byte_bits = bit_list[i:i+8]
            if len(byte_bits) < 8:
                break
            val = 0
            for b in byte_bits:
                val = (val << 1) | b
            chars.append(chr(val))
        return "".join(chars)
    
    def binary_list_to_hex(self, binary_list):
        # Ensure the length of the list is a multiple of 4
        if len(binary_list) % 4 != 0:
            raise ValueError("The length of the binary list must be a multiple of 4.")
        
        # Group into chunks of 4 bits and convert to hex
        hex_string = ''.join(
            hex(int(''.join(map(str, binary_list[i:i+4])), 2))[2:]  # Convert binary to hex and remove "0x"
            for i in range(0, len(binary_list), 4)
        )
        return hex_string.lower()  # Convert to uppercase if desired

