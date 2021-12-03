__author__ = 'Cybereason Inc.'

import json
from qpylib import qpylib
import qpylib as qpylib_parent
import sys
sys.path.append('/opt/app-root/app/')


class LogSourceHandler(object):

    def __call_rest_endpoint(self, method, endpoint):
        '''
        Calls the rest endpoint using REST method of qpylib
        Parameters: method (String), endpoint (String)
        Returns: response (object)
        '''
        header = {'Accept': 'application/json'}
        head = qpylib_parent.rest_qpylib._add_headers(
            headers=header, version='12.1')
        return qpylib.REST(
            method, endpoint, headers=head)

    def __get_log_source_type_id(self, log_source_type_name):
        '''
        Fetch existing log source type id
        Parameters: log_source_type_name (String)
        Returns: log_source_id (int)
        '''
        log_source_id = 0
        endpoint = '/api/config/event_sources/log_source_management/log_source_types'
        filter = '?filter=name%3D%22{}%22'.format(log_source_type_name)
        log_source_type_response = self.__call_rest_endpoint('GET', endpoint + filter)
        if log_source_type_response.status_code == 200 and log_source_type_response.json():
            log_source_type_details = log_source_type_response.json()
            log_source_id = log_source_type_details[0].get('id')
        else:
            qpylib.log('Error while fetching log source type id. Response status {} text: {} '.format(log_source_type_response.status_code, log_source_type_response.text))
        return log_source_id

    def get_existing_log_sources(self, type):
        '''
        Fetch existing log sources
        Parameters: type (String)
        Returns: log_sources (list)
        '''
        log_sources = []          
        log_source_id = self.__get_log_source_type_id(type)
        if log_source_id:
            endpoint = '/api/config/event_sources/log_source_management/log_sources'
            filter = '?filter=type_id%3D%22{}%22'.format(log_source_id)
            log_source_response = self.__call_rest_endpoint('GET', endpoint + filter)
            if log_source_response.status_code == 200:
                log_sources_details = log_source_response.json()
                for log_source in log_sources_details:
                    log_sources.append(log_source.get('name'))
            else:
                qpylib.log('Error while fetching log source. Response status {} text: {} '.format(log_source_response.status_code, log_source_response.text))
        return log_sources

    def get_log_source_identifier(self, name):
        '''
        Fetch log source identifier using log source name
        Parameters: log_source_name (String)
        Returns: log_source_identifier (String)
        '''
        identifier = ''
        endpoint = '/api/config/event_sources/log_source_management/log_sources'
        # URLify the parameter
        log_source_name = name.replace(' ', '%20')
        filter = '?fields=protocol_parameters&filter=name%3D%22{}%22'.format(log_source_name)
        log_source_response = self.__call_rest_endpoint('GET', endpoint + filter)
        if log_source_response.status_code == 200:
            protocol_parameters = log_source_response.json()[0]['protocol_parameters']
            for parameter in protocol_parameters:
                if parameter['name'] == 'identifier':
                    identifier = parameter['value']
        else:
            qpylib.log('Error while fetching log source identifier. Response status {} text: {} '.format(log_source_response.status_code, log_source_response.text))
        return identifier