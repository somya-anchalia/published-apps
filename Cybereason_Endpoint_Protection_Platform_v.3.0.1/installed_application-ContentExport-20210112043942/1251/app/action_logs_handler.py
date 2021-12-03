__author__ = 'Cybereason Inc.'

import os
import datetime
import re
import time
from zipfile import ZipFile
from event_name_filter import event_name_filter
from qpylib import qpylib


class ActionLogProcessor:
    '''
        Process the action logs to create syslog events and ingest them to QBox
        Functions: process_action_log, 
    '''

    def process_action_log(self, action_log, log_source_identifier, socket_conn):
        '''
            Convert the json log to syslog event and send to QBox
            Parameters: self (object), action_log (object), log_source_identifier (str), socket_conn (str)
            Returns: None
        '''
        event = ''
        event += '\tCybereason-eventType=Cybereason User Action Event'
        event += '\tCybereason-ActionLogUserName='
        if action_log.get('username'):
            event += '{0}'.format(action_log.get('username'))

        event += '\tCybereason-ActionLogUserRole='
        if action_log.get('userRole'):
            event += '{0}'.format(action_log.get('userRole'))

        event += '\tCybereason-ActionLogLoginMethod='
        if action_log.get('loginMethod'):
            event += '{0}'.format(action_log.get('loginMethod'))

        event += '\tCybereason-ActionLogMachineName='
        if action_log.get('machineName'):
            event += '{0}'.format(action_log.get('machineName'))

        event += '\tCybereason-ActionLogMachineIP='
        if action_log.get('machineIP'):
            event += '{0}'.format(action_log.get('machineIP'))

        event += '\tCybereason-ActionLogType='
        if action_log.get('DeviceName'):
            event += '{0}'.format(action_log.get('DeviceName'))

        event += '\tCybereason-ActionLogUserActionTime='
        if action_log.get('userActionTime'):
            event += '{0}'.format(action_log.get('userActionTime'))

        event += '\tCybereason-ActionLogActionSuccess='
        if 'actionSuccess' in action_log:
            event += '{0}'.format(action_log.get('actionSuccess'))

        event += '\tCybereason-ActionLogQueryDetails='
        if action_log.get('queryDetail'):
            event += '{0}'.format(action_log.get('queryDetail'))

        event += '\tCybereason-ActionLogSeverity='
        if action_log.get('Severity'):
            event += '{0}'.format(action_log.get('Severity'))

        qid = 'UserAction'
        srcipaddress = "0.0.0.0"
        dstipaddress = "0.0.0.0"

        event_header = '{0} {1} LEEF:1.0|IBM|Cybereason|1.0|{2}|cat=ActionLog\tusrName=root\tsrc={3}\tdst={4}'\
            .format(time.strftime("%b %d %H:%M:%S"), log_source_identifier, qid, srcipaddress, dstipaddress)
        full_event = event_header + event + '\n'

        qpylib.log('Processed event syslog: {}'.format(
            full_event), 'DEBUG')
        socket_conn.send(full_event)


class ActionLogReader:
    '''
        Extracting and reading the action log zip file
        Functions: unzip_file, read_cef_events, _filter_action_log, _process_cef_events
    '''

    def unzip_file(self, user_action_logs_path, extracted_files_path, parent_zip, content):
        '''
            Parameters: self (object), user_action_logs_path (str), extracted_files_path (str), parent_zip (str), content (bytes)
            Returns: None
        '''
        if not os.path.exists(user_action_logs_path):
            os.makedirs(user_action_logs_path)
        with open(parent_zip, 'wb') as file:
            file.write(content)
        # Extract the downloaded script
        if not os.path.exists(extracted_files_path):
            os.makedirs(extracted_files_path)
        with ZipFile(parent_zip, 'r') as myzip:
            myzip.extractall(path=extracted_files_path)
        os.remove(parent_zip)

    def read_cef_events(self, log_source_identifier, path, is_first_poll, socket_conn, last_polled_timestamp=None, contains_last_log=False):
        '''
            Reads the CEF formatted event returned from API
            Parameters: self (object), path (str), is_first_poll (Boolean), last_polled_timestamp (timestamp), contains_last_log (Boolean)
        '''
        user_action = dict()
        with open(path, 'r') as file:
            cef_events = file.readlines()
            log_processor = ActionLogProcessor()
            for cef_event in cef_events:
                user_action = self._process_cef_events(
                    path, is_first_poll, last_polled_timestamp, cef_event)
                if user_action:
                    log_processor.process_action_log(
                        user_action, log_source_identifier, socket_conn)
        if contains_last_log and user_action:
            return user_action.get('userActionTime')

    def _filter_action_log(self, device_name):
        '''
            Parameters: device_name (string)
            Returns: is_filtered_event (Boolean)
        '''
        event_name = device_name.strip().split('/')[1]
        if event_name in event_name_filter:
            return True

    def _process_cef_events(self, path, is_first_poll, last_polled_timestamp, cef_event):
        '''
            Parameters: self (object), path (str), is_first_poll (Boolean), 
            last_polled_timestamp (timestamp)
        '''
        is_filtered_event = False
        log_parser = ActionLogParser()
        user_action = log_parser.parse(cef_event.strip())
        user_action = {k: None if not v else v for k, v in user_action.items()}
        # adding validations
        action_status = user_action['actionSuccess']
        user_action['actionSuccess'] = False
        if 'DeviceName' in user_action:
            is_filtered_event = self._filter_action_log(
                user_action['DeviceName'])
        if is_filtered_event:
            if action_status == "1":
                user_action['actionSuccess'] = True
            if user_action and is_first_poll:
                return user_action
            elif user_action:
                timestamp_str = user_action.get('userActionTime')
                res = re.sub('UTC', '', timestamp_str).strip()
                log_timestamp = datetime.datetime.strptime(
                    res, '%b %d %Y, %H:%M:%S')
                if log_timestamp > last_polled_timestamp:
                    return user_action


class ActionLogParser:
    '''
        Parsing of the CEF action logs to create a key-value dictionary of action logs
        Functions: parse()
    '''

    def parse(self, str_input):
        '''
            Parse the CEF event and return a dict with the syslog, header values and the extension
            Parameters: self (object), str_input (cef event to parse)
            Returns: values (dict) 
        '''
        values = dict()
        # This regex separates the string into the CEF header and the extension
        syslog_chunk = r'(.*)((CEF:\d+)([^=\\]+\|){,7})'
        header_re = r'((CEF:\d+)([^=\\]+\|){,7})(.*)'
        res_syslog = re.search(syslog_chunk, str_input)
        res = re.search(header_re, str_input)
        if res_syslog:
            syslog = res_syslog.group(1).split(' ')
            values["ServerName"] = syslog[3]
            values["LoggerName"] = syslog[4]
        if res:
            header = res.group(1)
            extension = res.group(4)
            # Split the header on the "|" char.
            spl = re.split(r'(?<!\\)\|', header)
            values["DeviceVendor"] = spl[1]
            values["DeviceProduct"] = spl[2]
            values["DeviceEventClassID"] = spl[4]
            values["DeviceName"] = spl[5]
            if len(spl) > 6:
                values["Severity"] = spl[6]
            cef_start = spl[0].find('CEF')
            if cef_start == -1:
                return None
            (cef, version) = spl[0][cef_start:].split(':')
            values["CEFVersion"] = version
            # The regex here finds a single key=value pair
            spl = re.findall(
                r'([^=\s]+)=((?:[\\]=|[^=]|)+)(?:\s|$)', extension)
            for i in spl:
                values[i[0]] = i[1]
            # Process custom field labels
            for key in list(values.keys()):
                if key[-5:] == "Label":
                    customlabel = key[:-5]
                    for customfield in list(values.keys()):
                        if customfield == customlabel:
                            values[values[key]] = values[customfield]
                            del values[customfield]
                            del values[key]
        else:
            qpylib.log('Could not parse record. Is it valid CEF format?')
            return None
        return values
