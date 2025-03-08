import yaml
import numpy as np
import hmac
import time

# a 1024 bit message
PAYLOAD   = "This message is the default payload for the tests, and is 1024 bits long. It will be superposed with HMAC tag, that is 256 bits!"

class CONFIG:
    def __init__(self, config_yaml_path = None):

        if config_yaml_path == None:
            try:
                self.load_config(config_yaml_path = "config.yaml")
            except:
                try:
                    self.load_default_config()
                except:
                    self.create_default_config()
                    self.load_default_config()
            return
        
        with open(config_yaml_path, 'r') as stream:
            try:
                self.config = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)
        self.MAC_KEY = self.config['MAC_KEY']

        self.FREQ = self.config['FREQ']
        self.TX_RATE = self.config['TX_RATE']
        self.TX_GAIN = self.config['TX_GAIN']
        self.TX_SPS = self.config['TX_SPS']



        self.RX_RATE = self.config['RX_RATE']
        self.RX_GAIN = self.config['RX_GAIN']
        self.LPF_CUTOFF = self.config['LPF_CUTOFF']
        self.ACQ_TIME = self.config['ACQ_TIME']
        self.MIMO = self.config['MIMO']
        self.CHANNEL = [0] if not self.MIMO else [0,1]
        self.LINIENT = self.config['LINIENT']



        self.IN_CHAMBER = self.config['IN_CHAMBER']

        self.PREAMBLE = self.config['PREAMBLE']
        self.PREAMBLE_REPEAT = self.config['PREAMBLE_REPEAT']
        self.PAYLOAD = self.config['PAYLOAD']
        self.MSG_CODE_RATE = self.config['MSG_CODE_RATE']
        self.MAC_CODE_RATE = self.config['MAC_CODE_RATE']
        self.SUPERPOSED = self.config['SUPERPOSED']

        self.MIN_FRAME_SIZE = self.config['MIN_FRAME_SIZE']
        self.WINDOW = self.config['WINDOW']
        self.FREQ_DEVIATION_PRECENTAGE = self.config['FREQ_DEVIATION_PRECENTAGE']

        self._minSize = self.config['_minSize']
        self._maxSize = self.config['_maxSize']
        self._minFrames = self.config['_minFrames']
        self._maxFrames = self.config['_maxFrames']

    def update_config(self, config, config_yaml_path = "config.yaml"):
        with open(config_yaml_path, 'w') as stream:
            try:
                yaml.dump(config, stream)
            except yaml.YAMLError as exc:
                print(exc)
        self.__init__(config_yaml_path)
    
    def load_config(self, config_yaml_path):
        with open(config_yaml_path, 'r') as stream:
            try:
                self.config = yaml.safe_load(stream)
                stream.close()
            except yaml.YAMLError as exc:
                print(exc)
        self.__init__(config_yaml_path)
        
    def load_default_config(self, default_config_yaml_path = "default_config.yaml"):
        with open(default_config_yaml_path, 'r') as stream:
            try:
                self.config = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)
                return None
        self.__init__(default_config_yaml_path)

    def create_default_config(self,default_config_yaml_path = "default_config.yaml"):
        config = {}
        config['MAC_KEY'] = "key"
        config['FREQ'] = 1.9e9

        config['TX_RATE'] = 1e6
        config['TX_GAIN'] = 50 # max gain 89.8
        config['TX_SPS'] = 40

        config['RX_RATE'] = 5e6
        config['RX_GAIN'] = 50 # Automatic Gain Control "agc" max gain 76
        # aviod the agc if the SNR calculation is needed
        config['LPF_CUTOFF'] = 3e5

        config['LINIENT'] = 10
        config['MIMO'] = False
        config['ACQ_TIME'] = 5
        config['IN_CHAMBER'] = False


        # repeat the preamble 10 times
        PREAMBLE_REPEAT = 15
        # the reason for long preamble is the power warm up on the SDR
        PREAMBLE =  [+1, +1, +1, +1, +1, 0, 0, +1, +1, 0, +1, 0, +1]
        PREAMBLE = np.repeat(PREAMBLE, PREAMBLE_REPEAT).tolist()

        config['PREAMBLE'] = PREAMBLE
        config['PREAMBLE_REPEAT'] = PREAMBLE_REPEAT
        config['PAYLOAD'] = PAYLOAD
        config['MSG_CODE_RATE'] = 1/3
        config['MAC_CODE_RATE'] = 1/3
        config['SUPERPOSED'] = False


        # detection and decoding parameters
        config['MIN_FRAME_SIZE'] = 7.6*len(PAYLOAD)* config['TX_SPS'] * config['RX_RATE']/config['TX_RATE']

        config['WINDOW'] = int(config['TX_SPS'] * config['RX_RATE']/config['TX_RATE'])
        config['FREQ_DEVIATION_PRECENTAGE'] = 5/100 



        config['_minSize'] = 1e3
        config['_maxSize'] = 99.99e6
        config['_minFrames'] = 2
        config['_maxFrames'] = 40

        self.update_config(config, config_yaml_path=default_config_yaml_path)













def test():
    conf = CONFIG()
    
if __name__ == "__main__":
    test()




