from models.crypto import SNCrypto
__author__ = 'Cybereason Inc.'

import json
import os
import copy
import base64
import threading
from qpylib import qpylib
import sys
from qpylib.encdec import Encryption, EncryptionError
sys.path.append('/opt/app-root/app/')


class UpdateConfiguration(object):
    filename = os.path.join(qpylib.get_store_path(),
                            'cy_config.json')
    _fileop_lock = threading.Lock()

    def __init__(self):
        ''' Initial Config '''
        self.config = {
            'host_info': [
            ],
            'proxy_https': {
                'idProxy': 'https',
                'chkProxy': False,
                'idAuth': 'authhttps',
                'chkProxyAuth': False,
                'proxy_ip': '',
                'proxy_pass': '',
                'proxy_port': '',
                'proxy_user': ''
            },
            'is_dirty': False
        }
        self._key = None

    def get_key(self):
        '''
            generates a key file and store it in `_key` for encryption/decryption purpose
        '''
        # If encryption key already exists then return
        if self._key is not None:
            return

        # no key exist in local instance
        try:
            # Read in cybereason key store for stored key for config files
            cybereason_key_store = Encryption( { 'name': 'cybereason_config_secret_key', 'user': 'cybereason'})
            self._key = cybereason_key_store.decrypt()
            self._key = self._key.encode()
        except EncryptionError:
            # If cybereason key store file doesn't exist/fail to decrypt it,
            # generate a new key for it and encrypt it
            cybereason_key_store = Encryption( { 'name': 'cybereason_config_secret_key', 'user': 'cybereason'})
            self._key = SNCrypto.gen_key()
            cybereason_key_store.encrypt(self._key.decode('utf-8'))

    def read_configuration(self):
        with UpdateConfiguration._fileop_lock:
            self.get_key()
            if not os.path.isfile(self.filename):
                # Just use default values
                return
            with open(self.filename, 'r') as data:
                self.config = json.load(data)
                data.close()

    def save_configuration(self):
        with UpdateConfiguration._fileop_lock:
            self.get_key()
            with open(self.filename, 'w+') as data:
                json.dump(self.config, data, indent=4)
                data.close()

    def decrypt_key_value(self, encrypted_value):
        self.get_key()
        decrypted_value = SNCrypto.decrypt(encrypted_value, self._key).strip()
        return decrypted_value

    def secure_json_object(self, json_object):
        '''
        Secures the json submitted by the user
        '''
        self.get_key()
        for key, value in json_object.items():
            if key in ('password', 'proxy_pass'):
                # ENCRYPT value and save in the object
                if(len(value.strip())):
                    encrypted_object = SNCrypto.encrypt(value, self._key).strip()
                    json_object[key] = encrypted_object
            elif isinstance(value, list):
                for item in value:
                    self.secure_json_object(item)
            elif isinstance(value, dict):
                self.secure_json_object(value)
            else:
                json_object[key] = value
        return json_object
