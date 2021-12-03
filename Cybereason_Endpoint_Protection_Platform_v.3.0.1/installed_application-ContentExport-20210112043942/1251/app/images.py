from qpylib.encdec import Encryption, EncryptionError
from models.crypto import SNCrypto
from qpylib import qpylib
import json
import os
import sys
sys.path.append("/opt/app-root/app/")


class ImageConfiguration(object):
    filename = os.path.join(qpylib.get_store_path(),
                            'image_file.json')

    def __init__(self):
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
            cybereason_key_store = Encryption(
                {'name': 'cybereason_images_secret_key', 'user': 'cybereason'})
            self._key = cybereason_key_store.decrypt()
            self._key = self._key.encode()
        except EncryptionError:
            # If cybereason key store file doesn't exist/fail to decrypt it,
            # generate a new key for it and encrypt it
            cybereason_key_store = Encryption(
                {'name': 'cybereason_images_secret_key', 'user': 'cybereason'})
            self._key = SNCrypto.gen_key()
            cybereason_key_store.encrypt(self._key.decode('utf-8'))

    def read_configuration(self):
        self.get_key()
        if not os.path.isfile(self.filename):
            # Just use default values
            self.config = {}
            return
        with open(self.filename, 'r') as data:
            self.config = json.load(data)
            data.close()

    def save_configuration(self):
        self.get_key()
        with open(self.filename, 'w') as data:
            json.dump(self.config, data)
            data.close()

    def append_configuration(self, base64String):
        exists = False
        icon_display_name = ""
        self.read_configuration()
        for ico_name in self.config:
            ico_data = self.config[ico_name]
            if ico_data['iconBase64'] == base64String:
                exists = True
                icon_display_name = ico_data['iconName']
                break
        if exists == False:
            icon_len = len(self.config)
            icon_name = 'Image000' + str(int(icon_len) + 1)
            icon_data = dict()
            icon_data[icon_name] = {
                'iconName': icon_name, 'iconBase64': base64String}
            self.config.update(icon_data)
            icon_display_name = icon_name
            self.save_configuration()
        return icon_display_name
