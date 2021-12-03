#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import json
import os
import time
import threading
import math
import base64
from datetime import datetime
from qpylib import qpylib
import sys
sys.path.append("/opt/app-root/app/")
from update_configuration import UpdateConfiguration
from requests.utils import quote
from constants import TIMEOUT_SECONDS
from rest_api_call import RestApiCall
from constants import TIMEOUT_SECONDS

class CRAPI(object):
    def __init__(self, index):
        #Read cy_config.json
        self.jwt_auth_token = None
        self.jwt_expiry_minutes = 0
        config_filepath = os.path.join(qpylib.get_store_path(), "cy_config.json")
        with open(config_filepath) as json_data:
            config_data = json.load(json_data)
        if config_data["host_info"]:
            self.username = str(config_data["host_info"][index]["username"])
            crconfig = UpdateConfiguration()
            self.password = crconfig.decrypt_key_value(config_data["host_info"][index]["password"])
            self.server = str(config_data["host_info"][index]["server"])
            self.port = str(config_data["host_info"][index]["port"])
            self.malop_back_days = str(config_data["host_info"][index]["malop_back_days"])
            self.malop_escalation_interval = str(config_data["host_info"][index]["malop_escalation_interval"])
            self.poll_suspicions = config_data["host_info"][index]["poll_suspicions"]
            self.poll_action_logs = config_data["host_info"][index]["poll_action_logs"]
            self.auth_type = config_data["host_info"][index]["auth_type"]
            self.headers = {
                "Content-Type": "application/json",
                "User-Agent": "CybereasonQRadarIntegration/3.0.1 (target={})".format(qpylib.get_console_address())
            }
            self.base_url = "https://" + self.server + ":" + self.port
        else:
            qpylib.log('No host found in the configuration, please configure a host from Admin page.')

        #Get Proxy Details
        self.proxy = ''
        isProxy = config_data["proxy_https"]["chkProxy"]
        proxyIP = config_data["proxy_https"]["proxy_ip"]
        proxyPort = config_data["proxy_https"]["proxy_port"]
        isProxyAuth = config_data["proxy_https"]["chkProxyAuth"]
        tmpProxyAuth = ''
        if(isProxyAuth == True):
            proxyUser = config_data["proxy_https"]["proxy_user"]
            proxy_password = crconfig.decrypt_key_value(config_data["proxy_https"]["proxy_user"])
            tmpProxyAuth = proxyUser+':'+ quote(proxy_password, safe='') +'@'
        if(isProxy == True):
            self.proxy = {
                'http': 'http://'+tmpProxyAuth+proxyIP+':'+proxyPort,
                'https': 'https://'+tmpProxyAuth+proxyIP+':'+proxyPort
    	    }
        else:
            self.proxy = ''
        if self.auth_type == 'jwt':
            self.rest_api_call = RestApiCall()
        else:
            self.rest_api_call = self.__create_session()

    def __create_session(self):
        login_url = '{}/login.html'.format(self.base_url)
        post_body = {
            'username': self.username,
            'password': self.password
        }
        session = requests.Session()
        session.post(login_url, data=post_body, proxies=self.proxy, verify=False, timeout=TIMEOUT_SECONDS)
        return session

    def __check_jwt_expiry(self, jwt_creation_timestamp):
        expired_flag = False
        latest = int(math.ceil(time.mktime(datetime.now().timetuple())))
        duration = latest - jwt_creation_timestamp
        if duration > (self.jwt_expiry_minutes*60):
            expired_flag = True
        return expired_flag

    def __set_jwt_expiry_mins(self):
        res = self.jwt_auth_token.split('.')
        data = res[1] + '===='
        decoded_token = base64.b64decode(data)
        decoded_token = json.loads(decoded_token)
        created_timestamp = decoded_token.get('iat',0)
        expiry_timestamp = decoded_token.get('exp',0)
        # Calulating expiry minutes with a buffer
        expiry_mins = int((expiry_timestamp-created_timestamp)/60 - 5)
        self.jwt_expiry_minutes = expiry_mins
        qpylib.log('JWT token will be renewed after {} minutes'.format(self.jwt_expiry_minutes))

    def __fetch_jwt(self):
        qpylib.log('Generating new JWT token')
        url = self.base_url + '/rest/auth/token'
        res = self.rest_api_call.post(url=url, auth=(self.username, self.password))
        self.jwt_auth_token = res.content.decode("utf-8")
        if self.jwt_auth_token:
            self.__set_jwt_expiry_mins()
        else:
            qpylib.log('JWT token not received')

    def __new_jwt_token(self, jwt_state_file, jwt_file, jwt_expiry):
        self.__fetch_jwt()
        if self.jwt_auth_token:
            latest = int(math.ceil(time.mktime(datetime.now().timetuple())))
            with open(jwt_state_file, 'w') as checkpoint:
                checkpoint.write(str(latest))
            with open(jwt_file, 'w') as checkpoint:
                checkpoint.write(self.jwt_auth_token)
            with open(jwt_expiry, 'w') as checkpoint:
                checkpoint.write(str(self.jwt_expiry_minutes))

    def __add_jwt_to_header(self):
        '''
            Add the JWT token to the headers dict
        '''
        jwt_state_dir = qpylib.get_store_path() + '/jwt_token_state/{}-{}'.format(self.server, self.username)
        jwt_file = jwt_state_dir + '/jwt_token.txt'
        jwt_state_file = jwt_state_dir + '/jwt_creation_timestamp.txt'
        jwt_expiry = jwt_state_dir + '/jwt_expiry_minutes.txt'
        if not os.path.exists(jwt_state_dir):
            os.makedirs(jwt_state_dir)
        if os.path.exists(jwt_state_file):
            with open(jwt_state_file, 'r') as file:
                jwt_creation_timestamp = int(file.read())
            with open(jwt_expiry, 'r') as file:
                self.jwt_expiry_minutes = int(file.read())
            expired = self.__check_jwt_expiry(jwt_creation_timestamp)
            if expired:
                qpylib.log('JWT token has expired, generating new one')
                self.__new_jwt_token(jwt_state_file, jwt_file, jwt_expiry)
            else:
                qpylib.log('Using saved JWT token', 'DEBUG')
                with open(jwt_file, 'r') as file:
                    self.jwt_auth_token = file.read()
        else:
            self.__new_jwt_token(jwt_state_file, jwt_file, jwt_expiry)
        if self.jwt_auth_token:
            self.headers["Authorization"] = 'Bearer ' + self.jwt_auth_token

    def post(self, url, req_data):
        full_url = self.base_url + url
        is_verify = False
        if self.auth_type == 'jwt':
            self.__add_jwt_to_header()
        qpylib.log("POST request with url=%s data=%s, headers=%s, verify=%s, proxies=%s" % (full_url, req_data, self.headers, is_verify, self.proxy),'DEBUG')
        response = self.rest_api_call.post(full_url, data=req_data, headers=self.headers, proxies=self.proxy, verify=is_verify, timeout=TIMEOUT_SECONDS)
        qpylib.log("POST response status=%s" % response.status_code,'DEBUG')
        if response.status_code != 200:
            qpylib.log('Error making an api call. Endpoint: {}, Method: POST, Status code: {}, Response text: {}'.format(url, response.status_code, response.text))
        return response

    def get(self, url):
        full_url = self.base_url + url
        if self.auth_type == 'jwt':
            self.__add_jwt_to_header()
        qpylib.log("GET request with url=%s, headers=%s, proxies=%s" % (full_url, self.headers, self.proxy),'DEBUG')
        response = self.rest_api_call.get(full_url, headers=self.headers, proxies=self.proxy, timeout=TIMEOUT_SECONDS)
        qpylib.log("GET response status=%s" % response.status_code,'DEBUG')
        if response.status_code != 200:
            qpylib.log('Error making an api call. Endpoint: {}, Method: GET, Status code: {}, Response text: {}'.format(url, response.status_code, response.text))
        return response

    def get_malop_status(self, malop_id):
        query='{"templateContext": "MALOP", "queryPath": [{"requestedType": "MalopProcess", "guidList":["' + malop_id + '"], "filters": [], "result": true}], "totalResultLimit": 500, "perGroupLimit": 500, "perFeatureLimit": 500}'
        url = "/rest/crimes/unified"
        malop = self.post(url, query)
        if malop.status_code == 200:
            readjson = json.loads(malop.text)
            if malop_id in readjson['data']['resultIdToElementDataMap']:
                return readjson['data']['resultIdToElementDataMap'][malop_id]['simpleValues']['managementStatus']['values'][0]
        return ""
