__author__ = 'Cybereason Inc.'

import os
import re
import time
import math
import json
import sys
import traceback
import glob
import gzip
from socket_connection import SocketConnection
from update_configuration import UpdateConfiguration
from state_serializer import StateSerializer
from process_malops import ProcessMalops
from cr_api import CRAPI
from qpylib import qpylib
from datetime import datetime
from datetime import timedelta
from time import mktime
from apscheduler.schedulers.background import BlockingScheduler
from action_logs_handler import ActionLogReader
from process_suspicion import ProcessSuspicion
sys.path.append("/opt/app-root/app/")
store_path = qpylib.get_store_path()


class PollMalopInbox:

    def __init__(self):
        self.config = UpdateConfiguration()
        self.consoleip = qpylib.get_console_address()

    def __get_past_timestamp(self, malop_back_days, log_source_identifier):
        '''
            Get historic timestamp
            Parameters: malop_back_days (int)
            Returns: timestamp (int)
        '''
        qpylib.log("Log Source {}: Malop Poll: Historical poll for last {} days".format(
            log_source_identifier, malop_back_days))
        d = datetime.now() - timedelta(days=int(malop_back_days))
        return int(mktime(d.timetuple())) * 1000

    def __poll(self, cr_api, endpoint, query):
        '''
            Poll for the malop data
            Parameters: cr_api (object), endpoint (str), query (object)
            Returns: response (object)
        '''
        data = json.dumps(query)
        response = cr_api.post(endpoint, data)
        qpylib.log("Response code for malops data {}".format(
            response.status_code), "DEBUG")
        if response.status_code == 500:
            qpylib.log("Internal server error while polling data from server")
            qpylib.log("Endpoint: {}".format(endpoint))
            qpylib.log("Query: {}".format(query))
            return {}
        elif response.status_code == 200:
            return response.json()
        else:
            return {}

    def __poll_edr_malop_data(self, cr_api, malop_guids):
        '''
            Get data of malops detected by EDR engine
            Parameters: cr_api (object), malop (object)
            Returns: malop_data (object)
        '''
        endpoint = '/rest/crimes/unified'
        query = {
            "queryPath": [
                {
                    "requestedType": "MalopProcess",
                    "filters": [],
                    "guidList": malop_guids,
                    "isResult":True
                }
            ],
            "totalResultLimit": 10000,
            "perGroupLimit": 10000,
            "perFeatureLimit": 1200,
            "templateContext": "MALOP",
            "queryTimeout": None,
            "customFields": [
                "decisionFeature",
                "iconBase64",
                "isBlocked",
                "hasRansomwareSuspendedProcesses",
                "detectionType",
                "decisionFeatureSet",
                "filesToRemediate",
                "isMitigated",
                "rootCauseElementTypes",
                "rootCauseElementNames",
                "rootCauseElementCompanyProduct",
                "creationTime",
                "malopLastUpdateTime",
                "elementDisplayName"
            ]
        }
        malop_data = self.__poll(cr_api, endpoint, query)
        return malop_data

    def poll_non_edr_malop_data(self, cr_api, guid):
        '''
            Get data of malops not detected by EDR engine
            Parameters: cr_api (object), guid (str)
            Returns: malop_data (object)
        '''
        endpoint = '/rest/detection/details'
        query = {
            'malopGuid': '{}'.format(guid)
        }
        malop_data = self.__poll(cr_api, endpoint, query)
        return malop_data

    def __shutdown_scheduler(self):
        '''
            Shuts down the running scheduler
        '''
        qpylib.log(
            'Configuration was modified, scheduler will be restarted.')
        qpylib.log('Jobs before: {}'.format(
            self.scheduler.get_jobs()), 'DEBUG')
        self.scheduler.remove_all_jobs()
        self.scheduler.shutdown(wait=False)

    def __get_start_time(self, cr_api, state_serializer, log_source_identifier):
        '''
            Get start time for polling query
            Parameters: cr_api (dict), state_serializer (obj)
        '''
        start_time = None
        state = state_serializer.get_state()
        if state and 'malop_poller' in state:
            start_time = state['malop_poller']['last_poll_timestamp']
        if not start_time:
            # This is the first poll (Historical poll)
            start_time = self.__get_past_timestamp(
                cr_api.malop_back_days, log_source_identifier)
        return start_time

    def __process_edr_malop(self, cr_api, edr_malops, edr_malop_detailed_data, log_source_identifier, socket_conn):
        malop_processor = ProcessMalops(cr_api)
        for malop in edr_malops:
            full_event = malop_processor.process_edr_malop(
                cr_api, malop, edr_malop_detailed_data, log_source_identifier)
            qpylib.log("Processed event syslog: {}".format(
                full_event), "DEBUG")
            socket_conn.send(full_event)

    def __process_polled_malops(self, cr_api, malops, log_source_identifier, socket_conn):
        '''
            Process and send malop to QRadar
            Parameters: cr_api (dict), malops (dict), log_source_identifier (str)
        '''
        edr_malops = list()
        non_edr_malops = list()
        edr_malop_guids = list()
        non_edr_malop_guids = list()
        malop_processor = ProcessMalops(cr_api)
        for malop in malops:
            if malop['edr']:
                edr_malop_guids.append(malop.get('guid'))
                edr_malops.append(malop)
            else:
                non_edr_malop_guids.append(malop.get('guid'))
                non_edr_malops.append(malop)

        # Polling and processing detailed data for edr malops
        edr_malop_detailed_data = self.__poll_edr_malop_data(
            cr_api, edr_malop_guids)
        self.__process_edr_malop(
            cr_api, edr_malops, edr_malop_detailed_data, log_source_identifier, socket_conn)

        # Polling and processing detailed data for non- edr malops
        for malop in non_edr_malops:
            non_edr_malop_detailed_data = self.poll_non_edr_malop_data(
                cr_api, malop.get('guid'))
            if non_edr_malop_detailed_data:
                full_event = malop_processor.process_non_edr_malop(
                    cr_api, malop, non_edr_malop_detailed_data, log_source_identifier)
                qpylib.log("Processed event syslog: {}".format(
                    full_event), "DEBUG")
                socket_conn.send(full_event)

    def __process_action_logs(self, cr_api, log_source_identifier, socket_conn):
        '''
            Fetches user action logs from monitor/global/userAuditLog endpoint
            Parameters: self (object), cr_api(str), log_source_identifier(str), socket_conn(object)
            Returns: None
        '''
        # Defining path and class
        last_action_time = None
        is_first_poll = True
        log_reader = ActionLogReader()
        user_action_logs_path = store_path + '/action_logs_polling_states/' + \
            cr_api.server + '-' + log_source_identifier
        parent_zip = user_action_logs_path + '/action_logs.zip'
        extracted_files_path = user_action_logs_path + '/extracted_data'
        checkpoint_file = user_action_logs_path + '/last_polled_timestamp.txt'

        if os.path.exists(checkpoint_file):
            with open(checkpoint_file, 'r') as file:
                str_timestamp = file.read()
                last_polled_timestamp = datetime.strptime(
                    str_timestamp, '%Y-%m-%d %H:%M:%S')
            is_first_poll = False
        else:
            last_polled_timestamp = None

        ret = cr_api.get('/rest/monitor/global/userAuditLog')
        if ret.status_code == 200:
            # Unzip the file returned from the api
            log_reader.unzip_file(user_action_logs_path,
                                  extracted_files_path, parent_zip, ret.content)

        action_logs_path = extracted_files_path + '/userAuditSyslog.log'
        # Process the log (already unzip) file if it exist
        if os.path.exists(action_logs_path):
            last_action_time = log_reader.read_cef_events(
                log_source_identifier, action_logs_path, is_first_poll, socket_conn, last_polled_timestamp, contains_last_log=True)
            os.remove(action_logs_path)

        # Process all the zip files after extracting the main zip file
        file_count = 1
        zips_count = len(glob.glob1(extracted_files_path, '*.gz'))
        while file_count <= zips_count:
            file_to_process = action_logs_path + '.' + str(file_count)
            file_to_extract = file_to_process + '.gz'
            if os.path.exists(file_to_extract):
                f_out = open(file_to_process, 'w')
                with gzip.open(file_to_extract, 'rb') as input_file:
                    f_out.write(input_file.read().decode("utf-8"))
                f_out.close()
                log_reader.read_cef_events(
                    log_source_identifier, file_to_process, is_first_poll, socket_conn, last_polled_timestamp)
                file_count = file_count + 1
                os.remove(file_to_extract)
                os.remove(file_to_process)

        # updating last polled time
        if last_action_time:
            timestamp_str = last_action_time
            res = re.sub('UTC', '', timestamp_str).strip()
            log_timestamp = datetime.strptime(
                res, '%b %d %Y, %H:%M:%S')
        else:
            log_timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        qpylib.log('Log Source {}: Saving the last polled timestamp for Action Logs : {} '.format(
            log_source_identifier, log_timestamp))
        with open(checkpoint_file, 'w') as checkpoint:
            checkpoint.write(str(log_timestamp))

    def __create_suspicion_query(self, earliest, latest):
        return {
            "queryPath": [
                {
                    "requestedType": "Process",
                    "filters": [{"facetName": "hasSuspicions", "values": [True]}],
                    "isResult": "true"}
            ],
            "totalResultLimit": 25000, "perGroupLimit": 25000, "perFeatureLimit": 25000,
            "templateContext": "SPECIFIC",
            "startTime": "{}000".format(earliest),
            "endTime": "{}000".format(latest),
            "customFields": [
                "elementDisplayName", "creationTime", "endTime", "commandLine", "isImageFileSignedAndVerified",
                "imageFile.maliciousClassificationType", "productType", "children", "parentProcess", "ownerMachine",
                "calculatedUser", "imageFile", "imageFile.sha1String", "imageFile.md5String", "imageFile.companyName",
                "imageFile.productName", "iconBase64", "ransomwareAutoRemediationSuspended", "executionPrevented",
                "isWhiteListClassification", "matchedWhiteListRuleIds"
            ]
        }

    def __process_suspicions(self, cr_api, log_source_identifier, socket_conn):
        '''
            Fetches suspicions from the portal
            Parameters: cr_api (object), log_source_identifier(str), socket_conn(object)
            Returns: None
        '''
        earliest = 0
        suspicion_processor = ProcessSuspicion(cr_api)
        suspicions_path = store_path + '/suspicions_polling_states/' + \
            cr_api.server + '-' + log_source_identifier
        checkpoint_file = suspicions_path + '/last_polled_timestamp.txt'

        if not os.path.exists(suspicions_path):
            os.makedirs(suspicions_path)
        if os.path.exists(checkpoint_file):
            with open(checkpoint_file, 'r') as file:
                earliest = int(file.read())

        latest = int(math.ceil(time.mktime(datetime.now().timetuple())))
        if earliest < 1:
            earliest = int(math.ceil(time.mktime(
                (datetime.now() - timedelta(days=30)).timetuple())))

        endpoint = '/rest/visualsearch/query/simple'
        query = self.__create_suspicion_query(earliest, latest)
        response = cr_api.post(endpoint, json.dumps(query))
        if response.status_code == 500:
            qpylib.log("Internal server error while polling data from server")
            qpylib.log("Endpoint: {}".format(endpoint))
            qpylib.log("Query: {}".format(query))
        elif response.status_code == 200:
            suspicions = json.loads(response.content)
            for guid in suspicions["data"]["resultIdToElementDataMap"]:
                suspicion = suspicions["data"]["resultIdToElementDataMap"][guid]
                suspicion_processor.process_suspicion(
                    cr_api, socket_conn, suspicion, log_source_identifier)

        # updating last polled time
        qpylib.log('Log Source {}: Saving the last polled timestamp for Suspicions as : {} '.format(
            log_source_identifier, latest))
        with open(checkpoint_file, 'w') as checkpoint:
            checkpoint.write(str(latest))

    def poll(self, index, log_source_identifier, job_id):
        '''
            Poll for the malicious data and send them to QRadar console
            Parameters: index (int), log_source_identifier (str)
        '''

        self.config.read_configuration()
        if self.config.config['is_dirty']:
            self.__shutdown_scheduler()

        qpylib.log('Log Source {}: Malop Poll: Starting to poll from Cybereason'.format(
            log_source_identifier), 'DEBUG')

        if log_source_identifier:
            qpylib.log('Log Source {}: Job started'.format(
                log_source_identifier), 'DEBUG')
            cr_api = CRAPI(index)
            qpylib.log('Log Source {}: Using {} authentication type'.format(
                log_source_identifier, cr_api.auth_type))
            socket_conn = SocketConnection(self.consoleip, 514)
            # Define polling timestamps
            current_time = datetime.now()
            end_time = int(mktime(current_time.timetuple())) * 1000
            state_file = cr_api.server + '-' + log_source_identifier
            state_serializer = StateSerializer(state_file)
            start_time = self.__get_start_time(
                cr_api, state_serializer, log_source_identifier)

            # Polling and sending processed timebound malops
            endpoint = '/rest/detection/inbox'
            query = {'startTime': start_time, 'endTime': end_time}
            qpylib.log("Log Source {}: Query for polling malops : {}".format(
                log_source_identifier, query))
            malops_data = self.__poll(cr_api, endpoint, query)
            if malops_data:
                qpylib.log("Log Source {}: Polled {} malops".format(
                    log_source_identifier, len(malops_data.get('malops'))))
                if len(malops_data['malops']) > 0:
                    self.__process_polled_malops(
                        cr_api, malops_data['malops'], log_source_identifier, socket_conn)
                #  Save the current time as last poll timestamp
                qpylib.log("Log Source {}: Processed {} malops".format(
                    log_source_identifier, len(malops_data.get('malops'))))
                state = {'malop_poller': {'last_poll_timestamp': int(
                    mktime(current_time.timetuple())) * 1000}}
                qpylib.log('Log Source {}: Saving the malop state : {} '.format(
                    log_source_identifier, state))
                state_serializer.save_state(state)

            if cr_api.poll_action_logs:
                qpylib.log('Log Source {}: Polling for Action Logs'.format(
                    log_source_identifier))
                self.__process_action_logs(
                    cr_api, log_source_identifier, socket_conn)

            if cr_api.poll_suspicions:
                qpylib.log('Log Source {}: Polling for Suspicions'.format(
                    log_source_identifier))
                self.__process_suspicions(
                    cr_api, log_source_identifier, socket_conn)

            qpylib.log('Log Source {}: Sent {} events to QBox'.format(
                log_source_identifier, socket_conn.count))
            socket_conn.sock.close()
        else:
            qpylib.log('Log Source {}: Failed to fetch log source identifier'.format(
                log_source_identifier))

        # Removing job from the jobs_running list
        qpylib.log('Log Source {}: Job completed'.format(
            log_source_identifier), 'DEBUG')

    def main(self):
        log_source_identifier = ''
        self.config.read_configuration()
        host_info = self.config.config.get('host_info')
        if host_info:
            self.scheduler = BlockingScheduler(timezone='UTC')
            for index, host in enumerate(host_info):
                log_source_identifier = host.get('log_source_identifier')
                if log_source_identifier:
                    job_id = host.get('server') + '-' + \
                        host.get('log_source_identifier')
                    self.scheduler.add_job(self.poll, 'interval', id=job_id, seconds=int(
                        host['malop_escalation_interval'])*60, args=[index, log_source_identifier, job_id])
                    qpylib.log(
                        "Job added in scheduler for logsource identifier: {}".format(log_source_identifier))
            self.scheduler.start()
            qpylib.log("Jobs at last: {}".format(
                self.scheduler.get_jobs()), 'DEBUG')
            # Making the is_dirty flag as false as jobs are added to the queue
            qpylib.log("Setting is_dirty flag false", "DEBUG")
            self.config.config['is_dirty'] = False
            self.config.save_configuration()
        else:
            # Waiting for configuration to be saved
            qpylib.log('Waiting for configuration to be saved')
            time.sleep(30)


if __name__ == '__main__':
    try:
        qpylib.create_log()
        poll_malop_inbox = PollMalopInbox()
        poll_malop_inbox.main()
    except Exception as exc:
        qpylib.log(
            "Malop poll: Exception occured while polling Malops. Details: {}".format(exc))
        qpylib.log(traceback.format_exc())
