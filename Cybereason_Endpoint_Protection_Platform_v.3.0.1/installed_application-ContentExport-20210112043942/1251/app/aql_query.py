import json
import time
import qpylib as qpylib_parent

# API endpoint for Ariel Database searches
ARIEL_SEARCHES_ENDPOINT = '/api/ariel/searches'
# Timeout to wait until giving up on polling an Ariel search
TIMEOUT_MILLISECONDS = 15000
# Response when a request with no response body is successful
SUCCESS_RESPONSE = {'success': 'true'}
# Response when a request with no response body fails
FAILURE_RESPONSE = {'success': 'false'}
# Response when a polling request times out
TIMEOUT_RESPONSE = {'error': 'Query timed out'}

class AQLQuery:
    def __init__(self, qpylib_obj):
        self.qpylib = qpylib_obj
        self.headers = qpylib_parent.rest_qpylib._add_headers(headers={'Accept': 'application/json'}, version='12.1')

    def search(self, query):
        """
            Creates a new search with the query provided, returns a search ID to allow further
            search interaction, such as retrieving results
        """
        # Parameter of ?query_expression=QUERY
        params = {'query_expression': query}
        # HTTP POST to /api/ariel/searches?query_expression=QUERY
        response = self.qpylib.REST(
            'POST',
            ARIEL_SEARCHES_ENDPOINT,
            headers=self.headers,
            params=params
        ).json()
        # Return the response
        return json.dumps(response)

    def wait_for_response(self, search_id):
        """
        Repeatedly call the Ariel API to check if a search has finished processing
        if it has, retrieve and return the results
        Poll only as long as the timeout defined
        """
        # Start time that the polling began at
        init_time = time.time()
        while init_time + TIMEOUT_MILLISECONDS > time.time():
            # While within the timeout
            # Poll with an HTTP GET request to the Ariel searches endpoint specifying
            # a search to retrieve the information of
            # /api/ariel/searches/SEARCH_ID
            response = self.qpylib.REST(
                'GET',
                '{0}/{1}'.format(ARIEL_SEARCHES_ENDPOINT, search_id),
                headers=self.headers
            ).json()
            if 'http_response' in response:
                # If there's an 'http_response' attribute in the response
                # the request has failed, output the response and error
                return json.dumps(response)
            if response['status'] == 'COMPLETED':
                # If the status of the query is COMPLETED, the results can now be retrieved
                # Make an HTTP GET request to the Ariel searches endpoint specifying
                # a search to retrieve the results of
                # /api/ariel/searches/SEARCH_ID/results
                response = self.qpylib.REST(
                    'GET',
                    '{0}/{1}/results'.format(ARIEL_SEARCHES_ENDPOINT, search_id),
                    headers=self.headers
                ).json()
                # Return the results
                return json.dumps(response)
            # Wait for 1 second before polling again to avoid spamming the API
            time.sleep(1)
        # If the polling has timed out, return an error
        return json.dumps(TIMEOUT_RESPONSE)