import pymongo.collection
import uhd, time, config, os
from operator import itemgetter
from itertools import groupby
import numpy as np
import pymongo
import datetime 
import copy
import channelCoding as cc
import hmac


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
            for i in range(nr_batches):
                streamer.recv(recv_buffer, metadata)
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
                    recv_buffer[0].tofile(f) if (cnt:=cnt+1) < self.conf.LINIENT else np.zeros(batch_size, dtype=np.complex64).tofile(f)
                

            duration = time.time() - start
            print("\n Recorded Time: " + str(duration))
            # Stop Stream
            self._stop_stream(streamer=streamer, recv_buffer=recv_buffer)
            f.close()
            return file
    
        


class Demodulation:
    def __init__(self, conf:config.CONFIG = config.CONFIG()):
        self.conf = conf
        

    def fft_max_peak(self, frame,window):
        fft = np.fft.fftshift(np.fft.fft(frame[:window]))
        peak = np.argmax(np.abs(fft))
        return peak,fft
    
    def decision(self, peak, threshold):
        return 0 if peak < threshold else 1
    
    def llr_from_fft(self, fft):
        E_f1 = np.sum(np.power(np.abs(fft[len(fft)//2 - int(len(fft)*self.conf.FREQ_DEVIATION_PRECENTAGE)]),1))
        E_f2 = np.sum(np.power(np.abs(fft[len(fft)//2 + int(len(fft)*self.conf.FREQ_DEVIATION_PRECENTAGE)]),1))
        # llr for BFSK modulation is given by the following formula
        return (E_f1-E_f2)


    def decode(self, frame):
    # compute sliding fft of the signal every 40 samples where the peak is 1 and the rest 0
        res= []
        llr = []
        window = slide = self.conf.WINDOW
        
        # res.append(self.decision(peak = peak, threshold=window//2))
        for i in range(0,len(frame),slide):
            peak,fft  = self.fft_max_peak(frame[i:i+window],window)
            res.append(self.decision(peak=peak, threshold=window//2))
            llr.append(self.llr_from_fft(fft))
        return res, llr

    def find_subarray(self, data, sub):
        n, m = len(data), len(sub)
        if m == 0:
            return 0  # Edge case: empty subarray
        for i in range(n - m + 1):
            if data[i:i+m] == sub:
                return i
        return -1

    def get_frame(self, data, include_markers=False):
        preamble = self.conf.PREAMBLE
        postamble = self.conf.PREAMBLE[36::-1]
        # 1. Find the first occurrence of the preamble.
        start_idx = self.find_subarray(data, preamble)
        if start_idx == -1:
            return None  # Preamble not found

        # 2. Find the first occurrence of the postamble, starting after preamble ends.
        end_search_start = start_idx + len(preamble)
        end_idx = self.find_subarray(data[end_search_start:], postamble)
        if end_idx == -1:
            return None  # Postamble not found

        # Adjust end_idx relative to the original data
        end_idx += end_search_start

        if include_markers:
            # Return from start of preamble to end of postamble
            return data[start_idx : end_idx + len(postamble)], (start_idx, end_idx + len(postamble))
        else:
            # Return only what's between the preamble and postamble
            return data[start_idx + len(preamble) : end_idx], (start_idx + len(preamble), end_idx)
        


    def get_llr(self, frame):
        res,llr = self.decode(frame)
        try:
            frame, index = self.get_frame(res)
        except:
            print("premable not found!")
            return None, None
        # msg_scale = cc.pick_bg2_file_for_Z()
        # mac_scale = int(1/self.conf.MAC_CODE_RATE)
        llr_msg = llr[index[0]:index[0]+4352]
        llr_mac = llr[index[0]+4352:index[0]+4352+1088]
        msg = res[index[0]:index[0]+4352]
        mac = res[index[0]+4352:index[0]+4352+1088]
        return msg, mac, llr_msg, llr_mac
    
    def soft_decision(self, llr, H_param):
        return cc.decode_llr(np.array(llr), H_param)[0]
    def ldpc_decode(self, llr_msg, llr_mac):
        msg_H_param = cc.get_5G_ldpc_params("msg: 1024 code_rate: "+str(np.round(self.conf.MSG_CODE_RATE,2))+".txt")
        mac_H_param = cc.get_5G_ldpc_params("msg: 256 code_rate: "+str(np.round(self.conf.MAC_CODE_RATE,2))+".txt")
        msg = self.soft_decision(llr_msg, H_param=msg_H_param)
        mac = self.soft_decision(llr_mac, H_param=mac_H_param)
        return msg, mac





class PostProcessing:
    def __init__(self,  file:str, conf:config.CONFIG = config.CONFIG(), demod:Demodulation = Demodulation()):
        self.file = file
        self.conf = conf
        self.demod = demod

        self.IQsamples = np.fromfile(file, np.complex64)

        self.zeroRemover(samples=self.IQsamples,framesIndex=self.frameFinder(self.IQsamples))  

        self.tindx = np.fromfile(self.file+".tindx", dtype=int, sep= ',')
        self.TotalFramesIndex = self.frameFinder(self.IQsamples)
        self.tindx = self.tindx.reshape(-1,2)

    def __len__(self):
        return len(self.TotalFramesIndex)

    def indexByNumber(self,num):
        return self.TotalFramesIndex[num]
    def frameByIndex(self,index):
        return self.IQsamples[index[0]:index[1]]

    def frameByNumber(self,frame_nr:int):
        return self.frameByIndex(self.TotalFramesIndex[frame_nr])

    def frameFinder(self, samples):
        test_list = np.nonzero(samples)
        framesIndex = []
        for k, g in groupby(enumerate(test_list[0]), lambda ix: ix[0]-ix[1]):
            temp = list(map(itemgetter(1), g))
            if len(temp)< self.conf.MIN_FRAME_SIZE:
                continue
            framesIndex.append([temp[0],temp[-1]])
        return np.array(framesIndex)

    def zeroRemover(self, samples, framesIndex):
        f = open(self.file,"wb")
        f_time_index= open(self.file+".tindx","wb")
        framesIndex.tofile(f_time_index,sep= ',')
        for i,j in framesIndex:
            frame = samples[i:j]
            #if len(samples)< thresh:
                # continue
            frame.tofile(f)
            np.zeros(2,dtype=np.complex64).tofile(f)

        f.close()
        f_time_index.close()

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
            insert_data = copy.deepcopy(self.conf.config)
            insert_data["TIME"] =  datetime.datetime.now()
            frame = self.frameByNumber(indx)
            # insert_data['I'], insert_data['Q'] = np.array(np.real(frame), dtype=np.int8).tolist(), np.array(np.imag(frame), dtype=np.int8).tolist()
            msg, mac, msg_llr, mac_llr = self.demod.get_llr(frame)
  
            if msg_llr is None or mac_llr is None:
                print("preamble not found!")
                insert_data['error'] = 'premable not found!'
                collection.insert_one(insert_data)
                continue
            insert_data['msg_hard_decision'] = self.bits_to_string(msg[0:1024])
            insert_data['mac_hard_decision'] = self.binary_list_to_hex(mac[0:256])
            insert_data['success_verification'] = hmac.new(self.conf.MAC_KEY.encode('utf-8'), msg=insert_data['msg_hard_decision'].encode('utf-8'), digestmod='sha256').hexdigest() == insert_data['mac_hard_decision']


            insert_data['llr_msg'] = msg_llr
            insert_data['llr_mac'] = mac_llr

            msg, mac = self.demod.ldpc_decode(msg_llr, mac_llr)
            insert_data['rceived_msg_ldpc_string'] = self.bits_to_string(msg[0:1024])
            insert_data['rceived_mac_ldpc_hex'] = self.binary_list_to_hex(mac[0:256])
            insert_data['ldpc_success_verification'] = hmac.new(self.conf.MAC_KEY.encode('utf-8'), msg=insert_data['rceived_msg_ldpc_string'].encode('utf-8'), digestmod='sha256').hexdigest() == insert_data['rceived_mac_ldpc_hex']

            print("msg: ", insert_data['rceived_msg_ldpc_string'], "\nsuccess MAC: ", insert_data['rceived_mac_ldpc_hex'])
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