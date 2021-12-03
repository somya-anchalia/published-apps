import json
import logging as logger
import math
import base64
import os
import sys
import time
import datetime
import requests
import re
import glob
import gzip
from zipfile import ZipFile
import uuid
import configparser
from Utilities import KennyLoggins
from random import randint
from event_name_filter import event_name_filter
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
import platform
import traceback
if 'Linux' in platform.system():
    from signal import signal, SIGPIPE, SIG_DFL
    signal(SIGPIPE, SIG_DFL)

# dir_path = os.path.dirname(os.path.realpath(__file__))

__author__ = 'ksmith'

_MI_APP_NAME = 'Cybereason For Splunk Modular Input'
_APP_NAME = 'CybereasonForSplunk'

kl = KennyLoggins()
log = kl.get_logger(_APP_NAME, "restclient", logger.INFO)

log.debug("logging setup complete")
log_location = make_splunkhome_path(['var', 'log', 'splunk', _APP_NAME])
server_conf_location = make_splunkhome_path(['etc', 'system', 'default'])


class CybereasonAPIError(Exception):
    pass


class CybereasonClient:

    def __init__(self, base_url=None, username=None, password=None, proxy=None, modular_input=None, auth_type=None, utils=None, cred_realm=None, **kwargs):
        try:
            t = base_url.split(":")
            self.mi = modular_input
            self.password = password
            self.port = t[1]
            self.username = username
            self.server = t[0]
            self.base_url = "https://{}:{}".format(self.server, self.port)
            self.login_url = self.base_url + "/login.html"
            self._useproxy = False
            self._log = log
            self.verify = True
            self.child_processes = dict()
            self.auth_type = auth_type
            self.is_first_poll = True
            self.jwt_auth_token = None
            self.jwt_expiry_minutes = 0
            self.utils = utils
            self.cred_realm = cred_realm
            self.headers = {"Content-Type": "application/json", "User-Agent": "CybereasonSplunkIntegration/1.5.0 (target="+self._get_server_address()+")"}
            log.debug("action=init func=__init__ initial_verify={} passed={}".format(self.verify, kwargs))
            if kwargs.get("ssl_verify", None) is not None:
                log.debug("action=init func=__init__ set_verify={}".format(self._check_false(kwargs.get("ssl_verify"))))
                self.verify = self._check_false(kwargs.get("ssl_verify"))
            if proxy is not None and proxy is not "not_configured" and proxy is not "none" and proxy:
                log.debug("component=proxy found proxy configuration")
                pconfig = proxy

                if "host" not in pconfig or "port" not in pconfig:
                    log.error(
                        "component=proxy action=get_proxy_config status=failed step='host_or_port'")
                    raise AttributeError("Failed to find Hostname or Port in Configuration Object")
                protocol = "http"
                if "protocol" in pconfig:
                    protocol = pconfig["protocol"]
                authentication = ""
                hostname = pconfig["host"]
                proxyport = pconfig["port"]
                log.debug("component=proxy set hostname={0} and port={1} in proxy configuration".format(hostname,
                                                                                                        proxyport))
                if "authentication" in pconfig:
                    log.debug("component=proxy found authentication settings")
                    authconfig = pconfig["authentication"]
                    if "username" not in authconfig or "password" not in authconfig:
                        log.error("component=proxy action=get_proxy_authentication_config status=failed")
                        raise AttributeError("Failed to find Username or password in Configuration Object")
                    authentication = "{0}:{1}@".format(authconfig["username"], authconfig["password"])
                proxy = {"http": "{0}://{1}{2}:{3}/".format(protocol, authentication, hostname, proxyport),
                         "https": "{0}://{1}{2}:{3}/".format(protocol, authentication, hostname, proxyport)}
                self.proxies = proxy
                self._useproxy = True
            self._create_session()
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            addl = "file={} line={} error={}".format(fname, exc_tb.tb_lineno, e)
            log.error("{}".format(addl))
            raise e

    def _get_server_address(self):
        target = 'unknown'
        try:
            server_conf_path = os.path.join(server_conf_location, 'server.conf')
            if os.path.exists(server_conf_path):
                config = configparser.ConfigParser()
                config.read(server_conf_path)
                target = str(config['dfs']['spark_master_host'])
        except Exception as exc:
            log.exception(f'Error occured while reading server name. Exception: {exc}\n')
        return target

    def _check_true(self, v):
        if v == "TRUE" or v == 1 or v == "True" or v is True or v == "1":
            log.debug("action=_check_true v={} result=True".format(v))
            return True
        else:
            log.debug("action=_check_true v={} result=False".format(v))
            return False

    def _check_false(self, v):
        if v == "FALSE" or v == 0 or v == "False" or v is False or v == "0":
            log.debug("action=_check_false v={} result=False".format(v))
            return False
        else:
            log.debug("action=_check_false v={} result=True".format(v))
            return True

    def __check_jwt_expiry(self, jwt_creation_timestamp):
        expired_flag = False
        latest = int(math.ceil(time.mktime(datetime.datetime.now().timetuple())))
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
        log.info('JWT token will be renewed after {} minutes'.format(self.jwt_expiry_minutes))

    def __fetch_jwt(self):
        log.info('Generating new JWT token')
        url = self._build_endpoint("auth/token")
        res = requests.post(url=url,auth=(self.username,self.password))
        self.jwt_auth_token = res.content.decode("utf-8")
        if self.jwt_auth_token:
            self.__set_jwt_expiry_mins()
        else:
            log.info('JWT token not received')

    def __new_jwt_token(self, jwt_state_file, jwt_expiry):
        self.__fetch_jwt()
        if self.jwt_auth_token:
            latest = int(math.ceil(time.mktime(datetime.datetime.now().timetuple())))
            with open(jwt_state_file, 'w') as checkpoint:
                checkpoint.write(str(latest))
            with open(jwt_expiry, 'w') as checkpoint:
                checkpoint.write(str(self.jwt_expiry_minutes))
            self.utils.set_credential('JWT_token_' + self.cred_realm, self.username, self.jwt_auth_token)

    def __add_jwt_to_header(self):
        '''
            Add the JWT token to the headers dict
        '''
        jwt_state_dir = log_location + '/jwt_token_state/{}-{}-{}'.format(self.cred_realm, self.server, self.username)
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
                log.info('JWT token has expired, generating new one')
                self.__new_jwt_token(jwt_state_file, jwt_expiry)
            else:
                log.debug('Using saved JWT token')
                self.jwt_auth_token = self.utils.get_credential('JWT_token_' + self.cred_realm, self.username)
        else:
            self.__new_jwt_token(jwt_state_file, jwt_expiry)
        if self.jwt_auth_token:
            self.headers["Authorization"] = 'Bearer ' + self.jwt_auth_token

    def _create_session(self, counter=0):
        counter = counter + 1
        log.debug("action=create_session counter={}".format(counter))
        if counter > 10:
            log.fatal("action=create_session counter={} over_10".format(counter))
            return
        try:
            if self.auth_type == 'jwt_token':
                self.session = requests
                self.__add_jwt_to_header()
            else:
                self.session = requests.session()
            log.debug("action=create_session ssl_verify={}".format(self.verify))
            self.headers.update({"Content-Type": "application/x-www-form-urlencoded"})
            if self._useproxy:
                response = self.session.post(self.login_url,
                                             data={"username": self.username, "password": self.password},
                                             proxies=self.proxies, verify=self.verify,
                                             headers=self.headers)
            else:
                response = self.session.post(self.login_url,
                                             data={"username": self.username, "password": self.password},
                                             verify=self.verify,
                                             headers=self.headers)
            self.headers.update({"Content-Type": "application/json"})

            code = response.status_code
            if code == 200 and "error" in response.url:
                raise CybereasonAPIError(
                    "type='login error' url='{}' code=200 possible_reason='check for bad credentials'".format(
                        response.url))

            if code == 200 and "reset.html" in response.url:
                raise CybereasonAPIError(
                    "type='login_error' url='{}' code=200 possible_reason='password reset required'".format(
                        response.url))

            if code == 200 and "Authentication Code" in response.text:
                raise CybereasonAPIError(
                    "type='login error' url='{}' code=200 possible_reason='check for TWO FACTOR enabled'".format(
                        response.url))

            log.debug("action=create_session code={} resp='{}'".format(code, response))
            if code == 500:
                raise CybereasonAPIError("Server error", response.json())

            if code == 410:
                raise CybereasonAPIError("Item no longer exists", response.json())

            if code == 400:
                raise CybereasonAPIError("Malformed query", response.json())

            if code != 200:
                raise CybereasonAPIError("Query failed", response.json())

            if 'input type="password"' in response.text or "<app-login>" in response.text:
                [log.debug(
                    "action=login subsection=history code={} url={}".format(x.status_code,
                                                                            x.url
                                                                            ))
                    for x in response.history]
                log.debug("action=login msg='Cookie expired, performing login again'")
                return self._create_session(counter=counter)
            log.debug("action=login code={} status=end_of_session session={}".format(code, self.session))

            if "<app></app>" in response.text:
                log.info(f"action=login msg='assuming good login, resuming operations for server: {self.server} and user: {self.username}'")

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            addl = "action=login file={} exception_line={} error_type={} {}".format(fname, exc_tb.tb_lineno,
                                                                                    type(e),
                                                                                    e)
            log.error("{}".format(addl))
            raise e

    def _build_endpoint(self, endpoint="visualsearch/query/simple", **kwargs):
        return "https://{}:{}/rest/{}".format(self.server, self.port, endpoint)

    def _call(self, data=None, url=None, **kwargs):
        self._log.debug("calling use_proxy={} url={} data={}".format(self._useproxy, url, data))
        ret = None
        if self.auth_type == 'jwt_token':
            self.__add_jwt_to_header()
        try:
            if data is None:
                if self._useproxy:
                    log.debug("action=call_get use_proxy=true")
                    ret = self.session.get(url=url, headers=self.headers, verify=self.verify, proxies=self.proxies)
                else:
                    log.debug("action=call_get use_proxy=false")
                    ret = self.session.get(url=url, headers=self.headers, verify=self.verify)
                return ret
            else:
                if self._useproxy:
                    log.debug("action=call_post use_proxy=true")
                    ret = self.session.post(url=url, headers=self.headers, verify=self.verify, data=data, proxies=self.proxies)
                else:
                    log.debug("action=call_post use_proxy=false url={} data={} headers={}".format(url, data, self.headers))
                    try:
                        ret = self.session.post(url=url, headers=self.headers, verify=self.verify, data=data)
                    except Exception as e:
                        log.debug("action=call_post step=error_caught_on_post e={} ret={}".format(e, ret))
                return ret
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            addl = "file={} line={} error={}".format(fname, exc_tb.tb_lineno, e)

            if ret is not None:
                if "unauthorized" in ret.content:
                    log.error("func=_call condition=unauthorized {} ret={}".format(addl, ret.text))
                    raise Exception("code=403 error_message=\"unauthorized user\" {}".format(e))
                elif "HTTP Status 500" in ret.text:
                    log.error("func=_call condition=server_error {} req={}".format(addl, data))
                    raise Exception("code=500 error_message=\"SERVER_ERROR\" {}".format(e))
                else:
                    log.error("func=_call condition=unknown {} ret={}".format(addl, ret.text))
                    raise Exception("unknown Exception {}: {}".format(e, ret.text))
            else:
                log.error("func=_call condition=unspecified_error {} ret={}".format(addl, ret.text))
                raise Exception(
                    "code=400 error_message=\"Unspecified Error\" {} ret_content=\"{}\"".format(e, ret))

    def _build_query(self, **kwargs):
        return {}

    def process_malop_elements(self, malop):
        for elem in malop["elementValues"]:
            self.mi.sourcetype("cybereason:malops:{}".format(elem))
            log.debug("parsing elementValues {}".format(elem))
            if not malop["elementValues"][elem]["elementValues"] is None:
                for elem_indv in malop["elementValues"][elem]["elementValues"]:
                    elem_indv["malop_guid"] = malop["malop_guid"]
                    elem_indv["timestamp"] = int(str(malop["malopLastUpdateTime"])[0:10])
                    elem_indv["rootCauseElementNames"] = malop["rootCauseElementNames"]
                    self.mi.print_event(json.dumps(elem_indv))

    def get_time_bound_malops(self, earliest=0,
                              latest=int(math.ceil(time.mktime(datetime.datetime.now().timetuple())))):
        try:
            log.debug("get_time_bound_malops")
            if earliest < 1:
                # CYBR-7991
                earliest = int(
                    math.ceil(time.mktime((datetime.datetime.now() - datetime.timedelta(days=365)).timetuple())))
            log.debug("action=get_time_bound_malops earliest={} latest={}".format(earliest, latest))
            query = {"queryPath": [{"requestedType": "MalopProcess", "result": "true",
                                    "timeRange": {"startFeatureId": "malopLastUpdateTime",
                                                  "endFeatureId": "malopLastUpdateTime",
                                                  "startTime": "{}000".format(earliest),
                                                  "endTime": "{}000".format(latest)}}], "totalResultLimit": 75000,
                     "perGroupLimit": 75000, "perFeatureLimit": 75000, "templateContext": "MALOP"}
            ret = self._call(data=json.dumps(query), url=self._build_endpoint())
            if not ret.status_code == 200:
                raise Exception(ret.content)
            my_obj = json.loads(ret.content)
            severity_dict = self._get_mapped_severities(earliest, latest)
            total_events = []
            log.info(f'Polled {len(my_obj["data"]["resultIdToElementDataMap"])} malops')
            for guid in my_obj["data"]["resultIdToElementDataMap"]:
                try:
                    log.debug("processing {}".format(guid))
                    self.child_processes.clear()
                    base_obj = my_obj["data"]["resultIdToElementDataMap"][guid]
                    base_obj["malop_guid"] = guid
                    base_obj["severity"] = self.get_malop_severity(guid, severity_dict)
                    # The malopLastUpdateTime is 13 digits which is an issue so only pull the 1st 10 digits
                    for idx, item in enumerate(base_obj["simpleValues"]["malopLastUpdateTime"]["values"]):
                        new_malop_last_update_time = int(
                            str(base_obj["simpleValues"]["malopLastUpdateTime"]["values"][idx])[0:10])
                        base_obj["timestamp"] = str(new_malop_last_update_time).encode("utf-8").decode("utf-8")
                        base_obj["simpleValues"]["malopLastUpdateTime"]["values"][idx] = base_obj["timestamp"]

                    if self.is_webshell_malop(guid, my_obj):
                        parent_processes = my_obj["data"]["resultIdToElementDataMap"][guid]["elementValues"]["primaryRootCauseElements"]["elementValues"]
                        for parent_process in parent_processes:
                            self.set_child_processes([parent_process["guid"]])
                        if self.child_processes:
                            child_processes = list(self.child_processes.values())
                            self.handle_child_processes(guid, base_obj["timestamp"], child_processes, parent_process["name"])

                    single_malop = self.get_single_malop(malop_guid=guid)
                    if single_malop is not None:
                        guid_detail = json.loads(single_malop)

                        for idx, item in enumerate(guid_detail["data"]["resultIdToElementDataMap"][guid]["simpleValues"][
                                                    "malopLastUpdateTime"]["values"]):
                            new_malop_last_update_time = int(str(
                                guid_detail["data"]["resultIdToElementDataMap"][guid]["simpleValues"][
                                    "malopLastUpdateTime"]["values"][idx])[0:10])
                            guid_detail["data"]["resultIdToElementDataMap"][guid]["simpleValues"]["malopLastUpdateTime"][
                                "values"][idx] = str(new_malop_last_update_time).encode("utf-8").decode("utf-8")

                        gd = guid_detail["data"]["resultIdToElementDataMap"][guid]["simpleValues"]
                        log.debug("processing base simpleValues")
                        [self._process_detail(x, base_obj["simpleValues"], base_obj,
                                            parent_function="get_time_bound_malops_base") for x in gd]
                        log.debug("processing detail simpleValues")
                        [self._process_detail(x, gd, base_obj, parent_function="get_time_bound_malops_detail") for x in gd]
                        if "iconBase64" in base_obj["simpleValues"]:
                            base_obj["simpleValues"]["iconBase64"] = "removed_for_size"
                        if "iconBase64" in base_obj:
                            base_obj["simpleValues"] = "removed_for_size"
                        my_obj["data"]["resultIdToElementDataMap"][guid]["simpleValues"] = "moved_to_root"
                        total_events.append(my_obj["data"]["resultIdToElementDataMap"][guid])
                except Exception as e:
                    log.info(f'Exception occured while processing malop id {guid}. Exception details: {e}')
                    log.error(f'Traceback:\n{traceback.format_exc()}')
            self.mi.sourcetype("cybereason:malops")
            self.mi.print_multiple_events(total_events, time_field="malopLastUpdateTime")
            [self.process_malop_elements(x) for x in total_events]
            return [self._api_return(operation="time_bound_malops", total_results=len(total_events))]
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            myJson = "message=\"{}\" exception_type=\"{}\" exception_arguments=\"{}\" filename=\"{}\" line=\"{}\" section=\"{}\"".format(
                str(e), type(e).__name__, e, fname, exc_tb.tb_lineno, "get_time_bound_malops")
            log.error("{}".format(myJson))
            raise e

    def _process_detail(self, detail, obj_values, base_object, parent_function="not_defined"):
        try:
            log.debug("func=_process_detail pf={} action=start object=_process_detail".format(parent_function))
            if detail in obj_values:
                self._log.debug("func=_process_detail pf={} is_detail_in_obj_values={}".format(parent_function,
                                                                                               detail in obj_values))
                if obj_values[detail]["values"] is None or obj_values[detail]["values"] == []:
                    self._log.debug(
                        "func=_process_detail pf={} obj_values[{}]['values'] is None".format(parent_function, detail))
                    base_object[detail] = ""
                else:
                    self._log.debug(
                        "func=_process_detail pf={} obj_values[{}]['values']={}".format(parent_function, detail,
                                                                                        obj_values[detail]["values"]))
                    whasup = obj_values[detail]["values"].pop()
                    self._log.debug("func=_process_detail pf={} whasup={}".format(parent_function, whasup))
                    obj_values[detail]["values"].append("{}".format(whasup))
                    self._log.debug(
                        "func=_process_detail pf={} action=assigning detail={} to base_object".format(parent_function,
                                                                                                      detail))
                    if detail != "comments":
                        base_object[detail] = ",".join(obj_values[detail]["values"])
                        self._log.debug("func=_process_detail pf={} base_object[{}]={}".format(parent_function, detail,
                                                                                               base_object[detail]))
                    else:
                        comments = str(obj_values[detail]["values"])
                        if comments:
                            if len(comments) < 1000:
                                base_object[detail] = comments
                            else:
                                base_object[detail] = comments[:997] + '....'

                self._log.debug("func=_process_detail pf={} action=returning base_object".format(parent_function))
                return base_object
        except Exception as e:
            log.error("{}".format(e))
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            myJson = "func=_process_detail pf={} message=\"{}\" " \
                     "exception_type=\"{}\" exception_arguments=\"{}\" " \
                     "filename=\"{}\" line=\"{}\" section=\"{}\"".format(parent_function,
                                                                         str(e), type(e).__name__, e, fname,
                                                                         exc_tb.tb_lineno, "process_detail")
            log.error("{}".format(myJson))
            raise e
        finally:
            return base_object

    def get_single_malop(self, malop_guid=None):
        log.debug("get_single_malop")
        if malop_guid is None:
            return None, None
        query = {"queryPath": [
            {"requestedType": "MalopProcess", "guidList": ["{}".format(malop_guid)],
             "isResult": "true"}],
            "totalResultLimit": 75000, "perGroupLimit": 75000, "perFeatureLimit": 75000,
            "templateContext": "OVERVIEW"}
        ret = self._call(data=json.dumps(query), url=self._build_endpoint("crimes/unified"))
        if ret is None:
            return None, None
        if not ret.status_code == 200:
            raise Exception(ret.content)
        return ret.content

    def get_all_malops(self):
        log.debug("get_all_malops")
        return self.get_time_bound_malops(earliest=1)

    def get_all_users(self):
        # rest / investigation / columns / undefined / User
        ret = None
        try:
            log.debug("get_all_users")
            ret = self._call(url=self._build_endpoint(endpoint="investigation/columns/undefined/User"))
            if not ret.status_code == 200:
                raise Exception(ret.content)
            myar = json.loads(ret.content)
            myar.append("elementDisplayName")
            query = {"queryPath": [{"requestedType": "User", "filters": [], "isResult": "true"}],
                     "totalResultLimit": 75000,
                     "perGroupLimit": 75000, "perFeatureLimit": 75000, "templateContext": "SPECIFIC",
                     "queryTimeout": 120000,
                     "customFields": myar}
            ret = self._call(url=self._build_endpoint(), data=json.dumps(query))
            if not ret.status_code == 200:
                raise Exception(ret.content)
            my_obj = json.loads(ret.content)
            total_events = []
            for guid in my_obj["data"]["resultIdToElementDataMap"]:
                try:
                    base_obj = my_obj["data"]["resultIdToElementDataMap"][guid]
                    base_obj["guid"] = guid
                    gd = base_obj["simpleValues"]
                    [self._process_detail(x, gd, base_obj, parent_function="get_all_users") for x in gd]
                    base_obj["simpleValues"] = "moved_to_root_object"
                    my_obj["data"]["resultIdToElementDataMap"][guid]["simpleValues"] = "moved_to_root"
                    total_events.append(my_obj["data"]["resultIdToElementDataMap"][guid])
                except Exception as e:
                    log.info(f'Exception occured while processing user data for malop id {guid}. Exception details: {e}')
                    log.error(f'Traceback:\n{traceback.format_exc()}')
            self.mi.sourcetype("cybereason:users")
            self.mi.print_multiple_events(total_events)
            return [self._api_return(operation="users", total_results=len(total_events))]
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            myJson = "message=\"{}\" exception_type=\"{}\" exception_arguments=\"{}\" filename=\"{}\" line=\"{}\" section=\"{}\"".format(
                str(e), type(e).__name__, e, fname, exc_tb.tb_lineno, "get_all_users")
            self._log.error(myJson)
            raise e

    def get_features(self):
        return self._call(url=self._build_endpoint(endpoint="features"))

    def _get_175_malware(self, starttime=0, limit=1000):
        try:
            url = self._build_endpoint("malware/query")
            query = {"filters": [
                {"fieldName": "needsAttention", "operator": "Is", "values": [True, False]},
                {"values": [(int(starttime) * 1000)], "fieldName": "timestamp", "operator": "GreaterThan"}],
                "sortingFieldName": "timestamp", "sortDirection": "DESC", "limit": limit, "offset": 0}
            log.debug("action=calling_malware url={} query={}".format(url, json.dumps(query)))
            ret = self._call(url=url, data=json.dumps(query))
            if not ret.status_code == 200:
                raise Exception(ret.content)
            my_obj = json.loads(ret.content)
            if my_obj is None:
                log.debug("action=none_my_obj")
                return [self._api_return(operation="malware", total_results=0, msg="Object Returned is None")]
            if my_obj.get("data") is None:
                log.debug("action=returned_events status={} {}".format(ret.status_code, json.dumps(my_obj)))
                return [self._api_return(operation="malware", total_results=0, msg="Data Object Returned is None")]
            # Do Pagination, sending events as found by limit
            self.mi.sourcetype("cybereason:malware")
            data = my_obj.get("data", {})
            if data.get("malwares"):
                log.debug("action=printing_events length={}".format(len(data.get("malwares"))))
            self.mi.print_multiple_events(data.get("malwares", []))
            log.debug("action=show_object obj={}".format(json.dumps(my_obj)))
            total_results = int(data.get("totalResults", 0))
            log.debug("action=show_total_results total_results={} hasMoreResults={}".format(total_results,
                                                                                            data.get("hasMoreResults",
                                                                                                     False)))
            while data.get("hasMoreResults", False):
                log.debug("action=continue_results hasMoreResults={}".format(data.get("hasMoreResults", False)))
                query.update({"offset" : query["offset"] + 1})
                log.debug(
                    "action=calling_malware offset: {} url={} query={}".format(query["offset"], url, json.dumps(query)))
                ret = self._call(url=url, data=json.dumps(query))
                my_obj = json.loads(ret.content)
                if my_obj is None:
                    my_obj = {"hasMoreResults": False}
                else:
                    if my_obj.get("data") is not None:
                        data = my_obj.get("data", {})
                        if data.get("malwares"):
                            log.debug("action=printing_events length={}".format(len(data.get("malwares"))))
                        self.mi.print_multiple_events(data.get("malwares", []))
                        total_results = total_results + int(data.get("totalResults", 0))
                        log.debug("action=show_total_results total_results={}".format(total_results))
            return [self._api_return(operation="malware", total_results=total_results)]
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            myJson = "message=\"{}\" exception_type=\"{}\" exception_arguments=\"{}\" filename=\"{}\" exception_line=\"{}\" section=\"{}\"".format(
                str(e), type(e).__name__, e, fname, exc_tb.tb_lineno, "get_175_malware")
            self._log.error(myJson)

    def _api_return(self, **kwargs):
        return {"api_operation": kwargs.get("operation", "unknown"), "total_results": kwargs.get("total_results", 0),
                "message": kwargs.get("msg", "no_message_sent")}

    def get_all_malware(self, starttime=0, limit=1000):
        try:
            return self._get_175_malware(starttime=starttime, limit=limit)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            myJson = "message=\"{}\" exception_type=\"{}\" exception_arguments=\"{}\" filename=\"{}\" exception_line=\"{}\" section=\"{}\"".format(
                str(e), type(e).__name__, e, fname, exc_tb.tb_lineno, "get_all_malware")
            self._log.error(myJson)

    def get_time_bound_suspicious(self, requested_type="Process", earliest=0,
                                  latest=int(math.ceil(time.mktime(datetime.datetime.now().timetuple())))):
        try:
            log.debug("get_time_bound_suspicious")
            if earliest < 1:
                # CYB-641
                # earliest = int(
                #     math.ceil(time.mktime((datetime.datetime.now() - datetime.timedelta(hours=4)).timetuple())))
                earliest = int(
                    math.ceil(time.mktime((datetime.datetime.now() - datetime.timedelta(days=90)).timetuple())))
            log.debug("action=get_time_bound_suspicious earliest={} latest={} requestedType={}".format(earliest, latest,
                                                                                                      requested_type))
            ltr = 25000
            query = {"queryPath": [
                {"requestedType": "{}".format(requested_type),
                 "filters": [{"facetName": "hasSuspicions", "values": [True]}],
                 "isResult": "true"}
            ],
                "totalResultLimit": ltr, "perGroupLimit": ltr, "perFeatureLimit": ltr,
                "templateContext": "SPECIFIC",
                "startTime": "{}000".format(earliest),
                "endTime": "{}000".format(latest),
                "customFields": ["elementDisplayName", "creationTime", "endTime", "commandLine",
                                 "isImageFileSignedAndVerified", "imageFile.maliciousClassificationType",
                                 "productType", "children", "parentProcess", "ownerMachine", "calculatedUser",
                                 "imageFile", "imageFile.sha1String", "imageFile.md5String",
                                 "imageFile.companyName",
                                 "imageFile.productName", "iconBase64", "ransomwareAutoRemediationSuspended",
                                 "executionPrevented", "isWhiteListClassification", "matchedWhiteListRuleIds"]}
            ret = self._call(url=self._build_endpoint(), data=json.dumps(query))
            if not ret.status_code == 200:
                raise Exception(ret.content)
            total_events = []
            my_obj = json.loads(ret.content)
            for guid in my_obj["data"]["resultIdToElementDataMap"]:
                try:
                    base_obj = my_obj["data"]["resultIdToElementDataMap"][guid]
                    base_obj["guid"] = guid
                    base_obj["requestedType"] = requested_type
                    gd = base_obj["simpleValues"]
                    [self._process_detail(x, gd, base_obj, parent_function="get_time_bound_suspicous") for x in gd]
                    base_obj["simpleValues"] = "moved_to_root_object"
                    my_obj["data"]["resultIdToElementDataMap"][guid]["simpleValues"] = "moved_to_root"
                    total_events.append(my_obj["data"]["resultIdToElementDataMap"][guid])
                except Exception as e:
                    log.info(f'Exception occured while processing suspicion for malop id {guid}. Exception details: {e}')
                    log.error(f'Traceback:\n{traceback.format_exc()}')
            self._log.debug("AnyFriendOfRicks total_events={} data_length={}".format(len(total_events), len(my_obj)))
            self.mi.sourcetype("cybereason:suspicious")
            self.mi.print_multiple_events(total_events)
            return [self._api_return(operation="get_time_bound_suspicious", total_results=len(total_events),
                                     result_limit=ltr)]
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            myJson = "message=\"{}\" exception_type=\"{}\" exception_arguments=\"{}\" filename=\"{}\" exception_line=\"{}\" section=\"{}\" requested_type={}".format(
                str(e), type(e).__name__, e, fname, exc_tb.tb_lineno, "get_time_bound_suspicious", requested_type)
            self._log.error(myJson)
            raise e

    def _get_mapped_severities(self, earliest, latest):
        '''
        Fetches severity of malops using rest/detection/inbox API
        Parameters:
                earliest (int)
                latest (int)
        Returns:
                severities (dict)
        '''
        log.debug("_get_mapped_severities")
        severities = dict()
        query = {"startTime":"{}000".format(earliest),"endTime":"{}000".format(latest)}
        log.debug("severity query={}".format(query))
        ret = self._call(data=json.dumps(query), url=self._build_endpoint("detection/inbox"))
        if ret is None:
            log.debug("severity query={}".format(query))
            return None
        if not ret.status_code == 200:
            raise Exception(ret.content)
        res_json = ret.json()
        for malop in res_json["malops"]:
            if malop.get("severity"):
                severities[malop.get("guid")] = malop.get("severity")
            else:
                severities[malop.get("guid")] = "Unknown"
        return severities

    def get_malop_severity(self, malop_guid, severity_dict):
        '''
        Gets malop severity from the severity_dict object
        Parameters:
                malop_guid (string)
                severity_dict (dict)
        Returns:
                severity (string)
        '''
        log.debug("get_malop_severity")
        if malop_guid in severity_dict:
            return severity_dict[malop_guid]
        else:
            return "Unknown"

    def get_all_action_logs(self):
        '''
        Fetches user action logs from monitor/global/userAuditLog endpoint
        Parameters: self (object)
        Returns: dict
        '''
        try:
            log.debug("get_all_action_logs")
            log_reader = LogReader()
            last_action_time = None
            user_action_logs_path = log_location + '/user_action_logs/{}-{}'.format(self.cred_realm, self.server)
            parent_zip = user_action_logs_path + '/action_logs.zip'
            extracted_files_path = user_action_logs_path + '/extracted_data'
            checkpoint_file = user_action_logs_path + '/last_polled_timestamp.txt'
            if os.path.exists(checkpoint_file):
                with open(checkpoint_file, 'r') as file:
                    str_timestamp = file.read()
                    last_polled_timestamp = datetime.datetime.strptime(str_timestamp, '%Y-%m-%d %H:%M:%S')
                self.is_first_poll = False
            else:
                last_polled_timestamp = None
            ret = self._call(url=self._build_endpoint(endpoint="monitor/global/userAuditLog"))
            if not ret.status_code == 200:
                raise Exception(ret.content)
            # Unzip the file returned from the api
            log_reader.unzip_file(user_action_logs_path, extracted_files_path, parent_zip, ret.content)
            # Process the log (already unzip) file if it exist
            action_logs_path = extracted_files_path + '/userAuditSyslog.log'
            if os.path.exists(action_logs_path):
                last_action_time = log_reader.read_cef_events(action_logs_path, self.mi, self.is_first_poll, last_polled_timestamp, contains_last_log=True)
                os.remove(action_logs_path)
            # Process all the zip files after extracting the main zip file
            file_count = 1
            zips_count = len(glob.glob1(extracted_files_path, '*.gz'))
            while file_count <= zips_count:
                file_to_process = action_logs_path + '.' + str(file_count)
                file_to_extract = file_to_process +  '.gz'
                if os.path.exists(file_to_extract):
                    f_out = open(file_to_process, 'w')
                    with gzip.open(file_to_extract, 'rb') as input_file:
                        f_out.write(input_file.read().decode("utf-8"))
                    f_out.close()
                    log_reader.read_cef_events(file_to_process, self.mi, self.is_first_poll, last_polled_timestamp)
                    file_count = file_count + 1
                    os.remove(file_to_extract)
                    os.remove(file_to_process)

            # updating last polled time
            if last_action_time:
                timestamp_str = last_action_time
                res = re.sub('UTC', '', timestamp_str).strip()
                log_timestamp = datetime.datetime.strptime(
                    res, '%b %d %Y, %H:%M:%S')
            else:
                log_timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            log.info('Saving the last polled timestamp for Action Logs : {} '.format(log_timestamp))
            with open(checkpoint_file, 'w') as checkpoint:
                checkpoint.write(str(log_timestamp))
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            myJson = "message=\"{}\" exception_type=\"{}\" exception_arguments=\"{}\" filename=\"{}\" line=\"{}\" section=\"{}\"".format(
                str(e), type(e).__name__, e, fname, exc_tb.tb_lineno, "get_all_action_logs")
            self._log.error(myJson)
            raise e

    def is_webshell_malop(self, guid, my_obj):
        '''
        Checks if the malop type is Webshell
        Parameters:
                guid (string)
                my_obj (dict)
        Returns:
                flag (Boolean)
        '''
        try:
            flag = False
            decision_feature = my_obj["data"]["resultIdToElementDataMap"][guid]["simpleValues"]["decisionFeature"]["values"][0]
            if decision_feature == "Process.maliciousWebShellExecution(Malop decision)":
                flag = True
            return flag
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            myJson = "message=\"{}\" exception_type=\"{}\" exception_arguments=\"{}\" filename=\"{}\" line=\"{}\" section=\"{}\"".format(
                str(e), type(e).__name__, e, fname, exc_tb.tb_lineno, "is_webshell_malop")
            self._log.error(myJson)
            raise e

    def get_child_process(self, process_id_list):
        '''
        Makes API call to fetch child processes for Webshell type malops process
        Parameters:
                process_id_list (list)
        Returns:
                childs (dict)
        '''
        ret = None
        element_values = None
        childs = dict()
        try:
            query = {
                "queryPath": [
                    {
                        "requestedType": "Process",
                        "guidList": process_id_list,
                        "result": True
                    }
                ],
                "totalResultLimit": 1000,
                "perGroupLimit": 1000,
                "perFeatureLimit": 100,
                "templateContext": "DETAILS",
                "customFields": [
                    "children"
                ]
            }
            ret = self._call(data=json.dumps(query), url=self._build_endpoint("visualsearch/query/simple"))
            if ret is None:
                log.debug("query={}".format(query))
                return None
            if not ret.status_code == 200:
                raise Exception(ret.content)
            res_json = ret.json()
            processes = res_json["data"]["resultIdToElementDataMap"]
            if len(processes) > 0:
                for guid, process in processes.items():
                    element_values = process.get("elementValues")
                    if element_values and "children" in element_values:
                        _child_proceses = element_values.get("children")["elementValues"]
                        if _child_proceses:
                            for child in _child_proceses:
                                childs[child["guid"]] = child
            return childs
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            myJson = "message=\"{}\" exception_type=\"{}\" exception_arguments=\"{}\" filename=\"{}\" line=\"{}\" section=\"{}\"".format(
                str(e), type(e).__name__, e, fname, exc_tb.tb_lineno, "get_child_process")
            self._log.error(myJson)
            raise e

    def set_child_processes(self, parent_process_id_list):
        '''
        Fetches child processes for Webshell type malop parent and child processes
        Parameters:
                parent_process_id_list (list)
        Returns:
                None
        '''
        childs = self.get_child_process(parent_process_id_list)
        if childs:
            process_id_list = list(childs.keys())
            for key, value in childs.items():
                self.child_processes[key] = value
            self.set_child_processes(process_id_list)
        else:
            log.debug("No child process for the process : {}".format(parent_process_id_list))

    def handle_child_processes(self, malop_guid, timestamp, child_processes, parent_process_name):
        '''
        Ingests child processes for Webshell type malop parent and child processes.
        Parameters:
                malop_id (string)
                timestamp (string)
                child_processes (list)
        Returns:
                None
        '''
        for process in child_processes:
            process["elementType"] = "Child processes"
            process["malop_guid"] = malop_guid
            process["timestamp"] = int(timestamp)
            process_name = process["name"]
            if process["name"] == parent_process_name:
                process["rootCauseElementNames"] = process_name + '(parent process)'
            else:
                process["rootCauseElementNames"] = process_name + '(child process)'
            log.debug("CHILD PROCESS : {}".format(process))
            self.mi.sourcetype("cybereason:malops:rootCauseElements")
            self.mi.print_event(json.dumps(process))

    def get_logon_sessions(self):
        '''
        Fetches logon sessions using rest/visualsearch/query/simple API
        Parameters:
                None
        Returns:
                dict
        '''
        ret = None
        try:
            log.debug("get_logon_sessions")
            past_24h_epoch = round((datetime.datetime.now() + datetime.timedelta(days=-1)).timestamp())
            current_epoch = round(datetime.datetime.now().timestamp())
            query = {"queryPath": [{"requestedType": "LogonSession", "filters":
                            [{"facetName": "creationTime", "filterType": "Between", "values": [past_24h_epoch*1000, current_epoch*1000]}], "isResult":True}],
             "totalResultLimit": 1000, "perGroupLimit": 100, "perFeatureLimit": 100, "templateContext": "SPECIFIC", "queryTimeout": 120000,
             "customFields": ["processes", "ownerMachine", "user", "remoteMachine", "logonType", "creationTime", "endTime", "elementDisplayName"]}
            log.debug("logon query={}".format(query))
            ret = self._call(data=json.dumps(query), url=self._build_endpoint())
            if ret is None:
                log.debug("logon sessions query={}".format(query))
                return None
            if not ret.status_code == 200:
                raise Exception(ret.content)
            res_json = ret.json()
            total_events = []
            for guid, data in res_json["data"]["resultIdToElementDataMap"].items():
                try:
                    base_obj = dict()
                    if "guidString" in data:
                        base_obj["guid"] = data["guidString"]
                    if "elementDisplayName" in data["simpleValues"]:
                        base_obj["element_name"] = data["simpleValues"]["elementDisplayName"]["values"][0]
                    if "ownerMachine" in data["elementValues"]:
                        base_obj["owner_machine"] = data["elementValues"]["ownerMachine"]["elementValues"][0]["name"]
                    if "user" in data["elementValues"]:
                        base_obj["user"] = data["elementValues"]["user"]["elementValues"][0]["name"]
                    if "remoteMachine" in data["elementValues"]:
                        base_obj["remote_machine"] = data["elementValues"]["remoteMachine"]["elementValues"][0]["name"]
                    if "logonType" in data["simpleValues"]:
                        base_obj["logon_type"] = data["simpleValues"]["logonType"]["values"][0]
                    if "creationTime" in data["simpleValues"]:
                        base_obj["created"] = round(int(data["simpleValues"]["creationTime"]["values"][0])/1000)
                    if "processes" in data["elementValues"]:
                        base_obj["processes"] = data["elementValues"]["processes"]["totalValues"]
                    base_obj["tag"] = "authentication"
                    base_obj["action"] = "success"
                    base_obj["app"] = "win:local"
                    base_obj["dest"] = "dest_host"
                    if "remote_machine" not in base_obj:
                        base_obj["remote_machine"] = "Unknown"
                    if "logon_type" not in base_obj:
                        base_obj["logon_type"] = "Unknown"
                    if "user" not in base_obj:
                        base_obj["user"] = "Unknown"
                    total_events.append(base_obj)
                except Exception as e:
                    log.info(f'Exception occured while processing logon session for malop id {guid}. Exception details: {e}')
                    log.error(f'Traceback:\n{traceback.format_exc()}')
            self.mi.sourcetype("cybereason:logon_sessions")
            self.mi.print_multiple_events(total_events)
            return [self._api_return(operation="logon_sessions", total_results=len(total_events))]
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            myJson = "message=\"{}\" exception_type=\"{}\" exception_arguments=\"{}\" filename=\"{}\" line=\"{}\" section=\"{}\"".format(
                str(e), type(e).__name__, e, fname, exc_tb.tb_lineno, "get_logon_sessions")
            self._log.error(myJson)
            raise e


class LogReader:
    '''
    Read CEF events received from the endpoint
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

    def read_cef_events(self, path, modular_input, is_first_poll, last_polled_timestamp=None, contains_last_log=False):
        '''
        Reads the CEF formatted event returned from API
        Parameters: self (object), path (str), modular_input (object), is_first_poll (Boolean), last_polled_timestamp (timestamp), contains_last_log (Boolean)
        Return: last_polled_timestamp (timestamp)
        '''
        last_log_timestamp = None
        with open(path, 'r') as file:
            cef_events = file.readlines()
            for cef_event in cef_events:
                last_log_timestamp = self._process_cef_events(path, modular_input, is_first_poll, last_polled_timestamp, cef_event, contains_last_log)
        if last_log_timestamp:
            return last_log_timestamp

    def _filter_action_log(self, device_name):
        '''
        Parameters: device_name (string)
        Returns: is_filtered_event (Boolean)
        '''
        event_name = device_name.strip().split('/')[1]
        if event_name in event_name_filter:
            return True

    def _process_cef_events(self, path, modular_input, is_first_poll, last_polled_timestamp, cef_event, contains_last_log=False):
        '''
        Parameters: self (object), path (str), modular_input (object), is_first_poll (Boolean), contains_last_log (Boolean)
        Return: last_polled_timestamp (timestamp)
        '''
        is_filtered_event = False
        log_parser = LogParser()
        log_printer = LogPrinter()
        user_action = log_parser.parse(cef_event.strip())
        user_action = {k: None if not v else v for k, v in user_action.items()}
        # adding a uuid to event
        user_action['uuid'] = str(uuid.uuid4())
        # adding validations
        action_status = user_action['actionSuccess']
        user_action['actionSuccess'] = False
        if 'DeviceName' in user_action:
            is_filtered_event = self._filter_action_log(user_action['DeviceName'])
        if is_filtered_event:
            if action_status == "1":
                user_action['actionSuccess'] = True
            if user_action and is_first_poll:
                log_printer.print_log("cybereason:action_logs", modular_input, user_action)
            elif user_action:
                timestamp_str = user_action.get('userActionTime')
                res = re.sub('UTC', '', timestamp_str).strip()
                log_timestamp = datetime.datetime.strptime(res, '%b %d %Y, %H:%M:%S')
                if log_timestamp > last_polled_timestamp:
                    log_printer.print_log("cybereason:action_logs", modular_input, user_action)
        if contains_last_log and user_action:
            return user_action.get('userActionTime')


class LogParser:
    '''
    Parse the CEF event and return a dict with the syslog, header values and the extension
    '''
    def parse(self, str_input):
        '''
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
            spl = re.findall(r'([^=\s]+)=((?:[\\]=|[^=]|)+)(?:\s|$)', extension)
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
            log.info('Could not parse record. Is it valid CEF format?')
            return None
        return values


class LogPrinter:
    '''
    Prints the log as splunk events
    '''
    def print_log(self, source_type, modular_input, log):
        '''
        Parameters: self (object), source_type (str), modular_input (object), log(str)
        Returns: None
        '''
        modular_input.sourcetype(source_type)
        modular_input.print_event(json.dumps(log))