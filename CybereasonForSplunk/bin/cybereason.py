import json
import logging as logger
import math
import os
import re
import sys
import time
import urllib
from datetime import datetime
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from ModularInput import ModularInput
from Utilities import KennyLoggins, Utilities
from cybereason_rest_client import CybereasonClient
import urllib.parse
import platform
import traceback
if 'Linux' in platform.system():
    from signal import signal, SIGPIPE, SIG_DFL
    signal(SIGPIPE, SIG_DFL)

__author__ = 'ksmith'

_MI_APP_NAME = 'Cybereason For Splunk Modular Input'
_APP_NAME = 'CybereasonForSplunk'

_SPLUNK_HOME = make_splunkhome_path([""])

kl = KennyLoggins()
log = kl.get_logger(_APP_NAME, "modularinput", logger.INFO)

log.debug("logging setup complete")


class CybereasonForSplunkModularInput(ModularInput):
    def __init__(self, **kwargs):
        ModularInput.__init__(self, **kwargs)

    def _get_checkpointfile(self, key):
        return os.path.join(self._config["checkpoint_dir"], "{0}_{1}.json".format(re.sub('[^a-zA-Z0-9]', '.', self.host()), key))

    def _validate_arguments(self, val_data):
        """
        :param val_data: The data that requires validation.
        :return:
        RAISE an error if the arguments do not validate correctly. The default is just "True".
        """
        allowed_endpoints = "malops,users,suspicious,malware"
        for evt_type in val_data["endpoints"].split(","):
            if evt_type not in allowed_endpoints:
                raise Exception("Endpoint: {} is invalid. Valid values are {}".format(evt_type, allowed_endpoints))
        if "cybereason_user" not in val_data:
            raise Exception("Username not present.")
        if len(val_data["cybereason_user"]) < 1:
            raise Exception("Username length is not valid. Length: {}".format(len(val_data["cybereason_user"])))
        if "base_url" not in val_data:
            raise Exception("Base URL not present.")
        if "credential_realm" not in val_data:
            raise Exception("Credential Realm is not present.")
        return True


MI = CybereasonForSplunkModularInput(app_name=_APP_NAME, scheme={
    "title": "Cybereason For Splunk",
    "description": "Cybereason allows to collect malops, malware, and more.",
    "args": [
        {"name": "base_url",
         "description": "This is the base_url for the Modular Input to consume information from. Include Port.",
         "title": "Base Url",
         "required": True
         },
        {"name": "cybereason_user",
         "description": "This is the username for the Modular Input to consume information with.",
         "title": "Username",
         "required": True
         },
        {"name": "credential_realm",
         "description": "This is the encrypted credential Realm to use when pulling the credential.",
         "title": "Credential Realm",
         "required": True
         },
        {"name": "endpoints",
         "description": "These are the endpoints (comma separated) to retrieve",
         "title": "Endpoints",
         "required": True
         },
        {"name": "proxy_name",
         "description": "This is the proxy information stanza name.", "title": "Proxy Name", "required": False},
        {"name": "ssl_verify", "description": "Support Only", "title": "SSL Verify", "required": False}
    ]
})


def run():
    MI.start()
    log.info("action=start object=modular_input")
    try:
        utils = Utilities(app_name=_APP_NAME, session_key=MI.get_config("session_key"))
        log.debug("utilities instantiated")
        base_url = MI.get_config("base_url")
        username = MI.get_config("cybereason_user")
        report_ids = MI.get_config("endpoints")
        auth_type = MI.get_config("auth_types")
        cred_realm = MI.get_config("credential_realm")
        if auth_type not in ['basic', 'jwt_token']:
            auth_type = 'basic'
        log.debug("Selected auth type : {}".format(auth_type))
        reports = report_ids.split(",")
        proxy_name = MI.get_config("proxy_name")
        proxy_config = False
        if proxy_name is not None and proxy_name != "not_configured" and proxy_name is not "none":
            proxy_config = utils.get_proxy_configuration(proxy_name)
            log.debug("received_proxy_configuration")
        if "," not in report_ids:
            reports = [report_ids]

        # Account for Python3 change to urllib quote module
        u_cred = utils.get_credential(cred_realm, urllib.parse.quote(username))
        cyb = CybereasonClient(base_url=base_url, username=username, password=u_cred, proxy=proxy_config,
                               ssl_verify=MI.get_config("ssl_verify"), modular_input=MI, auth_type=auth_type, utils=utils, cred_realm=cred_realm)
        log.info("action=lets_get_started object=modular_input")
        if report_ids is None or report_ids is False or report_ids.lower() == "false":
            MI.print_error("No Data Endpoints specified")
        MI.host(base_url)
        MI.source(MI.get_config("name"))
        log.info(f'Polling for Input with Credential_realm: {cred_realm}, Username: {username}, Server: {base_url}')
        for report_id in reports:
            try:
                log.info("action=start object={}".format(report_id))
                chk = MI._get_checkpoint(report_id)
                now = int(math.ceil(time.mktime(datetime.now().timetuple())))
                if chk is None:
                    chk = {}
                if "last_time" not in chk:
                    chk["last_time"] = 0
                log.info("checkpoint for endpoint={} is {}".format(report_id, chk))
                events = []
                log.info("query for information: {}".format(report_id))
                MI.sourcetype("cybereason:{}".format(report_id))
                if report_id == "malops":
                    events = cyb.get_time_bound_malops(earliest=chk["last_time"], latest=now)
                    MI.sourcetype("cybereason:api")
                    if events:
                        MI.print_multiple_events(events, time_field="malopLastUpdateTime")
                elif report_id == "users":
                    events = cyb.get_all_users()
                    if events:
                        MI.print_multiple_events(events)
                elif report_id == "suspicious":
                    events = cyb.get_time_bound_suspicious(requested_type="Process",
                                                           earliest=chk["last_time"], latest=now)
                    MI.sourcetype("cybereason:api")
                    if events:
                        MI.print_multiple_events(events)
                elif report_id == "malware":
                    events = cyb.get_all_malware(starttime=chk.get("last_time", 0), limit=1000)
                    MI.sourcetype("cybereason:api")
                    if events:
                        MI.print_multiple_events(events)
                elif report_id == "action_logs":
                    cyb.get_all_action_logs()
                elif report_id == "logon_sessions":
                    events = cyb.get_logon_sessions()
                    MI.sourcetype("cybereason:api")
                    if events:
                        MI.print_multiple_events(events)
                else:
                    raise Exception("No Report {} found".format(report_id))
                if events:
                    log.debug("pulled_events = {}".format(len(events)))
                log.debug("query executed")
                chk["last_time"] = now
                MI._set_checkpoint(report_id, object=chk)
                MI.sourcetype("cybereason:api")
                if events:
                    MI.print_event(json.dumps({"last_checkpoint": chk["last_time"], "object": report_id,
                                           "events_returned": len(events)}))
                log.info("action=stop object={}".format(report_id))
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                myJson = "message=\"{}\" exception_type=\"{}\" exception_arguments=\"{}\" filename=\"{}\" exception_line=\"{}\" input=\"{}\" section=\"{}\" credential_realm=\"{}\" username=\"{}\"".format(
                    str(e), type(e).__name__, e, fname, exc_tb.tb_lineno, MI.get_config("name"), report_id, cred_realm, username)
                log.error("{}".format(myJson))
                log.error(f'Traceback:\n{traceback.format_exc()}')
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        myJson = "message=\"{}\" exception_type=\"{}\" exception_arguments=\"{}\" filename=\"{}\" line=\"{}\" input=\"{}\"".format(
            str(e), type(e).__name__, e, fname, exc_tb.tb_lineno, MI.get_config("name"))
        log.error("{}".format(myJson))
    finally:
        log.info("action=stop object=modular_input")
        MI.stop()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":
            MI.scheme()
        elif sys.argv[1] == "--validate-arguments":
            MI.validate_arguments()
        elif sys.argv[1] == "--test":
            print('No tests for the scheme present')
        else:
            print('You giveth weird arguments')
    else:
        run()

    sys.exit(0)
