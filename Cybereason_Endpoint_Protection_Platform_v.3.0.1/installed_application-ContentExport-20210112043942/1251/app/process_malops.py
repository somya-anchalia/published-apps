__author__ = 'Cybereason Inc.'

import sys
import json
import time
from datetime import datetime
from qpylib import qpylib
from images import ImageConfiguration
sys.path.append("/opt/app-root/app/")


class ProcessMalops:

    def __init__(self, cr_api):
        self.malop_feature_translations = self.__get_translated_features(cr_api)
        self.malop_descriptions = self.__get_translated_descriptions(cr_api)

    def __malopdetectiontype(self, detectionType):
        return {
            'CNC_COMMUNICATION': 'Command and Control',
            'BLACKLIST': 'Blocklist',
            'CNC': 'Command and Control',
            'UNAUTHORIZED_USER': 'Compromised User',
            'CREDENTIAL_THEFT': 'Credential Theft',
            'DATA_TRANSMISSION_VOLUME': 'Data Transmission Volume',
            'ELEVATED_ACCESS': 'Elevated Access',
            'EXTENSION_MANIPULATION': 'Extension Manipulation',
            'HIJACKED_PROCESS': 'Injected Process',
            'KNOWN_MALWARE': 'Known Malware',
            'MALWARE_PROCESS': 'Known Malware',
            'MALICIOUS_PROCESS': 'Malicious process',
            'MALICIOUS_TOOL_PROCESS': 'Malicious tool',
            'PUP': 'PUP',
            'PERSISTENCE': 'Persistence',
            'PHISHING': 'Phishing',
            'UNWANTED_PROCESS': 'Potentially Unwanted Program',
            'RANSOMWARE': 'Ransomware',
            'RECONNAISSANCE': 'Reconnaissance',
            'UNAUTHORIZED_AUTH': 'Unauthorized authentication',
            'UNKNOWN': 'Unknown',
            'UNKNWOWN': 'Unknown Malware',
            'PROCESS_INJECTION': 'Process Injection',
            'LATERAL_MOVEMENT': 'Lateral Movement',
            'CUSTOM_RULE': 'Custom Rule',
        }.get(detectionType, '')

    def __malop_activity_type(self, malactype):
        return {
            'CNC_COMMUNICATION': 'Command and Control',
            'DATA_THEFT': 'Data Theft',
            'MALICIOUS_INFECTION': 'Infection',
            'LATERAL_MOVEMENT': 'Lateral Movement',
            'PRIVILEGE_ESCALATION': 'Privilege Escalation',
            'RANSOMWARE': 'Ransomware',
            'SCANNING': 'Scanning',
            'STOLEN_CREDENTIALS': 'Stolen credentials',
            'PERSISTENCE': 'Persistence',
        }.get(malactype, '')

    def __criticality(self, decisonfeature):
        return {
            'ransomwareByHashReputation': 'Critical',
            'maliciousHiddenModule': 'Critical',
            'maliciousWebShellExecution': 'Critical',
            'maliciousByCodeInjection': 'High',
            'blackListedFileHash': 'High',
            'maliciousExecutionOfPowerShell': 'High',
            'connectionToBlackListAddressByAddressRootCause': 'High',
            'maliciousShadowCopyDeletion': 'High',
            'connectionToBlackListDomainByDomainRootCause': 'High',
            'filelessMalware': 'High',
            'credentialTheftMalop': 'High',
            'abusingWindowsAccessibilityFeatures': 'High',
            'maliciousUseOfOSProcess': 'High',
            'jscriptRATMalop': 'High',
            'malwareByHashReputation': 'Medium',
            'maliciousByOpeningMaliciousFile': 'Medium',
            'connectionToMaliciousDomainByDomainRootCause': 'Medium',
            'connectionToMaliciousAddressByAddressRootCause': 'Medium',
            'maliciousByMalwareModule': 'Medium',
            'maliciousByAccessingAddressUsedByMalwares': 'Medium',
            'maliciousByDgaDetection': 'Medium',
            'maliciousExecutionOfShellProcess': 'Medium',
            'maliciousByDualExtensionByFileRootCause': 'Low',
            'unwantedByHashReputation': 'Low',
            'maliciousByUnwantedModule': 'Low',
        }.get(decisonfeature, 'Unknown')

    def __get_truncated_decision_feature(self, decision_feature):
        '''
            Decision feature is of the type "Process.rdpEnableMalop(Malop decision)". 
            We want just the "rdpEnableMalop" from this.
            Parameters: decision_feature (str)
            Returns: decision_feature (str)
        '''
        return decision_feature.replace('Process.', '').replace('(Malop decision)', '')

    def __get_translated_features(self, cr_api):
        # We do not have malop feature translations yet. Fetch them once (these will be fetched once per poll).
        response = cr_api.get('/rest/translate/features/all')
        return json.loads(response.text)

    def __get_translated_descriptions(self, cr_api):
        # We do not have malop feature translations yet. Fetch them once (these will be fetched once per poll).
        response = cr_api.get('/rest/translate/malopDescriptions/all')
        return json.loads(response.text)

    def __get_translate_descriptions_by_df(self, cr_api, decision_feature, count, name):
        ''' 
            Get translated descriptions as per the decision feature
            API endpoint: rest/translate/malopDescriptions/all
            Parameters: cr_api(object), decision_feature(str), count(int), name(str)
            Returns: result(str)
        '''
        if not self.malop_descriptions:
            self.__get_translated_descriptions(cr_api)
        # Decision feature is of the type "Process.rdpEnableMalop(Malop decision)". We want just the "rdpEnableMalop" from this.
        decision_feature_truncated = self.__get_truncated_decision_feature(
            decision_feature)
        decision_feature_description = self.malop_descriptions['Process'].get(
            decision_feature_truncated)
        result = ''
        if decision_feature_description:
            if count == 1:
                result = decision_feature_description['single'].replace(
                    '{{suspectName}}', name)
            elif count > 1:
                result = decision_feature_description['multiple'].replace(
                    '{{count}}', str(count))
        return result

    def __get_translate_feature_by_df(self, cr_api, decision_feature):
        ''' 
            Get translated decision feature
            API endpoint: rest/translate/features/all
            Parameters: cr_api(object), decision_feature(str)
            Returns: result(str)
        '''
        if not self.malop_feature_translations:
            self.__get_translated_features(cr_api)
        # Decision feature is of the type "Process.rdpEnableMalop(Malop decision)". We want just the "rdpEnableMalop" from this.
        decision_feature_truncated = self.__get_truncated_decision_feature(
            decision_feature)
        result = ''
        feature_translation_props = self.malop_feature_translations['Process'].get(
            decision_feature_truncated)
        if feature_translation_props:
            result = feature_translation_props.get('translatedName', '')
        return result

    def __get_src_dst_address_by_malop(self, cr_api, malopid):
        ''' 
            Fetches source and destination ip for a malop guid.
            API endpoint: rest/visualsearch/query/simple
            Parameters: cr_api(object),malop_id(str)
            Returns: dst_ip(str), src_ip(str)
        '''
        url = "/rest/visualsearch/query/simple"
        query = '{"queryPath":[{"requestedType":"MalopProcess","filters":[],"guidList":["' + malopid + '"],"connectionFeature":{"elementInstanceType":"MalopProcess","featureName":"suspects"}},{"requestedType":"Process","filters":[],"connectionFeature":{"elementInstanceType":"Process","featureName":"connections"}},{"requestedType":"Connection","filters":[],"isResult":true}],"totalResultLimit":5,"perGroupLimit":1200,"perFeatureLimit":1200,"templateContext":"SPECIFIC","queryTimeout":null,"customFields":["localAddress","serverAddress"]}'
        response = cr_api.post(url, query)

        dst_ip = "0.0.0.0"
        src_ip = "0.0.0.0"
        if response.status_code == 200:
            readjson = json.loads(response.text)
            if readjson["data"]:
                for malop_id1 in readjson["data"]["resultIdToElementDataMap"]:

                    id1 = readjson['data']['resultIdToElementDataMap'][malop_id1]
                    if "serverAddress" in id1["simpleValues"]:
                        if id1['simpleValues']['serverAddress']['totalValues'] >= 1:
                            dst_ip = id1['simpleValues']['serverAddress']['values'][0]

                    if "localAddress" in id1["elementValues"]:
                        if len(id1['elementValues']['localAddress']['elementValues']) >= 1:
                            src_ip = id1['elementValues']['localAddress']['elementValues'][0]['name']

        return dst_ip, src_ip

    def __get_flag_of_matching_process(self, cr_api, malop_id, hash):
        ''' 
            Fetches process data for the malop and returns the is_malicious flag value.
            API endpoint: rest/visualsearch/query/simple
            Parameters: cr_api(object),malop_id(str),hash(str)
            Returns: malicious_flag(Boolean)
        '''
        malicious_flag = False
        max_results = 1000
        url = "/rest/visualsearch/query/simple"
        json_param = {
            "templateContext": "SPECIFIC",
            "queryPath": [
                {
                    "requestedType": "MalopProcess",
                    "filters": [],
                    "guidList": [malop_id],
                    "connectionFeature": {
                        "elementInstanceType": "MalopProcess",
                        "featureName": "suspects"
                    }
                },
                {
                    "requestedType": "Process",
                    "filters": [],
                    "isResult": True
                }
            ],
            "totalResultLimit": max_results,
            "perGroupLimit": max_results,
            "perFeatureLimit": max_results,
            "queryTimeout": 120,
            "customFields": [
                "imageFile.sha1String"
            ]
        }
        query = json.dumps(json_param)
        response = cr_api.post(url, query)
        if response.status_code == 200:
            readjson = json.loads(response.text)
            process_dict = readjson['data']['resultIdToElementDataMap']
            for process_id in process_dict:
                process_data = process_dict[process_id]
                simple_values = process_data['simpleValues']
                if 'imageFile.sha1String' in simple_values:
                    if process_data['simpleValues'].get('imageFile.sha1String')['values'][0] == hash:
                        malicious_flag = process_data['isMalicious']
                        break
                    else:
                        malicious_flag = False
        return malicious_flag

    def __get_malicious_flag(self, cr_api, malop):
        ''' 
            Calculate hash for the malop and returns the is_malicious flag value of process with same hash.
            Parameters: cr_api(object), malop(dict)
            Returns: malicious_flag(Boolean)
        '''
        malicious_flag = False
        if 'rootCauseElementHashes' in malop['simpleValues']:
            hashes = malop['simpleValues']['rootCauseElementHashes'].get(
                'values')
            if hashes:
                malicious_flag = self.__get_flag_of_matching_process(
                    cr_api, malop['guidString'], hashes[0])
        return malicious_flag

    def process_edr_malop(self, cr_api, malop, malop_detailed_data, log_source_identifier):
        '''
            Process the edr malop
            Parameters: malop (object), malop_detailed_data (object), log_source_identifier (str)
            Returns: full_event (str)
        '''
        guid = malop['guid']
        event = ''
        malopdata = malop_detailed_data['data']['resultIdToElementDataMap'][guid]

        qpylib.log("Malop Poll: Malop GUID: {}".format(guid), "DEBUG")
        if 'decisionFeature' in malopdata["simpleValues"]:
            if malopdata["simpleValues"]['decisionFeature']['totalValues'] >= 1:
                decisionfeature = self.__get_translate_feature_by_df(
                    cr_api, malopdata["simpleValues"]['decisionFeature']['values'][0])
                event += '\tCybereason-decisionFeature={0}'.format(
                    decisionfeature)
            else:
                event += '\tCybereason-decisionFeature='
        else:
            event += '\tCybereason-decisionFeature='

        rootCauseElementNamecount = malopdata["simpleValues"]["rootCauseElementNames"]["totalValues"]
        rootCauseElementName = ""
        if rootCauseElementNamecount == 1:
            # Sometimes this comes in as None, make it string 'Null'
            rootCauseElementName = malopdata["simpleValues"]["rootCauseElementNames"]["values"][0] or 'Null'
        decision_feature = malopdata["simpleValues"]['decisionFeature']['values'][0]
        malop_desc = self.__get_translate_descriptions_by_df(
            cr_api, decision_feature, rootCauseElementNamecount, rootCauseElementName)
        event += '\tCybereason-MalopDesc=' + malop_desc

        event += '\tCybereason-eventType=Cybereason Malop Event'

        event += '\tCybereason-severity='
        if 'severity' in malop:
            event += '{0}'.format(malop['severity'])

        event += '\tCybereason-malopStartTime='
        if 'malopStartTime' in malopdata["simpleValues"]:
            if malopdata["simpleValues"]['malopStartTime']['totalValues'] >= 1:
                event += '{0}'.format(
                    malopdata["simpleValues"]['malopStartTime']['values'][0])

        event += '\tCybereason-detectionType='
        if 'detectionType' in malopdata["simpleValues"]:
            if malopdata["simpleValues"]['detectionType']['totalValues'] >= 1:
                detection_type = self.__malopdetectiontype(
                    malopdata["simpleValues"]['detectionType']['values'][0])
                event += '{0}'.format(detection_type)

        event += '\tCybereason-activityType='
        if 'elementDisplayName' in malopdata["simpleValues"]:
            if malopdata["simpleValues"]['elementDisplayName']['totalValues'] >= 1:
                activity_type = self.__malop_activity_type(
                    malopdata["simpleValues"]['elementDisplayName']['values'][0])
                event += '{0}'.format(activity_type)

        event += '\tCybereason-creationTime='
        if 'creationTime' in malopdata["simpleValues"]:
            if malopdata["simpleValues"]['creationTime']['totalValues'] >= 1:
                created_date = datetime.utcfromtimestamp(int(float(
                    malopdata["simpleValues"]['creationTime']['values'][0])/1000)).strftime('%Y-%m-%d,  %H:%M:%S')
                event += '{0}'.format(created_date)

        event += '\tCybereason-isBlocked='
        if 'isBlocked' in malopdata["simpleValues"]:
            if malopdata["simpleValues"]['isBlocked']['totalValues'] >= 1:
                event += '{0}'.format(
                    malopdata["simpleValues"]['isBlocked']['values'][0])

        event += '\tCybereason-rootCauseElementNames='
        if 'rootCauseElementNames' in malopdata["simpleValues"]:
            if malopdata["simpleValues"]['rootCauseElementNames']['totalValues'] >= 1:
                root_cause_elements = [
                    element for element in malopdata["simpleValues"]['rootCauseElementNames']['values']]
                event += '' + \
                    ', '.join(root_cause_elements)

        event += '\tCybereason-malopLastUpdateTime='
        if 'malopLastUpdateTime' in malopdata["simpleValues"]:
            if malopdata["simpleValues"]['malopLastUpdateTime']['totalValues'] >= 1:
                lut_date = datetime.utcfromtimestamp(int(float(
                    malopdata["simpleValues"]['malopLastUpdateTime']['values'][0])/1000)).strftime('%Y-%m-%d,  %H:%M:%S')
                event += '{0}'.format(
                    lut_date)

        event += '\tCybereason-rootCauseElementHashes='
        if 'rootCauseElementHashes' in malopdata["simpleValues"]:
            if malopdata["simpleValues"]['rootCauseElementHashes']['totalValues'] >= 1:
                event += '{0}'.format(
                    malopdata["simpleValues"]['rootCauseElementHashes']['values'][0])

        event += '\tCybereason-managementStatus='
        if 'managementStatus' in malopdata["simpleValues"]:
            if malopdata["simpleValues"]['managementStatus']['totalValues'] >= 1:
                event += '{0}'.format(
                    malopdata["simpleValues"]['managementStatus']['values'][0])

        event += '\tCybereason-customClassification='
        if 'customClassification' in malopdata["simpleValues"]:
            if malopdata["simpleValues"]['customClassification']['totalValues'] >= 1:
                event += '{0}'.format(
                    malopdata["simpleValues"]['customClassification']['values'][0])

        event += '\tCybereason-affectedUsers='
        if 'affectedUsers' in malopdata["elementValues"]:
            if malopdata["elementValues"]['affectedUsers']['totalValues'] >= 1:
                event += '{0}'.format(
                    malopdata["elementValues"]['affectedUsers']['elementValues'][0]['name'])

        event += '\tCybereason-affectedMachines='
        if 'affectedMachines' in malopdata["elementValues"]:
            if malopdata["elementValues"]['affectedMachines']['totalValues'] >= 1:
                machine_list = [
                    machine['name'] for machine in malopdata["elementValues"]['affectedMachines']['elementValues']]
                event += '' + \
                    ', '.join(machine_list)

        event += '\tCybereason-totalmachinecount='
        if 'affectedMachines' in malopdata["elementValues"]:
            event += '{0}'.format(
                malopdata["elementValues"]['affectedMachines']['totalValues'])

        event += '\tCybereason-isMalicious='
        if 'isMalicious' in malopdata:
            malicious_flag = self.__get_malicious_flag(cr_api, malopdata)
            event += '{0}'.format(malicious_flag)

        event += '\tCybereason-labelsIds='
        if 'labelsIds' in malopdata:
            event += '' + \
                ', '.join(map('{0}'.format, malopdata['labelsIds']))

        event += '\tCybereason-malopPriority='
        if 'malopPriority' in malopdata:
            malpriority = self.__criticality(malopdata["simpleValues"]['decisionFeature']['values'][0].replace(
                'Process.', '').replace('(Malop decision)', ''))
            event += '{0}'.format(malpriority)

        event += '\tCybereason-id='
        if 'guidString' in malopdata:
            event += '{0}'.format(malopdata['guidString'])

        event += '\tCybereason-malop-url='
        if 'guidString' in malopdata:
            url = 'https://' + cr_api.server + ':' + \
                cr_api.port + '/#/malop/' + malopdata['guidString']
            event += '{0}'.format(url)

        event += '\tCybereason-iconBase64='
        if 'iconBase64' in malopdata["simpleValues"]:
            evt_img = malopdata["simpleValues"]['iconBase64']['values'][0]
            imconfig = ImageConfiguration()
            imgary = imconfig.append_configuration(evt_img)
            strimg = imgary
            event += '{0}'.format(strimg)

        event += '\tCybereason-comments='
        if 'comments' in malopdata["simpleValues"]:
            if malopdata["simpleValues"]['comments']['totalValues'] >= 1:
                comment_array = [
                    comment['message'] for comment in malopdata["simpleValues"]['comments']['values']]
                full_comment = ', '.join(comment_array)
                event += '{0}'.format(full_comment)

        decisionfeaturecontain = (malopdata["simpleValues"]['decisionFeature']['values'][0].replace(
            'Process.', '').replace('(Malop decision)', ''))
        if "CustomRuleMalopDecisionFeature" in decisionfeaturecontain:
            qid = "CustomRuleMalopDecisionFeature*"
        else:
            qid = (malopdata["simpleValues"]['decisionFeature']['values'][0].replace(
                'Process.', '').replace('(Malop decision)', ''))
        affusr = ''
        if malopdata["elementValues"].get('affectedUsers'):
            affusr = malopdata["elementValues"]['affectedUsers']['elementValues'][0]['name']
        cy_malop_id = self.__get_src_dst_address_by_malop(
            cr_api, malopdata['guidString'])
        dstipaddress, srcipaddress = cy_malop_id

        event_header = '{0} {1} LEEF:1.0|IBM|Cybereason|1.0|{2}|cat=Malop\tusrName={3}\tsrc={4}\tdst={5}'\
            .format(time.strftime("%b %d %H:%M:%S"), log_source_identifier, qid, affusr, srcipaddress, dstipaddress)

        full_event = event_header + event + '\n'
        return full_event

    def process_non_edr_malop(self, cr_api, malop, malop_detailed_data, log_source_identifier):
        '''
            Process the non-edr malop
            Parameters: malop (object), malop_detailed_data (object), log_source_identifier (str)
            Returns: full_event (str)
        '''
        guid = malop['guid']
        event = ''

        qpylib.log("Malop poll: Malop GUID: {}".format(guid), "DEBUG")
        event += '\tCybereason-MalopDesc='
        if 'descriptions' in malop_detailed_data and malop_detailed_data['descriptions']:
            if len(malop_detailed_data['descriptions']) > 0:
                event += '{0}'.format(
                    malop_detailed_data['descriptions'][0])
        event += '\tCybereason-eventType=Cybereason Malop Event'
        event += '\tCybereason-severity='
        if 'severity' in malop:
            event += '{0}'.format(malop['severity'])
        event += '\tCybereason-malopStartTime='
        if 'creationTime' in malop_detailed_data:
            tstamp = datetime.utcfromtimestamp(int(
                float(malop_detailed_data['creationTime'])/1000)).strftime('%Y-%m-%d,  %H:%M:%S')
            event += '{0}'.format(tstamp)
        event += '\tCybereason-activityType='
        if 'activityType' in malop_detailed_data:
            detection_type = self.__malopdetectiontype(
                malop_detailed_data['malopDetectionType'])
            event += '{0}'.format(detection_type)
        event += '\tCybereason-creationTime='
        if 'creationTime' in malop_detailed_data:
            tstamp = datetime.utcfromtimestamp(int(
                float(malop_detailed_data['creationTime'])/1000)).strftime('%Y-%m-%d,  %H:%M:%S')
            event += '{0}'.format(tstamp)
        event += '\tCybereason-isBlocked='
        if 'isBlocked' in malop_detailed_data:
            event += '{0}'.format(
                malop_detailed_data['isBlocked'])
        event += '\tCybereason-rootCauseElementNames='
        if 'displayName' in malop_detailed_data:
            event += '{0}'.format(
                malop_detailed_data['displayName'])
        event += '\tCybereason-malopLastUpdateTime='
        if 'lastUpdateTime' in malop_detailed_data:
            last_tstamp = datetime.utcfromtimestamp(int(
                float(malop_detailed_data['lastUpdateTime'])/1000)).strftime('%Y-%m-%d,  %H:%M:%S')
            event += '{0}'.format(last_tstamp)
        event += '\tCybereason-rootCauseElementHashes='
        if 'fileHash' in malop_detailed_data:
            event += '{0}'.format(
                malop_detailed_data['fileHash'])
        event += '\tCybereason-managementStatus='
        if 'decisionStatuses' in malop_detailed_data and malop_detailed_data['decisionStatuses']:
            if len(malop_detailed_data['decisionStatuses']) > 0:
                event += '{0}'.format(
                    malop_detailed_data['decisionStatuses'][0])
        event += '\tCybereason-customClassification='
        if 'fileClassificationType' in malop_detailed_data:
            event += '{0}'.format(
                malop_detailed_data['fileClassificationType'])
        event += '\tCybereason-users='
        if 'users' in malop_detailed_data and malop_detailed_data['users']:
            if len(malop_detailed_data['users']) >= 1:
                users_list = [
                    user['displayName'] for user in malop_detailed_data['users']]
                event += '' + \
                    ', '.join(users_list)
        event += '\tCybereason-affectedMachines='
        if 'machines' in malop_detailed_data and malop_detailed_data['machines']:
            if len(malop_detailed_data['machines']) >= 1:
                machine_list = [
                    machine['displayName'] for machine in malop_detailed_data['machines']]
                event += '' + \
                    ', '.join(machine_list)
        event += '\tCybereason-totalmachinecount='
        if 'machines' in malop_detailed_data and malop_detailed_data['machines']:
            event += '{0}'.format(
                len(malop_detailed_data['machines']))
        event += '\tCybereason-isMalicious='
        if 'isMalicious' in malop_detailed_data:
            event += '{0}'.format(
                malop_detailed_data['isMalicious'])
        event += '\tCybereason-labelsIds='
        if 'labels' in malop_detailed_data:
            event += '{0}'.format(
                malop_detailed_data['labels'])
        event += '\tCybereason-malopPriority='
        if 'priority' in malop_detailed_data:
            event += '{0}'.format(
                malop_detailed_data['priority'])
        event += '\tCybereason-id='
        if 'guid' in malop_detailed_data:
            event += '{0}'.format(
                malop_detailed_data['guid'])
        event += '\tCybereason-malop-url='
        if 'guid' in malop_detailed_data:
            url = 'https://' + cr_api.server + ':' + cr_api.port + \
                '/#/detection-malop/' + malop_detailed_data['guid']
            event += '{0}'.format(url)
        event += '\tCybereason-detectionType='
        if 'malopDetectionType' in malop_detailed_data:
            detection_type = self.__malopdetectiontype(
                malop_detailed_data['malopDetectionType'])
            event += '{0}'.format(detection_type)
        event += '\tCybereason-elementType='
        if 'rootCauseElementType' in malop_detailed_data:
            event += '{0}'.format(
                malop_detailed_data['rootCauseElementType'])
        event += '\tCybereason-antiMalwareName='
        if 'detectionValues' in malop_detailed_data and malop_detailed_data['detectionValues']:
            if len(malop_detailed_data['detectionValues']) > 0:
                event += '{0}'.format(
                    malop_detailed_data['detectionValues'][0])
        event += '\tCybereason-files='
        if 'files' in malop_detailed_data and malop_detailed_data['files']:
            if len(malop_detailed_data['files']) >= 1:
                files_list = [
                    file['elementDisplayName'] for file in malop_detailed_data['files']]
                event += '' + \
                    ', '.join(files_list)

        qid = malop_detailed_data['malopDetectionType']
        srcipaddress = "0.0.0.0"
        dstipaddress = "0.0.0.0"

        event_header = '{0} {1} LEEF:1.0|IBM|Cybereason|1.0|{2}|cat=Malop\tusrName=root\tsrc={3}\tdst={4}'\
            .format(time.strftime("%b %d %H:%M:%S"), log_source_identifier, qid, srcipaddress, dstipaddress)
        full_event = event_header + event + '\n'

        return full_event
