__author__ = 'Cybereason Inc.'

import sys
import json
import time
from datetime import datetime
from qpylib import qpylib
sys.path.append('/opt/app-root/app/')


class ProcessSuspicion:

    def __init__(self, cr_api):
        self.malop_feature_translations = self.__get_translated_features(cr_api)

    def __get_translated_features(self, cr_api):
        # We do not have malop feature translations yet. Fetch them once (these will be fetched once per poll).
        response = cr_api.get('/rest/translate/features/all')
        return json.loads(response.text)

    def __get_translate_feature_by_df(self, cr_api, decision_feature):
        ''' 
            Get translated decision feature
            API endpoint: rest/translate/features/all
            Parameters: cr_api(object), decision_feature(str)
            Returns: result(str)
        '''
        if not self.malop_feature_translations:
            self.__get_translated_features(cr_api)
        result = ''
        feature_translation_props = self.malop_feature_translations['Process'].get(
            decision_feature)
        if feature_translation_props:
            result = feature_translation_props.get('translatedName', decision_feature)
        return result

    def process_suspicion(self, cr_api, socket_conn, suspicion, log_source_identifier):
        '''
            Process and sends a suspicion to QBox
            Parameters: cr_api (object), socket_conn(object), suspicion (object), log_source_identifier (str)
            Returns: None
        '''
        guid = suspicion['guidString']
        qpylib.log('Suspicion process: GUID: {}'.format(guid), 'DEBUG')
        event = ''
        event += '\tCybereason-eventType=Cybereason Suspicion Event'

        event += '\tCybereason-suspicionName='
        full_name = ''
        if 'elementDisplayName' in suspicion['simpleValues']:
            if suspicion['simpleValues']['elementDisplayName']['totalValues'] >= 1:
                full_name = '{0}'.format(suspicion['simpleValues']
                                      ['elementDisplayName']['values'][0])
        suspicion_detail = suspicion.get('suspicions')
        if suspicion_detail:
            suspicion_detail_list = list(suspicion_detail.keys())
            if len(suspicion_detail_list) > 0:
                decision_feature = suspicion_detail_list.pop()
                translated_name = self.__get_translate_feature_by_df(cr_api, decision_feature)
                if translated_name:
                    full_name = '{}:{}'.format(translated_name, full_name)
                else:
                    full_name = '{}:{}'.format(decision_feature, full_name)
        event += full_name

        event += '\tCybereason-suspicionCommandLine='
        if 'commandLine' in suspicion['simpleValues']:
            if suspicion['simpleValues']['commandLine']['totalValues'] >= 1:
                event += '{0}'.format(suspicion['simpleValues']
                                      ['commandLine']['values'][0])

        event += '\tCybereason-suspicionCreationTime='
        if 'creationTime' in suspicion['simpleValues']:
            if suspicion['simpleValues']['creationTime']['totalValues'] >= 1:
                event += '{0}'.format(datetime.utcfromtimestamp(int(float(
                    suspicion['simpleValues']['creationTime']['values'][0])/1000)).strftime('%Y-%m-%d,  %H:%M:%S'))

        event += '\tCybereason-suspicionSha1String='
        if 'imageFile.sha1String' in suspicion['simpleValues']:
            if suspicion['simpleValues'].get('imageFile.sha1String')['totalValues'] >= 1:
                event += '{0}'.format(
                    suspicion['simpleValues'].get('imageFile.sha1String')['values'][0])

        event += '\tCybereason-suspicionUser='
        if 'calculatedUser' in suspicion['elementValues']:
            if suspicion['elementValues']['calculatedUser']['totalValues'] >= 1:
                event += '{0}'.format(
                    suspicion['elementValues']['calculatedUser']['elementValues'][0]['name'])

        event += '\tCybereason-suspicionOwnerMachine='
        if 'ownerMachine' in suspicion['elementValues']:
            if suspicion['elementValues']['ownerMachine']['totalValues'] >= 1:
                event += '{0}'.format(
                    suspicion['elementValues']['ownerMachine']['elementValues'][0]['name'])

        event += '\tCybereason-suspicionParentProcess='
        if 'parentProcess' in suspicion['elementValues']:
            if suspicion['elementValues']['parentProcess']['totalValues'] >= 1:
                event += '{0}'.format(
                    suspicion['elementValues']['parentProcess']['elementValues'][0]['name'])

        qid = 'Suspicion'
        srcipaddress = '0.0.0.0'
        dstipaddress = '0.0.0.0'

        event_header = '{0} {1} LEEF:1.0|IBM|Cybereason|1.0|{2}|cat=Malop\tusrName=root\tsrc={3}\tdst={4}'\
            .format(time.strftime('%b %d %H:%M:%S'), log_source_identifier, qid, srcipaddress, dstipaddress)
        full_event = event_header + event + '\n'
        socket_conn.send(full_event)
