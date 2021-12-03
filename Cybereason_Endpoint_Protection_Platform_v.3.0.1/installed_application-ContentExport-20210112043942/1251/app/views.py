import os
import sys
import json, ast
import requests
from app import app
import random
import json
import re
from flask import jsonify, request, render_template
from qpylib import qpylib
import time
import base64
import traceback
from urllib.parse import urlparse
from app.cr_api import CRAPI
from .update_configuration import UpdateConfiguration
from datetime import datetime, timedelta, date
import csv
from .images import ImageConfiguration
from requests.utils import quote
from .constants import TIMEOUT_SECONDS
from .log_source_handler import LogSourceHandler
from poll_malop_inbox import PollMalopInbox
from connection_fetcher import MalopConnectionFetcher
from aql_query import AQLQuery
from qpylib.encdec import Encryption, EncryptionError
import secrets

qpylib.set_log_level('INFO')
if getattr(sys, 'frozen', False):
    rootFolder = os.path.dirname(os.path.abspath(sys.executable))
else:
    rootFolder = os.path.dirname(os.path.abspath(__file__))

app.config['CONFIG_FOLDER'] = os.path.abspath(qpylib.get_store_path())
app.config.update(SESSION_COOKIE_NAME='Cybereason-Session')

# Set a secret key used by cryptographic components in the QRadar framework
# for signing things like cookies
secret_key = None
try:
    # Read in secret key
    secret_key_store = Encryption({'name': 'secret_key', 'user': 'cybereason'})
    secret_key = secret_key_store.decrypt()
    qpylib.log('App started using a saved secret key.')
except EncryptionError:
    # If secret key file doesn't exist/fail to decrypt it,
    # generate a new random password for it and encrypt it
    qpylib.log('Secret key not found, creating one...')
    secret_key_store = Encryption({'name': 'secret_key', 'user': 'cybereason'})
    secret_key = secrets.token_urlsafe(64)
    secret_key_store.encrypt(secret_key)
app.secret_key = secret_key

# # for dev mode
# from flask_cors import CORS
# CORS(app)

def _check_server_in_config(server):
    '''
    Check if server exists in the config
    Parameters: server (str)
    Returns: flag (bool), index (int), log_source (str)
    '''
    flag = False
    index = None
    config = UpdateConfiguration()
    config.read_configuration()
    hosts = config.config['host_info']
    if hosts:
        # If hosts exist in the config
        for i, host in enumerate(hosts):
            # Looking for server in the host object
            if server == host['server']:
                log_source = host['log_source']
                flag = True
                index = i
                break
    return flag, index, log_source

def _save_tenant(config, form):
    config.config = form
    config.config['is_dirty'] = True
    qpylib.log("The config is not yet saved, cannot start polling", "DEBUG")
    config.save_configuration()

def _validate_tenant(added_tenant, form, config):
    '''
    Validates the tenant details by calling the login API
    Parameters: added_tenant (dict), form (dict)
    Returns: response_url (str)
    '''
    # Declaring vars
    is_proxy = False
    is_proxy_auth = False
    proxy_ip = ''
    proxy_port = ''
    tmp_proxy_auth = ''
    proxy = ''
    response_url = ''

    # Get API details
    url = added_tenant["server"]
    username = added_tenant["username"]
    password = added_tenant["password"]
    port = added_tenant["port"]
    data = {
        "username": username,
        "password": password
    }
    base_url = "https://" + url + ":{}".format(port)
    login_url = base_url + "/login.html"

    # Get proxy details
    proxy = ''
    if 'chkProxy' in form['proxy_https']:
        is_proxy = form['proxy_https']["chkProxy"]
        proxy_ip = form['proxy_https']["proxy_ip"]
        proxy_port = form['proxy_https']["proxy_port"]
    if 'chkProxyAuth' in form['proxy_https']:
        is_proxy_auth = form['proxy_https']["chkProxyAuth"]

    if is_proxy_auth:
        proxyUser = form['proxy_https']["proxy_user"]
        proxy_password = config.decrypt_key_value(form['proxy_https']["proxy_pass"])
        tmp_proxy_auth = proxyUser+':'+ quote(proxy_password, safe='') +'@'
    if is_proxy:
        proxy = {
            'http': 'http://'+tmp_proxy_auth+proxy_ip+':'+proxy_port,
            'https': 'https://'+tmp_proxy_auth+proxy_ip+':'+proxy_port
        }

    session = requests.session()
    response = session.post(login_url, data=data, verify=False, proxies=proxy, timeout=TIMEOUT_SECONDS)
    if response.status_code == 200:
        response_url = response.url
    return response_url

def _fetch_existing_machines(malop_id, log_source):
    qpylib.log('fetching machines using AQL', 'DEBUG')
    machines_list = []
    # AQL query object to make api calls to QBox
    aql_query_obj = AQLQuery(qpylib)

    # Fetch machine for a malop guid
    machine_aql_query = "SELECT \"Malop ID\" AS malop_id, \"Malop Machines\" as machines, DATEFORMAT(PARSETIMESTAMP('yyyy-MM-dd, H:m:s',\"Malop Last Update Time\"),'yyyy-MM-dd, H:m:s') AS last_update_time FROM events WHERE LOGSOURCENAME(logsourceid) = '"+log_source+"' and malop_id = '"+malop_id+"' ORDER BY PARSETIMESTAMP('yyyy-MM-dd, H:m:s', last_update_time) DESC LAST 100 DAYS"
    search_res = aql_query_obj.search(machine_aql_query)
    search_res_json = json.loads(search_res)
    search_id = search_res_json['search_id']
    query_response = aql_query_obj.wait_for_response(search_id)
    if query_response:
        query_res_json = json.loads(query_response)
        if len(query_res_json['events']) > 0:
            machines_list = query_res_json['events'][0]['machines'].split(',')
            machines_list = [machine.strip() for machine in machines_list]
    return machines_list

def _flag_new_data(existing_data, live_data):
    qpylib.log('Flagging the new data', 'DEBUG')
    for i, data in enumerate(live_data):
        if data['machine_name'] not in existing_data:
            live_data[i]['is_new'] = True
    return live_data

@app.route('/')
def default_route():
    '''
    Default route for the app
    '''
    return "Cybereason QRadar app default route"

@app.route('/set_log_level/<level>')
def set_log_level(level):
    '''
    App endpoint to set the log level
        parameters: 
            level (str) : log level to be set
    '''
    upper_case = level.upper()
    if upper_case in ['INFO', 'DEBUG', 'ERROR', 'WARNING', 'CRITICAL']:
        qpylib.set_log_level(upper_case)
        return "Log level set to {0}".format(upper_case)
    else:
        return "Invalid level"

@app.route('/get_config', methods=['GET'])
def get_config():
    qpylib.log("Fetching the config")
    config = UpdateConfiguration()
    config.read_configuration()
    return jsonify({
        'status': 'success',
        'configSettings': config.config
    })

@app.route('/save_configs', methods=['POST'])
def save_configs():
    qpylib.log("Saving the config from admin page")
    config = UpdateConfiguration()
    config.read_configuration()
    messages = []
    status = 'success'
    try:
        form = request.json
        if len(form['host_info']) < len(config.config['host_info']):
            qpylib.log('Tenant was removed, configuration have been saved')
            messages.append('Tenant was removed, configuration have been saved')
        else:
            existing_proxy_pass = config.config.get('proxy_https').get('proxy_pass')
            form_proxy_pass = form.get('proxy_https').get('proxy_pass')
            if existing_proxy_pass:
                if existing_proxy_pass != form_proxy_pass:
                    qpylib.log('Proxy password was changed, encrypting the new password', 'DEBUG')
                    form['proxy_https'] = config.secure_json_object(form['proxy_https'])
                else:
                    qpylib.log('Proxy password was not changed, not encrypting the password', 'DEBUG')
            else:
                qpylib.log('Proxy password is provided for the first time, encrypting the new password', 'DEBUG')
                form['proxy_https'] = config.secure_json_object(form['proxy_https'])
            qpylib.log('Configuration have been saved')
            messages.append('Configuration have been saved')
        _save_tenant(config, form)
        return jsonify({
            'status': status,
            'messages' : messages
        })
    except:
        qpylib.log(traceback.format_exc(), 'DEBUG')
        messages.append('Failed to establish connection to the server, please check the network settings')
        return jsonify({
            'status': 'error',
            'messages' : messages
        })

@app.route('/add_tenant', methods=['POST'])
def add_tenant():
    qpylib.log("Saving the config from admin page")
    config = UpdateConfiguration()
    config.read_configuration()
    messages = []
    status = 'error'
    try:
        form = request.json
        if len(form['host_info']) > len(config.config['host_info']):
            # A tenant was added
            added_tenant = form['host_info'].pop()
            log_source_handler = LogSourceHandler()
            added_tenant['log_source_identifier'] = log_source_handler.get_log_source_identifier(added_tenant['log_source'])
            response_url = _validate_tenant(added_tenant, form, config)
            if 'current' in response_url:
                encrypted_tenant = config.secure_json_object(added_tenant)
                form['host_info'].append(encrypted_tenant)
                _save_tenant(config, form)
                qpylib.log('Configuration have been saved')
                messages.append('Configuration have been saved')
                status = 'success'
            else:
                qpylib.log('Given Cybereason API details are incorrect')
                messages.append('Given Cybereason API details are incorrect')
                status = 'error'
        return jsonify({
            'status': status,
            'messages' : messages
        })
    except:
        qpylib.log(traceback.format_exc(), 'DEBUG')
        messages.append('Failed to establish connection to the server, please check the network settings')
        return jsonify({
            'status': 'error',
            'messages' : messages
        })

@app.route('/get_log_source', methods=['GET'])
def get_log_source():
    qpylib.log("Fetching the log sources from QRadar")
    try:
        log_sources = list()
        log_source_handler = LogSourceHandler()
        log_sources = log_source_handler.get_existing_log_sources('Cybereason')
        config = UpdateConfiguration()
        config.read_configuration()
        existing_hosts = config.config['host_info']
        if existing_hosts:
            for host in existing_hosts:
                log_source = host.get('log_source')
                if log_source in log_sources:
                    log_sources.remove(log_source)
        return jsonify({
            'status': 'success',
            'log_sources': log_sources
        })
    except Exception as e:
        qpylib.log("Error while fetching log sources" + str(e))
        return jsonify({
            'status': 'error',
            'log_sources': log_sources
        })

@app.route('/admin_screen')
def admin_screen():
    '''
    Configuration page
    '''
    app_id = qpylib.get_app_id()
    app_url = qpylib.get_app_base_url()
    qradar_app_url_path=urlparse(app_url).path
    return render_template('index.html',
                           app_id=app_id,
                           qradar_app_url=app_url,
                           qradar_app_url_path=qradar_app_url_path)

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    try:
        log_sources = []
        log_source_handler = LogSourceHandler()
        log_sources = log_source_handler.get_existing_log_sources('Cybereason')

        formdata={
            "chartContainerMalops": "", 
            "malop_events":"",
            "donutchartData":"",
            "pieChartData":"",
            "datepicker": "",
            "enddate": "",
            "log_sources":log_sources
        }

        chartContainerMalops = {
            'Command and Control': 0,
            'Data Theft':0,
            'Infection':0,
            'Lateral Movement':0,
            'Privilege Escalation':0,
            'Ransomware':0,
            'Scanning':0,
            'Stolen credentials':0,
            'Persistence':0
        }

        
        N = 10
        startdate = str(date.today() - timedelta(days=N))
        tmp_st = datetime.strptime(startdate,'%Y-%m-%d')
        tmp_st_str = tmp_st.strftime("%m/%d/%Y")
        formdata["datepicker"] = tmp_st_str
        end_date = str(date.today())
        tmp_ed = datetime.strptime(end_date, '%Y-%m-%d')
        tmp_ed_str = tmp_ed.strftime("%m/%d/%Y")
        formdata["enddate"] = tmp_ed_str
        dateRangeFilter = "LAST " + str(N) + " DAYS"
        log_source_filter = ''
        
        if request.method == 'POST':
            startdate = str(request.form.get("datepicker"))
            log_source_filter = str(request.form.get("log_source_selector"))
            if log_source_filter == 'default':
                log_source_filter = ''
            qpylib.log('log source selected : {}'.format(log_source_filter), 'DEBUG')
            tmp_st = datetime.strptime(startdate, '%m/%d/%Y')
            tmp_st_str = tmp_st.strftime("%Y-%m-%d")+" 00:00"
            enddate = str(request.form.get("enddate"))
            tmp_ed = datetime.strptime(enddate, '%m/%d/%Y')
            tmp_ed_str = tmp_ed.strftime("%Y-%m-%d")+ " 23:59"
            formdata["datepicker"] = request.form.get("datepicker")
            formdata["enddate"] = request.form.get("enddate")
            dateRangeFilter = "START '" + tmp_st_str + "' STOP '" + tmp_ed_str + "'"

        # AQL query object to make api calls to QBox
        aql_query_obj = AQLQuery(qpylib)

        # Malop by Activity Data
        chart_aql_query = "SELECT LONG(COUNT(*)) as eventcount, \"Malop Activity Type\" as activity_type FROM events WHERE LOGSOURCETYPENAME(deviceType) = 'Cybereason' and LOGSOURCENAME(logsourceid) LIKE '%" + log_source_filter + "%' and activity_type <> null GROUP BY activity_type " + dateRangeFilter
        search_res = aql_query_obj.search(chart_aql_query)
        search_res_json = json.loads(search_res)
        search_id = search_res_json['search_id']
        query_response = aql_query_obj.wait_for_response(search_id)
        if query_response:
            query_res_json = json.loads(query_response)
            for data in query_res_json['events']:
                chartContainerMalops[data['activity_type']] = data['eventcount']
            formdata['chartContainerMalops'] = chartContainerMalops
            if formdata['chartContainerMalops']:
                qpylib.log("Dashboard : Malop by Activity data loaded.")

        # Malop Inbox Data
        malop_aql_query = "SELECT \"Malop ID\" AS malop_id, \"Malop URL\" AS malop_url, \"Malop Severity\" as malop_severity, LOGSOURCENAME(logsourceid) AS log_source, CASE WHEN STRPOS(UtF8(payLoad),'Cybereason-iconBase64=') > 0 THEN REPLACEALL('\\n',SUBSTRING(UtF8(payLoad),STRPOS(UtF8(payLoad),'Cybereason-iconBase64=') + 22, STRLEN(UtF8(payLoad))),'') ELSE '' END as malop_icon ,\"Malop Detection Type\" as detection_type , \"Malop Activity Type\" AS malop_activity_type, QIDNAME(qid) AS event_name, DATEFORMAT(PARSETIMESTAMP('yyyy-MM-dd, H:m:s',\"Malop Last Update Time\"),'yyyy-MM-dd, H:m:s') AS last_update_time,\"Malop Creation Time\" as created_time,\"Malop Root Cause Name\" as root_cause_element_names,MAX(\"Malop Affected Machine Count\") AS machine_count FROM events WHERE LOGSOURCETYPENAME(deviceType) = 'Cybereason' AND log_source LIKE '%" + str(log_source_filter) + "%' AND QIDNAME(qid)!= 'unknown' AND malop_id <> null AND malop_url <> null GROUP BY malop_id ORDER BY PARSETIMESTAMP('yyyy-MM-dd, H:m:s', last_update_time) DESC " + dateRangeFilter
        search_res = aql_query_obj.search(malop_aql_query)
        search_res_json = json.loads(search_res)
        search_id = search_res_json['search_id']
        query_response = aql_query_obj.wait_for_response(search_id)
        if query_response:
            query_res_json = json.loads(query_response)
            malop_inbox_data = []
            for malop_data in query_res_json['events']:
                malop_data['root_cause_element_names'] = str(malop_data['root_cause_element_names']).split(',')[0]
                icon_name = malop_data['malop_icon']
                if icon_name != "" and str(icon_name).startswith('Image'):
                    icon_name = re.split(r'\t+',str(icon_name))[0]
                    imconfig = ImageConfiguration()
                    imconfig.read_configuration()
                    iconBase64 = ""
                    if icon_name in imconfig.config:
                        iconBase64 = imconfig.config[icon_name]['iconBase64']
                    malop_data['malop_iconbase64'] = iconBase64
                else:
                    malop_data['malop_iconbase64'] = ""
                malop_inbox_data.append(malop_data)
            formdata['malop_events'] = malop_inbox_data
            if formdata['malop_events']:
                qpylib.log("Dashboard : Malop Inbox data loaded.")

        # Malop by Types Data
        type_chart_aql_query = "SELECT COUNT(*) AS malop_count, CASE WHEN \"Malop Detection Type\" = NULL THEN '' ELSE \"Malop Detection Type\" END as detection_type  FROM events WHERE LOGSOURCETYPENAME(deviceType) = 'Cybereason' AND LOGSOURCENAME(logsourceid) LIKE '%" + log_source_filter + "%' AND QIDNAME(qid) != 'unknown' and detection_type <> ''  GROUP BY detection_type " + dateRangeFilter
        search_res = aql_query_obj.search(type_chart_aql_query)
        search_res_json = json.loads(search_res)
        search_id = search_res_json['search_id']
        query_response = aql_query_obj.wait_for_response(search_id)
        if query_response:
            query_res_json = json.loads(query_response)
            formdata['donutchartData'] = query_res_json['events']
            if formdata['donutchartData']:
                qpylib.log("Dashboard : Malop by Types data loaded.")

        # Top Suspicions Data
        suspicion_chart_aql_query = "SELECT \"Susp Process Name\" as suspicion_name, LONG(COUNT(*)) AS suspicion_count FROM events WHERE LOGSOURCETYPENAME(deviceType) = 'Cybereason' and LOGSOURCENAME(logsourceid) LIKE '%" + log_source_filter + "%' and QIDNAME(qid) = 'Suspicious Process' and suspicion_name <> null GROUP BY suspicion_name ORDER BY suspicion_count DESC LIMIT 10 " + dateRangeFilter
        search_res = aql_query_obj.search(suspicion_chart_aql_query)
        search_res_json = json.loads(search_res)
        search_id = search_res_json['search_id']
        query_response = aql_query_obj.wait_for_response(search_id)
        if query_response:
            query_res_json = json.loads(query_response)
            formdata['pieChartData'] = query_res_json['events']
            if formdata['pieChartData']:
                qpylib.log("Dashboard : Top Suspicions data loaded.")

        return render_template("dashboard.html", form=formdata)
    except Exception as e:
        qpylib.log("Dashboard area Error " + str(e))
        raise

@app.route('/open_affected_machines_and_users_details', methods=['GET'])
def open_affected_machines_and_users_details():
    qpylib.log("open_affected_machines_and_users_details context: " + str(request.args))
    server = request.args.get('server')
    malop_id = request.args.get('malop_id')
    detection_engine = request.args.get('detection_engine')
    server_exists, index, log_source = _check_server_in_config(server)
    if server_exists:
        qpylib.log(log_source, 'DEBUG')
        form_data = dict()
        machine_data = []
        user_data = []
        crapi = CRAPI(index)
        if detection_engine == 'antivirus':
            poll_malop = PollMalopInbox()
            malop_detailed_data = poll_malop.poll_non_edr_malop_data(crapi, malop_id)
            machines = malop_detailed_data.get('machines')
            if machines:
                for machine in machines:
                    machine_record = dict()
                    machine_record['machine_name'] = '{}'.format(machine.get('displayName'))
                    machine_record['is_isolated'] = '{}'.format(machine.get('isolated'))
                    machine_record['os_version'] = '{}'.format(machine.get('osType'))
                    machine_record['is_connected'] = 'Online' if machine.get('connected') else 'Offline'
                    machine_data.append(machine_record)
        else:
            url = "/rest/visualsearch/query/simple"
            query='{"queryPath":[{"requestedType":"MalopProcess","filters":[],"guidList":["' + malop_id + '"],"connectionFeature":{"elementInstanceType":"MalopProcess","featureName":"suspects"} },{"requestedType":"Process","filters":[],"connectionFeature":{"elementInstanceType":"Process","featureName":"ownerMachine"} },{"requestedType":"Machine","filters":[],"isResult":true}],"totalResultLimit":1000,"perGroupLimit":1200,"perFeatureLimit":1200,"templateContext":"SPECIFIC","queryTimeout":null,"customFields":["isActiveProbeConnected","osVersionType","isServer","isConnected","isIsolated","self","users","processes","pylumId","isWindows","adSid","adOU","adDisplayName","adDNSHostName","adDepartment","adCompany","adMachineRole","adLocation","adOrganization","elementDisplayName"]}'
            response = crapi.post(url, query)
            if response.status_code == 200:
                readjson = json.loads(response.text)
                for machine_rec in readjson['data']['resultIdToElementDataMap']:
                    machine = readjson['data']['resultIdToElementDataMap'][machine_rec]
                    machine_record = dict()
                    if 'elementDisplayName' in machine['simpleValues']:
                        machine_record['machine_name'] = ', '.join(machine['simpleValues']['elementDisplayName']['values'])
                    if 'isIsolated' in machine['simpleValues']:
                        machine_record['is_isolated'] = ', '.join(machine['simpleValues']['isIsolated']['values'])
                    if 'osVersionType' in machine['simpleValues']:
                        machine_record['os_version'] = ', '.join(machine['simpleValues']['osVersionType']['values'])
                    if 'isConnected' in machine['simpleValues']:
                        machine_record['is_connected'] = 'Online' if machine['simpleValues']['osVersionType']['values'][0] == 'true' else 'Offline'
                    machine_record['is_new'] = False
                    machine_data.append(machine_record)
        if machine_data:
            existing_machines = _fetch_existing_machines(malop_id, log_source)
            if existing_machines:
                machine_data = _flag_new_data(existing_machines, machine_data)
        form_data['machine_data'] = machine_data

        #Get Malop Users
        custom_fields = ["ownerOrganization","domain","self","processes","isAdmin","passwordAgeDays","adSid","adDisplayName","adLogonName","adDepartment","adCompany","elementDisplayName"]
        path = [
            {
            'requestedType': 'MalopProcess',
            'filters': [],
                    "guidList": malop_id.split(','),
            'connectionFeature': {'elementInstanceType': 'MalopProcess', 'featureName': 'suspects'}
        },
        {
            'requestedType': 'Process',
            'filters': [],
            'connectionFeature': {'elementInstanceType': 'Process', 'featureName': 'calculatedUser'}
        },
            {
            'requestedType': 'User',
                    'filters': [],
            'isResult': True
            }
        ]

        query = {
            'customFields': custom_fields,
            'perFeatureLimit': 1200,
            'perGroupLimit': 1000,
            'queryPath': path,
            'queryTimeout': 120000,
            'templateContext': 'MALOP',
            'totalResultLimit': 1000
        }

        query = json.dumps(query)
        url = "/rest/visualsearch/query/simple"
        response = crapi.post(url, query)
        if response.status_code == 200:
            readjson = json.loads(response.text)
            for user_rec in readjson['data']['resultIdToElementDataMap']:
                user = readjson['data']['resultIdToElementDataMap'][user_rec]
                user_record = dict()
                user_record['UserGuid'] = user_rec
                if 'elementDisplayName' in user['simpleValues']:
                    user_record['user_name']=', '.join(user['simpleValues']['elementDisplayName']['values'])
                if 'passwordAgeDays' in user['simpleValues']:
                    user_record['passwordAgeDays']=', '.join(user['simpleValues']['passwordAgeDays']['values'])
                if 'privileges' in user['simpleValues']:
                    user_record['privileges']=', '.join(user['simpleValues']['privileges']['values'])
                if 'isAdmin' in user['simpleValues']:
                    user_record['isAdmin']= True if user['simpleValues']['isAdmin']['values'][0] == 'true' else False
                user_data.append(user_record)
        form_data['user_data'] = user_data

        return render_template("affected_machines_and_users.html", form=form_data)
    else:
        qpylib.log('Credentials not found in the config for server: {}'.format(server))
        return 'Credentials not found in the config for server: {}'.format(server)

@app.route('/open_connection_details', methods=['GET'])
def open_connection_details():
    qpylib.log("open_connection_details context: " + str(request.args))
    server = request.args.get('server')
    malop_id = request.args.get('malop_id')
    server_exists, index, log_source = _check_server_in_config(server)
    if server_exists:
        qpylib.log(log_source, 'DEBUG')
        form_data = dict()
        connection_data = list()
        cr_api = CRAPI(index)
        connection_fetcher = MalopConnectionFetcher()
        connection_response = connection_fetcher.get_connection_for_malop(cr_api, malop_id)
        if connection_response:
            for guid in connection_response:
                connection_dict = {}
                connection_dict['name'] = connection_response[guid]['v1'].get('elementDisplayName')
                connection_dict['direction'] = connection_response[guid]['v1'].get('direction')
                connection_dict['ip'] = connection_response[guid]['v1'].get('serverAddress')
                connection_dict['port'] = connection_response[guid]['v1'].get('serverPort')
                connection_dict['port_type'] = connection_response[guid]['v1'].get('portType')
                connection_dict['received_bytes'] = connection_response[guid]['v1'].get('aggregatedReceivedBytesCount')
                connection_dict['transmitted_bytes'] = connection_response[guid]['v1'].get('aggregatedTransmittedBytesCount')
                connection_dict['remote_address'] = connection_response[guid]['v1'].get('remoteAddressCountryName')
                connection_dict['owner_machine'] = connection_response[guid]['v1'].get('ownerMachine')
                connection_dict['owner_process'] = connection_response[guid]['v1'].get('ownerProcess')
                if 'dnsQuery' in connection_response[guid]['v1']:
                    connection_dict['domain'] = connection_response[guid]['v1'].get('dnsQuery').split('>')[0].strip()
                else:
                    connection_dict['domain'] = 'N/A'
                connection_data.append(connection_dict)
        form_data['connection_data'] = connection_data
        return render_template("connection_data.html", form=form_data)
    else:
        qpylib.log('Credentials not found in the config for server: {}'.format(server))
        return 'Credentials not found in the config for server: {}'.format(server)

@app.route('/cr_update_malop_status', methods=['GET', 'POST'])
def cr_update_malop_status():
    qpylib.log("cr_update_malop_status context: " + str(request.args))
    server = request.args.get('server')
    server_exists, index, log_source = _check_server_in_config(server)
    if server_exists:
        qpylib.log(log_source, 'DEBUG')
        messages = []
        if request.method == 'GET':
            malop_id = request.args.get('malop_id')
        elif request.method == 'POST':
            malop_id = request.form['malop_id']
        formdata = dict()
        crapi = CRAPI(index)
        malop_status = crapi.get_malop_status(malop_id)
        qpylib.log("cr_update_malop_status malop_status: " + str(malop_status))
        formdata['malop_status'] = malop_status
        formdata['malop_id'] = malop_id
        if request.method == 'POST':
            try:
                formdata['malop_id'] = request.form['malop_id']
                malop_status = request.form['malop_status']
                query = { malop_id : malop_status }
                query = json.dumps(query)
                url = "/rest/crimes/status"
                crapi = CRAPI(index)
                response = crapi.post(url, query)
                formdata['malop_status'] = request.form['malop_status']
                messages.append("Cybereason Malop status updated successfully.")
            except Exception as e:
                qpylib.log("config Error " + str(e))
                messages.append("Error while updating the Cybereason malop status.")
        return render_template("cr_malop_status.html", form=formdata, messages=messages)
    else:
        qpylib.log('Credentials not found in the config for server: {}'.format(server))
        return 'Credentials not found in the config for server: {}'.format(server)

@app.route('/get_lookup_context', methods=['GET'])
def get_lookup_context():
    detection_engine = 'edr'
    context = request.args.get("context")
    if 'detection-malop' in context:
        detection_engine = 'antivirus'
    server = context.split('//')[1].split(':')[0].strip()
    malop_id = context.split('malop/')[1].strip()
    return json.dumps({"app_id":qpylib.get_app_id(),"server":server,"context":context,"malop_id":malop_id,"detection_engine":detection_engine})

# # Use this endpoint for test on local machine
# @app.route('/poll_malops', methods=['GET'])
# def poll_malops():
#     try:
#         poll_malop = PollMalopInbox()
#         poll_malop.main()
#     except Exception as exc:
#         qpylib.log("Malops poll: Exception occured while polling Malops {}".format(exc))
#         qpylib.log(traceback.format_exc())
#     return 'Pong!'
