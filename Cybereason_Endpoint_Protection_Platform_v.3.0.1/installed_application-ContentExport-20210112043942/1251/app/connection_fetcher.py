__author__ = 'Cybereason Inc.'

from qpylib import qpylib


class MalopConnectionFetcher:

    def get_connection_for_malop(self, cr_api, malop_id):
        '''
            Fetched the connection data for the passed malop guid
            Parameters: malop_id (String), crapi (object)
            Returns: response (object)
        '''
        connection_dict = dict()
        url = "/rest/visualsearch/query/simple"
        query = '{"queryPath":[{"requestedType":"MalopProcess","filters":[],"guidList":["'+ malop_id +'"],"connectionFeature":{"elementInstanceType":"MalopProcess","featureName":"suspects"}},{"requestedType":"Process","filters":[],"connectionFeature":{"elementInstanceType":"Process","featureName":"connections"}},{"requestedType":"Connection","filters":[],"isResult":true}],"totalResultLimit":1000,"perGroupLimit":100,"perFeatureLimit":100,"templateContext":"SPECIFIC","queryTimeout":120000,"customFields":["direction","serverAddress","serverPort","portType","aggregatedReceivedBytesCount","aggregatedTransmittedBytesCount","remoteAddressCountryName","accessedByMalwareEvidence","ownerMachine","ownerProcess","dnsQuery","calculatedCreationTime","endTime","elementDisplayName"]}'
        qpylib.log('query for connection: {}'.format(query), 'DEBUG')
        res = cr_api.post(url, query)
        if res.json()["status"] == "PARTIAL_SUCCESS" or "InternalServerErrorException" in res.json()["message"]:
            qpylib.log("Internal server error while fetching connection data, so moving on...")
            return {}
        elif res.status_code == 200:
            qpylib.log("Received Connections for Malop with id: {}".format(malop_id))
            res_json = self._parse_cr_response(res)
            connection_dict = self._flatten_connection_dict(res_json, malop_id)
            return connection_dict
        else :
            return {}

    def _flatten_connection_dict(self, connection_dict, malop_id):
        '''
            The JSON response for malops from Cybereason is complex, and we often need simple values from it.
            We will save a simplified (flattened) version of the machines JSON. We will also save the original raw data
            in case it is needed. The rule is to NEVER remove or modify anything from the simplified version. If you need
            to modify any member (e.g. convert from a single value to an array), add a version to the object and store it
            there. This is critical to ensure that any changes here do not break existing integrations
        '''
        flattened_connection_dict = {}
        for connection_id, original_connection in connection_dict.items():
            flattened_connection_dict[connection_id] = {
                'raw': original_connection
            }
            flattened_connection = self._get_element_value(original_connection)
            for simple_value_key, simple_value in original_connection['simpleValues'].items():
                if simple_value['totalValues'] == 1:
                    flattened_connection[simple_value_key] = simple_value['values'][0]
            flattened_connection_dict[connection_id]['v1'] = flattened_connection
        return flattened_connection_dict

    def _parse_cr_response(self, response):
        '''
            Parses a Cybereason API response. Tries to find a valid JSON response, and if found, 
            returns results at ["data"]["resultIdToElementDataMap"]
            WILL THROW an exception if the response is not JSON
        '''
        result = None
        try:
            result = response.json()['data']['resultIdToElementDataMap']
        except Exception:
            raise ValueError("Exception when parsing JSON response. Actual response is: " + response.text)
        return result

    def _parse_cached_response(self, response):
        '''
            Parses a Cybereason API response. Tries to find a valid JSON response,
            and if found, returns results at ["data"]["resultIdToElementDataMap"]
            WILL THROW an exception if the response is not JSON
        '''
        result = None
        try:
            result = response['data']['resultIdToElementDataMap']
        except Exception:
            raise ValueError(
                "Exception when parsing JSON response. Actual response is: " + response.text)
        return result

    def _get_element_value(self, original_connection):
        processed_element_values = {}
        for element_value_key, element_value in original_connection['elementValues'].items():
            if element_value['totalValues'] == 1 and element_value['elementValues'] is not None:
                processed_element_values[element_value_key] = element_value['elementValues'][0]['name']
        return processed_element_values
