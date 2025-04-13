import sys
sys.path.append('/home/moh/Documents/PhD/Kim/Superposing_LDPC/')
print(sys.path)

from src import MQTT_RX, MQTT_TX

import unittest
from unittest.mock import MagicMock, patch
import json

# Let's simulate a dummy config module with the required structure

class CONFIG:
    MQTT = {
        'BROKER': '10.29.162.146',
        'PORT': 1883,
        'AIO_USERNAME': 'testuser',
        'AIO_KEY': 'testkey'
    }

# Refined unit tests focusing on expected behavior: RX sends ready, TX sends begin
class TestMQTTCoordination(unittest.TestCase):

    # to be done
