
import numpy as np
import json
import os
import pymongo




class CONFIG:
    def __init__(self):

        

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
            raise FileNotFoundError("MongoDB connection string file not found. Please use the rename the connectionString-template.json to connectionString.json in the MongoDB folder")

        

        client = pymongo.MongoClient(self.connectionString)
        db = client["config"]
        collection = db["config"]
        self.config = collection.find_one()
        if self.config is None:
            collection.insert_one(self.create_default_config())
            self.config = collection.find_one()


        self.MongoDB_Collection_name = self.config['MongoDB_Collection_name']

        self.SOURCE = self.config['SOURCE']
        self.DESTINATION = self.config['DESTINATION']
        self.RELAY = self.config['RELAY']

        self.TX_REPEAT = self.config['TX_REPEAT']
        self.RX_MAX_MAGNITUDE_THRESHOLD_SCALE = self.config['RX_MAX_MAGNITUDE_THRESHOLD_SCALE']

        self.MAC_KEY = self.config['MAC_KEY']
        self.MAC_SHA = self.config['MAC_SHA']

        if self.MAC_SHA == 'sha256':
            self.TAG_SIZE = 256

        self.MAC_REP = self.config['MAC_REP']
        self.MAC_LDPC = self.config['MAC_LDPC']
        self.MAC_CODE_RATE = self.MAC_REP  *  self.MAC_LDPC
        self.MSG_CODE_RATE = self.config['MSG_CODE_RATE']
        
        self.MAC_SIZE_ENCODED = self.TAG_SIZE/self.MAC_CODE_RATE
        self.MSG_SIZE:float = (self.TAG_SIZE/self.MAC_CODE_RATE * self.MSG_CODE_RATE ) - self.TAG_SIZE

        if self.MSG_SIZE.is_integer():
            self.MSG_SIZE = int(self.MSG_SIZE)
            if self.MSG_SIZE %8 == 0:
                self.PAYLOAD = self.config['PAYLOAD'][:self.MSG_SIZE//8]
            else:
                raise "message size is not divisible to 8 which is necessary for char conversion"
        else:
            raise "Error! the combination is not producing the message size to be an intiger"
        


        self.FREQ = self.config['FREQ']
        self.FREQ_DEV = self.config['FREQ_DEV']  
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

        self.PREAMBLE_REPEAT = self.config['PREAMBLE_REPEAT']

        self.PREAMBLE =  np.repeat(self.config['PREAMBLE'], self.config['PREAMBLE_REPEAT']).tolist()
        self.POSTAMBLE =  np.repeat(self.config['POSTAMBLE'], self.config['PREAMBLE_REPEAT']).tolist()



        self.SUPERPOSED = self.config['SUPERPOSED']
        self.ALPHA = self.config['ALPHA']

        self.MIN_FRAME_SIZE =((len(self.PAYLOAD*8)/self.config['MSG_CODE_RATE'])+2*len(self.PREAMBLE ))* self.config['TX_SPS'] * self.config['RX_RATE']/self.config['TX_RATE']
        self.WINDOW = int(self.config['TX_SPS'] * self.config['RX_RATE']/self.config['TX_RATE'])

        self._minSize = self.config['_minSize']
        self._maxSize = self.config['_maxSize']
        self._minFrames = self.config['_minFrames']
        self._maxFrames = self.config['_maxFrames']

    def update_config(self, config):
        client = pymongo.MongoClient(self.connectionString)
        db = client["config"]
        collection = db["config"]
        collection.update_one({}, {"$set": config}, upsert=True)

        
        
    def reset_to_default_config(self):
        client = pymongo.MongoClient(self.connectionString)
        db = client["config"]
        collection = db["config"]
        collection.delete_many({})
        self.update_config(self.create_default_config())
        
    def create_default_config(self):
        config = {}

        config['MongoDB_Collection_name'] = "SIC_MAC"

        ########### APPLICATION LAYER PARAMETERS ############
        PAYLOAD = "This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0.This message is the default payload for the tests, and is 5504 bits long. It will be superposed with MAC tag of 256 bits with 1/45 code rate, which makes the codeword length of 11520.0."
        config['PREAMBLE'] = [1, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1]
        config['POSTAMBLE'] = [1, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1]

        config['PREAMBLE_REPEAT'] = 17
        config['PAYLOAD'] = PAYLOAD

   
        config['MAC_SHA'] = "sha256"

        config['MAC_REP'] = 1/19
        config['MAC_LDPC'] = 1/3
        config['MSG_CODE_RATE'] = 1/2



      


        config['SUPERPOSED'] = False
        ############## PHY LAYER PARAMETERS #################
        config['ACQ_TIME'] = 2.0
        config['TX_REPEAT'] = 3
        config['RX_MAX_MAGNITUDE_THRESHOLD_SCALE'] = 0.5
        

        
        config['ALPHA'] = 0.05


        config['MAC_KEY'] = "key"
        config['FREQ'] = 1.9e9
        config['FREQ_DEV'] = 1e5
        config['TX_SPS'] = 100
        config['TX_RATE'] = 1e7
        config['RX_RATE'] = 2e7
        config['LPF_CUTOFF'] = 6e5 




        ########## USRP PARAMETERS ######################
        config['SOURCE'] = "8000169"
        config['TX_GAIN'] = 62 
        config['TX_PAYLOAD_POWER_SCALE'] = 0.003

        config['DESTINATION'] = "8000182"
        config['RX_GAIN'] = 20.0 




        config['RELAY'] = "8000122" 
        config['TX_RELAY_GAIN'] = config['TX_GAIN'] 
        config['RX_RELAY_GAIN'] = config['RX_GAIN'] 


        
        config['MIMO'] = False
        config['IN_CHAMBER'] = False


        config['_minSize'] = 1e3
        config['_maxSize'] = 99.99e6
        config['_minFrames'] = 1
        config['_maxFrames'] = 100

        return config

        


def test():
    conf = CONFIG()
    
if __name__ == "__main__":
    test()




