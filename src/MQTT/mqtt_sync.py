import paho.mqtt.client as mqtt
import time
from .. import config

class MQTTBase:
    def __init__(self, conf: config.CONFIG, role: str):
        assert role.lower() in ['source', 'relay', 'destination'], "role must be 'destination', 'relay', or 'source'"
        self.role = role.lower()
        self.BROKER = conf.MQTT['BROKER']
        self.PORT = conf.MQTT['PORT']
        self.USERNAME = conf.MQTT['AIO_USERNAME']
        self.AIO_KEY = conf.MQTT['AIO_KEY']

        # the topics for the MQTT for Adafruit IO must have this format:
        # <username>/feeds/<feed_name>
        self.begin_topic = f"{self.USERNAME}/feeds/begin"
        self.ready_topic = f"{self.USERNAME}/feeds/ready"

        self.client = mqtt.Client()
        self.client.username_pw_set(self.USERNAME, self.AIO_KEY)

class MQTT_RX(MQTTBase):
    def __init__(self, conf: config.CONFIG, role: str):
        super().__init__(conf, role)
        self.begin_received = False

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(self.BROKER, self.PORT, 60)
        # Start the network loop once in the constructor.
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        print(f"[{self.role.upper()} RX] Connected. Subscribing to '{self.begin_topic}'")
        self.client.subscribe(self.begin_topic)

    def on_message(self, client, userdata, msg: mqtt.MQTTMessage):
        if msg.topic == self.begin_topic:
            print(f"[{self.role.upper()} RX] Received 'begin'")
            self.begin_received = True

    def send_ready_and_wait_for_begin(self):
        # Continuously publish "ready" until we detect a "begin" message.
        print(f"[{self.role.upper()} RX] Publishing 'ready'")
        while not self.begin_received:
            self.client.publish(topic=self.ready_topic, payload=self.role)
            time.sleep(1)
        # Once begin received, disconnect.
        print(f"[{self.role.upper()} RX] 'Begin' detected, disconnecting.")
        self.client.disconnect()


class MQTT_TX(MQTTBase):
    def __init__(self, conf: config.CONFIG, role: str):
        super().__init__(conf, role)
        self.ready_status = {'destination': False, 'relay': False}

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(self.BROKER, self.PORT, 60)


    def on_connect(self, client, userdata, flags, rc):
        print(f"[SOURCE TX] Connected. Subscribing to '{self.ready_topic}'")
        self.client.subscribe(self.ready_topic)

    def on_message(self, client, userdata, msg: mqtt.MQTTMessage):
        role = msg.payload.decode().strip().lower()
        
        if not self.ready_status.get(role):
            self.ready_status[role] = True
            print(f"[SOURCE TX] Received 'ready' from: {role}")

        if self.role == 'source':
            if all(self.ready_status.values()):
                self.send_begin()
                self.client.disconnect()
        else:
            print(f"[{self.role.upper()} TX] Received 'ready' from {role} but not source. Waiting for source to send 'begin'.")
            self.send_begin()
            self.client.disconnect()


    def wait_for_all_ready(self,sleep_time=1):
        self.client.loop_forever()
        print(f"[{self.role.upper()} TX] All nodes ready")
        time.sleep(sleep_time)

    def send_begin(self):
        print(f"[{self.role.upper()} TX] Sending 'begin'")
        self.client.publish(self.begin_topic, "start", qos=1)

