import yaml
import numpy as np
import json
import os




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

        # Read the src/MQTT/MQTT.json file relative to this file
        cache_file_path = os.path.join(os.path.dirname(__file__), "MQTT","MQTT.json")
        try:
            with open(cache_file_path, "r") as file:
                self.MQTT = json.load(file)
        except FileNotFoundError:
            print("MQTT.json file not found. Please use the rename the MQTT-template.json to MQTT.json in the MQTT folder")
            print("Using MQTT is not necessary for the tests and other synchronization can be used!")
            self.MQTT = None

        # Read the src/MongoDB/connectionString.json file relative to this file
        cache_file_path = os.path.join(os.path.dirname(__file__), "MongoDB","connectionString.json")
        try:
            with open(cache_file_path, "r") as file:
                self.connectionString = json.load(file)['connectionString']
        except FileNotFoundError:
            print("connectionString.json file not found. Please use the rename the connectionString-template.json to connectionString.json in the MongoDB folder")
            print("Using MongoDB is not necessary for the tests and other method such as files or databases can be used!")
            self.connectionString = None
         

        self.SOURCE = self.config['SOURCE']
        self.DESTINATION = self.config['DESTINATION']
        self.RELAY = self.config['RELAY']

        self.MAC_KEY = self.config['MAC_KEY']

        self.FREQ = self.config['FREQ']
        self.TX_RATE = self.config['TX_RATE']
        self.TX_GAIN = self.config['TX_GAIN']
        self.TX_RELAY_GAIN = self.config['TX_RELAY_GAIN']
        self.TX_PAYLOAD_POWER_SCALE = self.config['TX_PAYLOAD_POWER_SCALE']
        self.TX_SPS = self.config['TX_SPS']



        self.RX_RATE = self.config['RX_RATE']
        self.RX_GAIN = self.config['RX_GAIN']
        self.RX_RELAY_GAIN = self.config['RX_RELAY_GAIN']
        self.LPF_CUTOFF = self.config['LPF_CUTOFF']
        self.ACQ_TIME = self.config['ACQ_TIME']
        self.MIMO = self.config['MIMO']
        self.CHANNEL = [0]
        # self.THRESHOLD_DEST = self.config['THRESHOLD_Dest']
        # self.THRESHOLD_RELAY = self.config['THRESHOLD_Relay']


        self.IN_CHAMBER = self.config['IN_CHAMBER']

        self.PREAMBLE = self.config['PREAMBLE']
        self.POSTAMBLE = self.config['POSTAMBLE']
        self.PREAMBLE_REPEAT = self.config['PREAMBLE_REPEAT']
        self.PAYLOAD = self.config['PAYLOAD']
        self.MSG_CODE_RATE = self.config['MSG_CODE_RATE']
        self.MAC_CODE_RATE = self.config['MAC_CODE_RATE']
        self.SUPERPOSED = self.config['SUPERPOSED']
        self.ALPHA = self.config['ALPHA']

        self.MIN_FRAME_SIZE = self.config['MIN_FRAME_SIZE']
        self.WINDOW = self.config['WINDOW']

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

        ########### APPLICATION LAYER PARAMETERS ############
        PAYLOAD = "This message is the default payload for the tests, and is 1088 bits long. It will be superposed with MAC tag of 256 bits with Rate= 1/3?This message is the default payload for the tests, and is 1088 bits long. It will be superposed with MAC tag of 256 bits with Rate= 1/3?This message is the default payload for the tests, and is 1088 bits long. It will be superposed with MAC tag of 256 bits with Rate= 1/3?"
        PREAMBLE_REPEAT = 10
        PREAMBLE =  [1, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1]
        POSTAMBLE =  [0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 1, 0]
        PREAMBLE = np.repeat(PREAMBLE, PREAMBLE_REPEAT).tolist()
        POSTAMBLE = np.repeat(POSTAMBLE, PREAMBLE_REPEAT).tolist()

        config['PREAMBLE'] = PREAMBLE
        config['POSTAMBLE'] = POSTAMBLE
        config['PREAMBLE_REPEAT'] = PREAMBLE_REPEAT
        config['PAYLOAD'] = PAYLOAD
        config['MSG_CODE_RATE'] = 1
        config['MAC_CODE_RATE'] = 1/3
        config['SUPERPOSED'] = False
        ############## PHY LAYER PARAMETERS #################
        config['ACQ_TIME'] = 3.0

        
        config['ALPHA'] = 0.2


        config['MAC_KEY'] = "key"
        config['FREQ'] = 1.9e9
        config['TX_SPS'] = 40
        config['TX_RATE'] = 1e6
        config['RX_RATE'] = 5e6
        config['LPF_CUTOFF'] = 3e5 

        config['MIN_FRAME_SIZE'] = (len(PAYLOAD)/config['MSG_CODE_RATE']+2*len(PREAMBLE)*PREAMBLE_REPEAT)* config['TX_SPS'] * config['RX_RATE']/config['TX_RATE']
        config['WINDOW'] = int(config['TX_SPS'] * config['RX_RATE']/config['TX_RATE'])

        ########## USRP PARAMETERS ######################
        config['SOURCE'] = "8000169"
        config['TX_GAIN'] = 60 
        config['TX_PAYLOAD_POWER_SCALE'] = 0.01

        config['DESTINATION'] = "8000182"
        config['RX_GAIN'] = 50.0 




        config['RELAY'] = "8000122" 
        config['TX_RELAY_GAIN'] = config['TX_GAIN'] 
        config['RX_RELAY_GAIN'] = config['RX_GAIN'] 


        
        config['MIMO'] = False
        config['IN_CHAMBER'] = False


        config['_minSize'] = 1e3
        config['_maxSize'] = 99.99e6
        config['_minFrames'] = 1
        config['_maxFrames'] = 40

        self.update_config(config, config_yaml_path=default_config_yaml_path)


def test():
    conf = CONFIG()
    
if __name__ == "__main__":
    test()




