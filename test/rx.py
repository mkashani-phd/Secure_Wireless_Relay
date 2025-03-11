import pymongo.collection
import uhd, time, config, os
from operator import itemgetter
from itertools import groupby
import scipy.signal 
from scipy.special import i0
import numpy as np
import pymongo
import datetime 
import copy
import channelCoding as cc
import hmac
import bson
import queue

import matplotlib.pyplot as plt

noise_batch_size_len = 2040
noise_nr_batches = 10


class RX:
    def __init__(self, conf:config.CONFIG = config.CONFIG(), usrp:uhd.usrp.MultiUSRP = uhd.usrp.MultiUSRP(args="serial=8000182")):
        self.conf = conf
        self.usrp = usrp

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
        batch_size, nr_batches = self._batch_init(streamer=  streamer, batch_size= None)
        recv_buffer = np.zeros((len(self.conf.CHANNEL), batch_size), dtype=np.complex64)
        metadata = uhd.types.RXMetadata()

        for chnl in self.conf.CHANNEL:
            self.usrp.set_rx_rate(self.conf.RX_RATE, chnl)
            self.usrp.set_rx_freq(uhd.libpyuhd.types.tune_request(self.conf.FREQ), chnl)
            if self.conf.RX_GAIN != "agc":
                self.usrp.set_rx_gain(self.conf.RX_GAIN, chnl)
        if self.conf.RX_GAIN == "agc":
            self.usrp.set_rx_agc(True, 0)
            print("AGC is enabled")

        self._start_stream(streamer = streamer,batch_size= batch_size)
        

        #updating file name if mimo
        if self.conf.MIMO:
            file1 = "_"+str(np.round(self.usrp.get_rx_freq(),2))+"_"+str(np.round(self.usrp.get_rx_rate(),2))+"_"+str(self.conf.RX_GAIN)+"_"+str(self.conf.ACQ_TIME) + "_"+ str(self.conf.IN_CHAMBER)+"_1.iq"
            file2 = "_"+str(np.round(self.usrp.get_rx_freq(),2))+"_"+str(np.round(self.usrp.get_rx_rate(),2))+"_"+str(self.conf.RX_GAIN)+"_"+str(self.conf.ACQ_TIME) + "_"+ str(self.conf.IN_CHAMBER)+"_2.iq"
            f1 = open(file1,"wb")
            f2 = open(file2,"wb")

            start = time.time()
            for i in range(nr_batches):
                streamer.recv(recv_buffer, metadata)
                # np.zeros(1).tofile(f)
                recv_buffer[0].tofile(f1)
                recv_buffer[1].tofile(f2)
            duration = time.time() - start
            print("\n Recorded Time: " + str(duration))
            # Stop Stream
            self._stop_stream(streamer=streamer, recv_buffer=recv_buffer)
            f1.close()
            f2.close()
            return streamer, file1, file2

        else:
            file = "_"+str(np.round(self.usrp.get_rx_freq(),2))+"_"+str(np.round(self.usrp.get_rx_rate(),2))+"_"+str(self.conf.RX_GAIN)+"_"+str(self.conf.ACQ_TIME) + "_"+ str(self.conf.IN_CHAMBER)+"_.iq"
            f = open(file,"wb")
            start = time.time()
            cnt = 4
            


            for i in range(nr_batches + noise_nr_batches):
                streamer.recv(recv_buffer, metadata)
                if i < noise_nr_batches:
                    recv_buffer[0].tofile(f)
                    continue
                elif i == noise_nr_batches:
                    np.zeros(10).tofile(f)
                    continue
                # recv_buffer[0] = self.butter(recv_buffer[0], cutoff=0.5, Fs=self.conf.RX_RATE)
                fft = np.abs(np.fft.fft(recv_buffer[0]))
                if np.sum(
                    np.concatenate(
                                [
                                fft[1:int(self.conf.FREQ_DEVIATION_PRECENTAGE*len(fft))], 
                                fft[int(1-self.conf.FREQ_DEVIATION_PRECENTAGE*batch_size):]
                                ]
                            )
                        ) > 1.4*2*self.conf.FREQ_DEVIATION_PRECENTAGE*np.sum(fft[int(self.conf.FREQ_DEVIATION_PRECENTAGE*batch_size): int(1-self.conf.FREQ_DEVIATION_PRECENTAGE*batch_size)]):
                    
                    recv_buffer[0].tofile(f) 
                    cnt = 0   
                else:
                    if (cnt:=cnt+1) < self.conf.LINIENT:
                       recv_buffer[0].tofile(f)  
                    else:
                        np.zeros(batch_size).tofile(f)

                

            duration = time.time() - start
            print("\n Recorded Time: " + str(duration))
            # Stop Stream
            self._stop_stream(streamer=streamer, recv_buffer=recv_buffer)
            f.close()
            return file
    
        








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
    
    
    


    def compute_hard_desicion_and_llr(self, signal, symbol_length, tone_bins, noise_level):

        offset = self.find_best_offset(signal, symbol_length, tone_bins)
        print("offset: ", offset)

        n_symbols = (len(signal) - offset) // symbol_length
        symbols = signal[offset:n_symbols * symbol_length + offset]
        

        hard_decision = []
        for i in range(0,len(symbols),symbol_length):
            peak,fft  = self.fft_max_peak(symbols[i:i+symbol_length],symbol_length)
            hard_decision.append(self.decision(peak=peak, threshold=symbol_length//2))

        

        fft_symbols = np.fft.fft(symbols.reshape(n_symbols, symbol_length), axis=1)
        # Extract the magnitudes at the two tone bins.
        # r0 corresponds to the first tone and r1 to the second tone.
        r0 = np.abs(fft_symbols[:, tone_bins[0]])
        r1 = np.abs(fft_symbols[:, tone_bins[1]])
        
        # Compute the amplitude factor from the signal energy.
        energy = np.average(np.abs(signal)**2)
        A = np.sqrt(energy)
        
        llrs = 2*A*(r1 - r0) / noise_level

        plt.figure(figsize=(10,5), dpi=80)
        plt.stem(llrs)
        plt.title("LLRs with superposition alpha = 1", fontsize=40)
        plt.xlabel("Symbol index", fontsize=20)
        plt.ylabel("LLR", fontsize=20)
        plt.show()

        
        return hard_decision, list(llrs)



    def decode(self, frame, noise):
    # compute sliding fft of the signal every 40 samples where the peak is 1 and the rest 0
        # lpf
        frame = self.butter(frame)
        return self.compute_hard_desicion_and_llr(frame, self.conf.WINDOW, [10,190], np.average(np.abs(self.butter(noise))**2))
        

    
    def getSNR(self, payload, noise):
        # calculate the frame power avoiding the preamble

        noise_power = np.average(np.abs(self.butter(noise))**2)
        payload_power = np.average(np.abs(self.butter(payload))**2)
        print("noise power: ", noise_power)
        print("payload power: ", payload_power)

        SNR = 10*np.log10( np.average( (payload_power  / noise_power) -1))
        return SNR





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
            print(f"Best match found at index {best_index} with average vote score {best_score}")
            return best_index
        else:
            print("Known sequence not found")
            return None

    def detect_message_indices(self,received, preamble, repeat, cooefficient=2):
        preamble = preamble
        received_start = self.find_best_sequence(received[:len(preamble)*cooefficient], preamble[::repeat], repeat)
        received_end = self.find_best_sequence(received[-cooefficient*len(preamble):], preamble[::repeat], repeat)
        if received_start is None or received_end is None:
            return None, None
        return received_start + len(preamble), received_end + len(received)-(cooefficient*len(preamble))



    
    def soft_decision(self, llr, H_param):
        # try:
        return cc.decode_llr(np.array(llr), H_param)[0]
        # except:
        #     return None
    
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
    def __init__(self,  file:str, conf:config.CONFIG = config.CONFIG(), demod:Demodulation = Demodulation()):
        self.file = file
        self.conf = conf
        self.demod = demod

        self.IQsamples = np.fromfile(file, np.complex64)

        import matplotlib.pyplot as plt
        # plt.figure(figsize=(20,10), dpi=80)
        # plt.plot(np.abs(self.IQsamples))
        # plt.show()

        self.TotalFramesIndex, self.TotalNoiseIndex = self.frameFinder(self.IQsamples)


        # self.zeroRemover(samples=self.IQsamples,framesIndex=framesIndex)  
        # self.tindx = np.fromfile(self.file+".tindx", dtype=int, sep= ',')
        # self.tindx = self.tindx.reshape(-1,2)

        

    def __len__(self):
        return len(self.TotalFramesIndex)


    def frameByIndex(self,index):
        return self.IQsamples[index[0]:index[1]]
    def frameByNumber(self,frame_nr:int):
        return self.frameByIndex(self.TotalFramesIndex[frame_nr])
    
    def noiseByIndex(self,index):
        return self.IQsamples[index[0]:index[1]]
    def noiseByNumber(self,noise_nr:int):
        return self.noiseByIndex(self.TotalNoiseIndex[noise_nr])

    def frameFinder(self, samples):
        plt.plot(np.abs(samples))
        test_list = np.nonzero(samples)
        noise_index = []
        framesIndex = []


        for k, g in groupby(enumerate(test_list[0]), lambda ix: ix[0]-ix[1]):
            temp = list(map(itemgetter(1), g))
            if len(temp)== noise_nr_batches* noise_batch_size_len: #hard coded but must be changed
                noise_index.append([temp[0],temp[-1]])
                frame = False
                continue
            elif len(temp)< self.conf.MIN_FRAME_SIZE:
                continue

            framesIndex.append([temp[0],temp[-1]])

        return np.array(framesIndex), np.array(noise_index*len(framesIndex))

    # def zeroRemover(self, samples, framesIndex):
    #     f = open(self.file,"wb")
    #     f_time_index= open(self.file+".tindx","wb")

    #     framesIndex.tofile(f_time_index,sep= ',')
    #     for i,j in framesIndex:
    #         frame = samples[i:j]
    #         frame.tofile(f)
    #         np.zeros(2,dtype=np.complex64).tofile(f)

    #     f.close()
    #     f_time_index.close()

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


    
    def push_to_db(self, collection: pymongo.collection.Collection):
        for indx in range(len(self.TotalFramesIndex)):
            print("\nProcessing frame: ", indx)

            insert_data = copy.deepcopy(self.conf.config)
            insert_data["TIME"] =  datetime.datetime.now()

            frame = self.frameByNumber(indx)
            noise = self.noiseByNumber(indx)


            # I = np.array(np.real(frame)).tobytes()
            # Q = np.array(np.imag(frame)).tobytes()
            # insert_data['I'], insert_data['Q'] = bson.binary.Binary(I), bson.binary.Binary(Q)
            # insert_data['frame_dtype'] = 'float'
            # insert_data['frame_shape'] = list(frame.shape)
 

            # noise_I = np.array(np.real(noise)).tobytes()
            # noise_Q = np.array(np.imag(noise)).tobytes()
            # insert_data['noise_I'] , insert_data['noise_Q'] = bson.binary.Binary(noise_I), bson.binary.Binary(noise_Q)
            # insert_data['noise_dtype'] = 'float'
            # insert_data['noise_shape'] = list(noise.shape)

            
            # calculate the frame power avoiding the preamble
            payload = frame[int(len(self.conf.PREAMBLE)*self.conf.PREAMBLE_REPEAT*self.conf.TX_SPS * 1.2) : int(-1*len(self.conf.PREAMBLE)*self.conf.PREAMBLE_REPEAT*self.conf.TX_SPS * 1.2)]
            insert_data['SNR'] = self.demod.getSNR(payload, noise)
            print("SNR: ", insert_data['SNR'])


            hard_decision,llr = self.demod.decode(frame, noise)
            
            index = self.demod.detect_message_indices(received=list(hard_decision), preamble=self.conf.PREAMBLE, repeat=self.conf.PREAMBLE_REPEAT)
            if index[0] is None or index[1] is None:
                print("preamble not found!")
                insert_data['error'] = 'premable not found!'
                collection.insert_one(insert_data)
                continue

            msg_hard_decision = hard_decision[index[0]:index[1]]
            insert_data['msg_hard_decision'] = self.bits_to_string(msg_hard_decision)
            print("msg: ", insert_data['msg_hard_decision'])


            msg_llr = llr[index[0]:index[1]]   
            insert_data['llr_msg'] = msg_llr

            msg_llr = [i /100 for i in msg_llr]
            msg_llr = [ i -100 if i >0 else i + 100 for i in msg_llr]
            plt.figure(figsize=(10,5), dpi=80)
            plt.stem(msg_llr)
            plt.title("LLRs with superposition alpha = 1", fontsize=40)
            plt.show()
            print("msg_llr: ", msg_llr)
            
            # insert_data['mac_hard_decision'] = self.binary_list_to_hex(mac[0:256])
            # insert_data['success_verification'] = hmac.new(self.conf.MAC_KEY.encode('utf-8'), msg=insert_data['msg_hard_decision'].encode('utf-8'), digestmod='sha256').hexdigest() == insert_data['mac_hard_decision']



            mac = self.demod.soft_decision(msg_llr, H_param=cc.get_5G_ldpc_params("msg: 256 code_rate: "+str(np.round(self.conf.MAC_CODE_RATE,2))+".txt"))
            if mac is None:
                print("ldpc decoding failed!")
                insert_data['error'] = 'ldpc decoding failed!'
                collection.insert_one(insert_data)
                continue
            insert_data['rceived_mac_ldpc_hex'] = self.binary_list_to_hex(mac[0:256])
            # insert_data['ldpc_success_verification'] = hmac.new(self.conf.MAC_KEY.encode('utf-8'), msg=insert_data['rceived_msg_ldpc_string'].encode('utf-8'), digestmod='sha256').hexdigest() == insert_data['rceived_mac_ldpc_hex']
            
            print('')
            print(insert_data['rceived_mac_ldpc_hex'])
            print('649cf0f60f9f7eef788f654956aa3c0186c8334e5f5f7780269a63ec2e292108')

            print('')

            collection.insert_one(insert_data)

        print("\nData pushed to the database ...")



### tests
def test():

    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    mydb = myclient["MAC_SUPERPOSITION"]

    rx = RX()
    files = rx.record()

    pp = PostProcessing(file=files)
    if(pp.check()):
        pp.push_to_db(collection = mydb['1D'])



if __name__ == "__main__":
    test()