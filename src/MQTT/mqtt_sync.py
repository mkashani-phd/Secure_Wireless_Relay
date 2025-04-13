import paho.mqtt.client as mqtt
import time
import json
from .. import config

class MQTTBase:
    def __init__(self, conf: config.CONFIG, role: str, phase:int = 1, verbose: bool = False):
        self.ERROR = False 
        self.verbose = verbose

        assert role.lower() in ['source', 'relay', 'destination'], "role must be 'destination', 'relay', or 'source'"
        self.role = role.lower()
        assert phase in [1, 2], "phase must be 1 or 2"
        self.phase = phase
        
        self.BROKER = conf.MQTT['BROKER']
        self.PORT = conf.MQTT['PORT']
        self.USERNAME = conf.MQTT['AIO_USERNAME']
        self.AIO_KEY = conf.MQTT['AIO_KEY']

        # the topics for the MQTT for Adafruit IO must have this format:
        # <username>/feeds/<feed_name>
        self.begin_topic = f"{self.USERNAME}/feeds/begin"
        self.ready_topic = f"{self.USERNAME}/feeds/ready"
        self.error_topic = f"{self.USERNAME}/feeds/error"

        self.client = mqtt.Client()
        self.client.username_pw_set(self.USERNAME, self.AIO_KEY)

class MQTT_RX(MQTTBase):
    def __init__(self, conf: config.CONFIG, role: str, phase:int = 1, verbose: bool = False):
        super().__init__(conf, role, phase, verbose)
        self.begin_received = False

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(self.BROKER, self.PORT, 60)
        # Start the network loop once in the constructor.

        if self.role == 'relay':
            assert self.phase == 1, "phase must be 1 for 'relay' in RX mode"


        self.client.loop_start()
    

    def on_connect(self, client, userdata, flags, rc):
        print(f"[{self.role.upper()} RX] Connected. Subscribing to '{self.begin_topic}'") if self.verbose else None 
        self.client.subscribe(self.begin_topic)
        self.client.subscribe(self.error_topic)

    def on_message(self, client, userdata, msg: mqtt.MQTTMessage):
        if msg.topic == self.error_topic:
            print(f"[{self.role.upper()} RX] Detected Error: {msg.payload.decode()}") if self.verbose else None
            self.ERROR = True
            return
        if msg.topic == self.begin_topic:
            print(f"[{self.role.upper()} RX] Received 'begin'") if self.verbose else None
            self.begin_received = True

    def send_ready_and_wait_for_begin(self):
        # Continuously publish "ready" until we detect a "begin" message.

        print(f"[{self.role.upper()} RX] Publishing 'ready' for phase {self.phase}") if self.verbose else None
        payload = {'phase': self.phase, 'role': self.role}

        try:
            while not self.begin_received and not self.ERROR:
                self.client.publish(topic=self.ready_topic, payload=json.dumps(payload), qos=1)
                time.sleep(.1)
        except:
            self.client.publish(topic=self.error_topic, payload=f'{self.role} error', qos=1)
            self.ERROR = True
            print(f"[{self.role.upper()} RX] publishing 'error'") if self.verbose else None
        
        self.client.disconnect()    
        return False if self.ERROR else True



class MQTT_TX(MQTTBase):
    def __init__(self, conf: config.CONFIG, role: str, phase:int = 1, verbose: bool = False):
        super().__init__(conf, role, phase, verbose)
        self.ready_status = {
                                1:{'destination': False, 'relay': False},
                                2:{'destination': False}
                            }
        
        if self.role == 'relay':
            assert self.phase == 2, "phase must be 2 for 'relay' in TX mode"
        elif self.role == 'source':
            assert self.phase == 1, "phase must be 1 for 'source' in TX mode"

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(self.BROKER, self.PORT, 60)


    def on_connect(self, client, userdata, flags, rc):
        print(f"[{self.role.upper()} TX] Connected. Subscribing to '{self.ready_topic}'") if self.verbose else None
        self.client.subscribe(self.ready_topic)
        self.client.subscribe(self.error_topic)

    def on_message(self, client, userdata, msg: mqtt.MQTTMessage):
        if msg.topic == self.error_topic:
            print(f"[{self.role.upper()} TX] Detected Error: {msg.payload.decode()}") if self.verbose else None
            self.ERROR = True
            self.client.disconnect()
            return
        if msg.topic != self.ready_topic:
            print(f"[{self.role.upper()} TX] Unknown topic: {msg.topic}") if self.verbose else None
            return
        try:
            msg = json.loads(msg.payload.decode())
            role = msg['role']
            phase = msg['phase']
        except json.JSONDecodeError:
            print(f"[{self.role.upper()} TX] Error decoding JSON message") if self.verbose else None
            return
        
        if self.phase != phase and self.role == 'relay':
            print(f"[{self.role.upper()} TX] Received 'ready' from {role} in phase {phase}, but {self.role} is in phase {self.phase}") if self.verbose else None
            self.client.publish(topic=self.error_topic, payload=f'{self.role} phase mismatch error', qos=1)
            return
        
        if not self.ready_status[phase][role]:
            self.ready_status[phase][role] = True
            print(f"[{self.role.upper()} TX] Received 'ready' from {role} for phase {phase}") if self.verbose else None

        if self.role == 'source':
            if all(self.ready_status[1].values()):
                self.send_begin()
                self.client.disconnect()
        elif self.role == 'relay':
            if all(self.ready_status[2].values()):
                self.send_begin()
                self.client.disconnect()


    def wait_for_all_ready(self,sleep_time=1):

        try:
            self.client.loop_forever()
        except:
            self.client.publish(topic=self.error_topic, payload=f'{self.role} error', qos=1)
            self.ERROR = True
            print(f"[{self.role.upper()} TX] publishing 'error'") if self.verbose else None

        if self.ERROR:
            return False
    
        print(f"[{self.role.upper()} TX] All nodes ready") if self.verbose else None
        time.sleep(sleep_time)
        return True

    def send_begin(self):
        print(f"[{self.role.upper()} TX] Sending 'begin'") if self.verbose else None
        self.client.publish(self.begin_topic, "start", qos=1)

