import requests
from constants import TIMEOUT_SECONDS


class RestApiCall(object):
    '''
    Wrapper class to make GET or POST api calls
    '''
    def __init__(self):
        pass

    def post(self, url, headers={}, data=None, auth=None, proxies=None, verify=False, timeout=TIMEOUT_SECONDS):
        '''
        Wrapper for POST method
        '''
        return requests.post(url, headers=headers, data=data, auth=auth, verify=verify, proxies=proxies, timeout=timeout)

    def get(self, url, headers={}, proxies=None, verify=False, timeout=TIMEOUT_SECONDS):
        '''
        Wrapper for GET method
        '''
        return requests.get(url, headers=headers, verify=verify, proxies=proxies, timeout=timeout)