
import numpy as np
import json
import os
import pymongo
from os import urandom




class ENC_CONFIG:
    def __init__(self):

        
        # Read the src/MongoDB/connectionString.json file relative to this file
        cache_file_path = os.path.join(os.path.dirname(__file__), "MongoDB","connectionString.json")
        try:
            with open(cache_file_path, "r") as file:
                self.connectionString = json.load(file)['connectionString']
        except FileNotFoundError:
            raise FileNotFoundError("MongoDB connection string file not found. Please use the rename the connectionString-template.json to connectionString.json in the MongoDB folder")

        

        client = pymongo.MongoClient(self.connectionString)
        db = client["encryption_config"]
        collection = db["encryption_config"]
        self.enc_config = collection.find_one()
        if self.enc_config is None:
            collection.insert_one(self.create_default_config())
            self.enc_config = collection.find_one()

    
        self.PAYLOAD = self.enc_config['PAYLOAD']
        self.MSG_CODERATE = self.enc_config['MSG_CODERATE']

        self.KEY = self.enc_config['KEY']
        self.IV = self.enc_config['IV']
        self.COUNTER = self.enc_config['COUNTER']

    def _internal_update(self):
        self.__init__()



    def update_config(self, enc_config:dict|tuple):
        client = pymongo.MongoClient(self.connectionString)
        db = client["encryption_config"]
        collection = db["encryption_config"]
        if isinstance(enc_config, dict):
            collection.update_one({}, {"$set": enc_config}, upsert=True)
        elif isinstance(enc_config, tuple) or isinstance(enc_config, list):
            key, value = enc_config
            collection.update_one({}, {"$set": {key:value}}, upsert=True)
        self.__init__()

        
        
    def reset_to_default_config(self):
        client = pymongo.MongoClient(self.connectionString)
        db = client["encryption_config"]
        collection = db["encryption_config"]
        collection.delete_many({})
        self.update_config(self.create_default_config())
        
    def create_default_config(self):
        enc_config = {}


        ########### APPLICATION LAYER PARAMETERS ############
        PAYLOAD = "This message is the default payload for the tests, and is 256 * 8 bits long. It will be superposed with a random key, which makes the double-encrypted Ciphertext. This message is the default payload for the tests, and is 256 * 8 bits long. It will be super"

        enc_config['PAYLOAD'] = PAYLOAD
        enc_config['MSG_CODERATE'] = 1/2

        enc_config['KEY'] = urandom(32).hex()
        enc_config['IV'] = urandom(16).hex()
        enc_config['COUNTER'] = 0

        return enc_config





        

        


def test():
    conf = ENC_CONFIG()

    conf.update_config(('COUNTER', conf.COUNTER+1))

    import encryption, utils

    hex_rand, int_rand = encryption.AESCTRAligned.get_range(key=bytes.fromhex(conf.KEY), 
                                        iv=bytes.fromhex(conf.IV),         
                                        chunk_bits=len(conf.PAYLOAD)*8,
                                        index=conf.COUNTER,
                                        return_int=True)

    print("msg length:", len(utils.string_to_bits(conf.PAYLOAD)),"random key length:", len(utils.hex_to_bits(hex_rand.hex()))) 
    print("counter_before", conf.COUNTER)
    conf.update_config(['COUNTER', conf.COUNTER+1])
    print("counter_after", conf.COUNTER)
    
if __name__ == "__main__":
    test()




