"""
Written by Aplura, LLC
Copyright (C) 2016-2020 Aplura, ,LLC

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""
from __future__ import absolute_import
import sys
import os.path

if sys.version_info >= (3, 0):
    base_location = sys.path[0].split(os.path.sep)
    base_location.pop(-1)
    base_location.append(os.path.sep.join(["lib", "python3.7", "site-packages"]))
    sys.path.pop(0)
    sys.path.insert(0, os.path.sep.join(base_location))

import itertools
import json
import logging
import os
import os.path
import string
import sys
import time
import uuid
import xml.sax.saxutils
from datetime import timedelta, datetime

from Utilities import KennyLoggins
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

from defusedxml.minidom import parseString


# Add Additional Imports Here
class Unbuffered:
    def __init__(self, stream):
        self.stream = stream

    def write(self, data):
        self.stream.write(data)
        self.stream.flush()

    def __getattr__(self, attr):
        return getattr(self.stream, attr)


class ModularInput:
    """ Base Class for splunk Modular Input """
    """ These are the basic Variables used through out the class """
    _SPLUNK_HOME = os.getenv("SPLUNK_HOME")
    _should_print_debug = False
    _service_checkpoints = {}
    _log_level = logging.INFO
    log = None
    _config = {}
    _scheme = {}
    _required_schema_arguments = []
    _loaded_checkpoints = {}
    _default_checkpoint_lookback_minutes = 60

    # Properties
    @property
    def scheme_title(self):
        return self._scheme["title"]

    @property
    def scheme_description(self):
        return self._scheme["description"]

    @property
    def scheme_args(self):
        return self._scheme["args"]

    @property
    def cim_model(self):
        return self.__cim_model

    @cim_model.setter
    def cim_model(self, x):
        self.__cim_model = x

    @property
    def _use_cim(self):
        return self.__use_cim

    @_use_cim.setter
    def _use_cim(self, x):
        self.__use_cim = x

    @property
    def _splunk_home(self):
        return self.__splunk_home

    @_splunk_home.setter
    def _splunk_home(self, s):
        self.__splunk_home = s

    @property
    def _app_name(self):
        return self.__app_name

    @_app_name.setter
    def _app_name(self, s):
        self.__app_name = s

    @property
    def _app_home(self):
        return self.__app_home

    @_app_home.setter
    def _app_home(self, s):
        self.__app_home = s

    # Begin Methods
    def __init__(self, app_name=None, scheme={}, cim_fields=None):
        try:
            self.__splunk_home = None
            if app_name is None:
                raise Exception("App Name not passed to Modular Input")
            self._app_name = app_name
            self._use_cim = False
            self._setup_logging()
            self.log.debug("Splunk App Name set: {}".format(self._app_name))
            self.source(app_name)
            self.sourcetype(app_name)
            self.host(app_name)
            if self._splunk_home is None:
                self._splunk_home = make_splunkhome_path([""])
            if self._splunk_home is None:
                raise Exception("SPLUNK HOME UNABLE TO BE SET")
            self.log.debug("Splunk Home set: {}".format(self._splunk_home))
            self._app_home = os.path.join(self._splunk_home, "etc", "apps", self._app_name)

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            myJson = "message=\"{}\" exception_type=\"{}\" exception_arguments=\"{}\" filename=\"{}\" line=\"{}\" input=\"{}\"".format(
                str(e), type(e).__name__, e, fname, exc_tb.tb_lineno, self.get_config("name"))
            self.log.error(myJson)
            raise e
        self.log.debug("Starting MI __init__ : app_name={} scheme={} ".format(app_name, scheme))
        self.log.debug("Splunk Home set: {}".format(self._app_home))
        self.log.debug("Building Scheme: {}".format(scheme))
        self._build_scheme(scheme=scheme)
        if cim_fields is not None:
            self._use_cim = True
            self.cim_model = cim_fields

        sys.stdout = Unbuffered(sys.stdout)

    def set_logger(self, log):
        self.log = log

    def _setup_logging(self, ll=logging.INFO):
        kl = KennyLoggins()
        self.log = kl.get_logger(self._app_name, "modularinput", ll)

    def _apply_cim(self, event):
        for cm in self.cim_model:
            try:
                event[cm] = self.cim_model[cm]
            except:
                pass
        return event

    class Unbuffered:
        def __init__(self, stream):
            self.stream = stream

        def write(self, data):
            self.stream.write(data)
            self.stream.flush()

        def __getattr__(self, attr):
            return getattr(self.stream, attr)

    def _build_scheme(self, scheme={}):
        """ Let's build a scheme for the modular input.
        Keyword arguments:
        scheme -- the schema object that will configure the input.
        { "title" : "my title", "description": " my description" }
        """
        tmp = "{}{}{}{}".format("<scheme><title>{}</title>".format(scheme["title"]),
                                "<description>{}</description>".format(scheme["description"]),
                                "<use_external_validation>true</use_external_validation>",
                                "<streaming_mode>xml</streaming_mode><endpoint><args>")
        self._scheme = scheme
        for arg in scheme["args"]:
            if "required" in arg:
                # Update for NET-27
                if arg["required"]:
                    self._required_schema_arguments.append(arg["name"])
                self._required_schema_arguments.append(arg["name"])
            tmp = "{}<arg name=\"{}\"><title>{}</title><description>{}</description></arg>".format(
                tmp, arg["name"], arg["title"], arg["description"])
        tmp = "{}</args></endpoint></scheme>".format(tmp)
        self.log.debug("Built A Scheme: {}".format(tmp))
        self.scheme(tmp)

    def _print(self, s):
        print("{}".format(s))

    BASE62 = "{}{}{}".format(string.digits, string.ascii_lowercase, string.ascii_uppercase)
    BASE72 = "{}!@#$%^&*()".format(BASE62)
    PRINTABLE = string.printable

    # Use this with Integer tracking IDs
    def base_encode(self, range, alphabet=BASE62):
        return [self._base_encode(x, alphabet) for x in range]

    def base_decode(self, range, alphabet=BASE62):
        return [self._base_decode(x, alphabet) for x in range]

    def _base_encode(self, num, alphabet=BASE62):
        """Encode a positive number in Base X

        Arguments:
        - `num`: The number to encode
        - `alphabet`: The alphabet to use for encoding
        """
        self.log.info("action=_base_encode num={} alphabet={} type={}".format(num, alphabet, type(num)))
        if not self.is_number(num):
            return "::STR::{}".format(num)
        else:
            if num == 0:
                return alphabet[0]
            arr = []
            base = len(alphabet)
            while num:
                num, rem = divmod(num, base)
                arr.append(alphabet[rem])
            arr.reverse()
            return ''.join(arr)

    def is_number(self, s):
        try:
            int(s)
            return True
        except ValueError:
            return False

    def _base_decode(self, sstring, alphabet=BASE62):
        """Decode a Base X encoded string into the number

        Arguments:
        - `string`: The encoded string
        - `alphabet`: The alphabet to use for encoding
        """
        self.log.info("action=_base_decode num={} alphabet={}".format(sstring, alphabet))
        if sstring.startswith("::STR::"):
            return sstring
        base = len(alphabet)
        strlen = len(sstring)
        num = 0

        idx = 0
        for char in sstring:
            power = (strlen - (idx + 1))
            num += alphabet.index(char) * (base ** power)
            idx += 1

        return num

    def compress_ranges(self, i):
        c = []
        i = list(set(i))
        i.sort(key=int)
        for a, b in itertools.groupby(enumerate(i), lambda x, y: y - x):
            b = list(b)
            c.append((b[0][1], b[-1][1]))
        return c

    def decompress_ranges(self, i):
        c = []
        for tup in i:
            mini, maxi = tup
            c = itertools.chain(c, range(mini, int(maxi) + 1))
        return [x for x in c]

    def _escape(self, s):
        return xml.sax.saxutils.escape("{}".format(s))

    def _require_configuration(self, config, key):
        if key not in config:
            raise Exception("Invalid configuration received from Splunk: key '{}' is missing.".format(key))

    def _print_debug(self, s):
        myStr = "app={} source={} sourcetype={} host={} {}".format(
            self._app_name, self.source(), self.sourcetype(), self.host(), s)
        self.log.debug(myStr)

    def debug(self, s):
        self._print_debug(s)

    def info(self, s):
        self._print_info(s)

    def _print_info(self, s):
        myStr = "app={} source={} sourcetype={} host={} {}".format(
            self._app_name, self.source(), self.sourcetype(), self.host(), s)
        self.log.info(myStr)

    def _catch_error(self, e, **kwargs):
        myJson = {"timestamp": self.gen_date_string(), "log_level": "ERROR"}
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        myJson["errors"] = [{"msg": str((e)),
                             "exception_type": "{}".format(type(e)).__name__,
                             "exception_arguments": "{}".format(e),
                             "filename": fname,
                             "line": exc_tb.tb_lineno,
                             "input_name": self.get_config("name")
                             }]
        if "severity" in kwargs:
            myJson["errors"][0]["severity"] = kwargs["severity"]
        oldst = self.sourcetype()
        self.sourcetype("{}:error".format(self._app_name))
        self.print_error("{}".format(json.dumps(myJson)))
        self.print_event("{}".format((json.dumps(myJson))))
        self.sourcetype(oldst)

    def catch_error(self, e, **kwargs):
        self._catch_error(e, **kwargs)

    def do_info(self, s={}):
        oldst = self.sourcetype()
        self.sourcetype("{}:info".format(self._app_name))
        self.print_error("{}".format(json.dumps(s)))
        self.print_event("{}".format((json.dumps(s))))
        self.sourcetype(oldst)

    def _checkpoint(self, key, value=False, checkpoint_time=None, is_object=False):
        chkpointfile = os.path.join(self._config["checkpoint_dir"], "{}_{}".format(self.host(), key))
        if not value:
            chk_time = 0
            self._loaded_checkpoints[key] = (datetime.utcnow() - datetime.utcfromtimestamp(0)).total_seconds()
            self.debug("set checkpoint load time to: {}".format(self._loaded_checkpoints[key]))
            try:
                if os.path.isfile(chkpointfile):
                    self.debug("File Exists: {}".format(chkpointfile))
                    chk_time = self._read_file(chkpointfile)
                    self.debug("found a value in the file for {} : {}".format(key, chk_time))
                    if not is_object:
                        chk_time = float(chk_time)
                    else:
                        chk_time = json.loads(chk_time)
                else:
                    # assume that this means the checkpoint is not there
                    # Let's Default to 60 minutes ago. Just to start pulling data.
                    # TODO: Make loading a checkpoint configurable in respect to the look back time (in minutes)
                    self.debug("Setting Checkpoint {} default time".format(key))
                    wibbly_wobbly_timey_wimey = datetime.utcnow() - timedelta(
                        minutes=self.checkpoint_default_lookback())
                    chk_time = (wibbly_wobbly_timey_wimey - datetime.utcfromtimestamp(0)).total_seconds()
                    chk_time = float(chk_time)
                    if is_object:
                        chk_time = {}
            except Exception as e:
                self._catch_error(e)
            self.debug("Returning CheckPoint Time {}".format(chk_time))
            return chk_time
        else:
            try:
                # So to avoid "long runs" and "time lapse" in checkpointing,
                # if no time is passed, use the time the checkpoint was loaded.
                # if "now" is passed, use "now". Can I haz tautology?
                # First identified in ASA-3
                chk_time = checkpoint_time
                if chk_time is None:
                    chk_time = self._loaded_checkpoints[key]
                if chk_time is "now":
                    chk_time = (datetime.utcnow() - datetime.utcfromtimestamp(0)).total_seconds()
                if is_object:
                    chk_time = json.dumps(chk_time)
                self._write_file(chkpointfile, "{}".format(chk_time))
                return True
            except Exception as e:
                self._catch_error(e)
                return False

    # read XML configuration passed from splunkd
    def _get_config(self):
        self.log.debug("Starting _get_config")
        config = {}
        try:
            # read everything from stdin
            config_str = sys.stdin.read()
            self.log.debug("Found a configuration string: {}".format(config_str))
            # parse the config XML
            doc = parseString(config_str)
            root = doc.documentElement
            chkpointdir = root.getElementsByTagName("checkpoint_dir")[0].firstChild.data
            config["checkpoint_dir"] = chkpointdir
            sessionkey = root.getElementsByTagName("session_key")[0].firstChild.data
            config["session_key"] = sessionkey
            self.log.debug("XML: found checkpoint_dir: {}".format(chkpointdir))
            conf_node = root.getElementsByTagName("configuration")[0]
            if conf_node:
                self.log.debug("XML: found configuration")
                self.log.debug("{}".format(conf_node))
                stanza = conf_node.getElementsByTagName("stanza")[0]
                if stanza:
                    stanza_name = stanza.getAttribute("name")
                    if stanza_name:
                        self.log.debug("XML: found stanza " + stanza_name)
                        config["name"] = stanza_name
                        params = stanza.getElementsByTagName("param")
                        for param in params:
                            param_name = param.getAttribute("name")
                            self.log.debug("XML: found param '{}'".format(param_name))
                            if param_name and param.firstChild and \
                                    param.firstChild.nodeType == param.firstChild.TEXT_NODE:
                                data = param.firstChild.data
                                config[param_name] = data
                                self.log.debug("XML: '{}' -> '{}'".format(param_name, data))
            for arg in self._required_schema_arguments:
                self._require_configuration(config, arg)
            if not config:
                self.print_error("Invalid Configuration received from Splunk.")
                raise Exception("Invalid configuration received from Splunk.")

                # just some validation: make sure these keys are present (required)
        except Exception as e:
            raise Exception("Error getting Splunk configuration via STDIN: {}".format(str(e)))
        return config

    def _get_validation_data(self):
        val_data = {}
        # read everything from stdin
        val_str = sys.stdin.read()
        # parse the validation XML
        doc = parseString(val_str)
        root = doc.documentElement
        self.log.debug("XML: found items")
        try:
            item_node = root.getElementsByTagName("item")[0]
        except:
            item_node = root.getElementsByTagName("configuration")[0]
        if item_node:
            self.log.debug("XML: found item")
            name = item_node.getAttribute("name")
            val_data["stanza"] = name
            params_node = item_node.getElementsByTagName("param")
            for param in params_node:
                name = param.getAttribute("name")
                self.log.debug("Found param {}".format(name))
                if name and param.firstChild and \
                        param.firstChild.nodeType == param.firstChild.TEXT_NODE:
                    val_data[name] = param.firstChild.data
        return val_data

    def _multiple_events(self, events, time_field="timestamp"):
        self.log.debug("Got this event object: {0}".format(len(events)))
        for evt in events:
            self.print_event(json.dumps(evt), time_field=time_field)
            self.log.debug("printed a multi event event")

    def _validate_arguments(self, val_data):
        """
        :param val_data: The data that requires validation.
        :return: perform logic to validate the passed data custom to your environment.
        """
        return True

    """ PUBLIC FUNCTIONS """

    def start(self):
        self.run()
        self.init_stream()

    def stop(self):
        self.print_done_event()
        self.end_stream()

    def run(self):
        self.log.debug("Building Config")
        self._config = self._get_config()
        self._config["tracking_uuid"] = self.guid()
        self.log.debug("Config Built: {}".format(self._config))

    def scheme(self, scheme=False):
        if scheme:
            self.log.debug("Setting Scheme: {}".format(scheme))
            self._SCHEME = scheme
        else:
            self._print(self._SCHEME)
        return self._SCHEME

    def checkpoint_default_lookback(self, new_time=None):
        if new_time is not None:
            self._default_checkpoint_lookback_minutes = new_time
        return self._default_checkpoint_lookback_minutes

    def sourcetype(self, sourcetype=False):
        if sourcetype:
            self._SOURCETYPE = sourcetype
        return self._SOURCETYPE

    def source(self, source=False):
        if source:
            self._SOURCE = source
        return self._SOURCE

    def host(self, host=False):
        if host:
            self._HOST = host
        return self._HOST

    def _get_checkpointfile(self, key):
        return os.path.join(self._config["checkpoint_dir"], "{0}_{1}".format(self.host(), key))

    def _get_checkpoint(self, key):
        """
        Internal Function to get the checkpoint. Disassociate all this stuff.
        :param key:
        :return:
        """
        chkpointfile = self._get_checkpointfile(key)
        chk_time = 0
        self._loaded_checkpoints[key] = (datetime.utcnow() - datetime.utcfromtimestamp(0)).total_seconds()
        self.debug("set checkpoint load time to: {}".format(self._loaded_checkpoints[key]))
        try:
            if os.path.isfile(chkpointfile):
                self.debug("File Exists: {}".format(chkpointfile))
                chk_time = self._read_file(chkpointfile)
                self.debug("found a value in the file for {} : {}".format(key, chk_time))

                if isinstance(type(chk_time), float) or isinstance(type(chk_time), int):
                    chk_time = float(chk_time)
                else:
                    chk_time = json.loads(chk_time)
            else:
                # assume that this means the checkpoint is not there
                # We will not auto-create one. It is not up to the getter to create a checkpoint. Return none,
                # have MI do the check.
                return None
        except Exception as e:
            self._catch_error(e)
        self.debug("Returning CheckPoint {}".format(chk_time))
        return chk_time

    def get_checkpoint(self, key, isObject=False):
        return self._checkpoint(key, value=False, is_object=isObject)

    def _set_checkpoint(self, key, object=None):
        try:
            # So to avoid "long runs" and "time lapse" in checkpointing,
            # if no time is passed, use the time the checkpoint was loaded.
            # if "now" is passed, use "now". Can I haz tautology?
            # First identified in ASA-3
            chkpointfile = self._get_checkpointfile(key)
            checkpoint = object
            if checkpoint is None:
                checkpoint = self._loaded_checkpoints[key]
            if checkpoint is "now":
                checkpoint = (datetime.utcnow() - datetime.utcfromtimestamp(0)).total_seconds()
            if not isinstance(object, int) and not isinstance(object, float):
                checkpoint = json.dumps(checkpoint)
            self._write_file(chkpointfile, "{}".format(checkpoint))
            return True
        except Exception as e:
            self._catch_error(e)
            return False

    def _write_file(self, filename, file_contents):
        try:
            f = open(filename, "w+")
            f.write(file_contents)
        except Exception as e:
            self._catch_error(e)
        finally:
            f.close()

    def _read_file(self, filename):
        try:
            f = open(filename, "r")
            return "{}".format(f.read().strip())
        except Exception as e:
            self._catch_error(e)
        finally:
            f.close()

    def set_checkpoint(self, key, checkpoint_time=None, isObject=False):
        """

        :param key: The key to use when storing the checkpoint.
        :param checkpoint_time: The time to use. If not sent, will default to the time the checkpoint was loaded.
        :param isObject: IS the checkpoint item an object?
        :return: The Time that was saved.
        """
        return self._checkpoint(key, value=True, checkpoint_time=checkpoint_time, is_object=isObject)

    def get_config(self, key=None):
        if key is None:
            return self._config
        return self._config.get(key, None)

    def config(self, key=None):
        return self.get_config(key)

    def init_stream(self):
        self._print("<stream>")
        self.log.debug("printed start of stream")

    def end_stream(self):
        self._print("</stream>")
        self.log.debug("printed end of stream")

    # TODO: Add an argument that is a function that will transform the data prior to output in the XML Stream
    def print_event(self, event_data, time_field="timestamp", explicit_time=None):
        if len(event_data) < 1:
            event_data = ""
        _isJson = False
        try:
            event_data = json.loads(event_data)
            self.log.debug("successful parse of JSON data: Is Dict: {}".format(isinstance(event_data, dict)))
            _isJson = True
        except ValueError as e:
            pass
        my_time = None
        if isinstance(event_data, dict) or _isJson:
            if time_field not in event_data and "timestamp" not in event_data:
                event_data["timestamp"] = self.gen_date_string()
                self.log.debug("setting timestamp to generated time: {}".format(event_data["timestamp"]))
            elif time_field in event_data and "timestamp" not in event_data:
                event_data["timestamp"] = event_data[time_field]
                self.log.debug("setting timestamp to time_field {} time: {}".format(event_data[time_field],
                                                                                    event_data["timestamp"]))
            else:
                self.log.debug("unknown condition: time_field {} ".format(event_data[time_field]))
            event_data["modular_input_consumption_time"] = self.gen_date_string()
            my_time = event_data["timestamp"]
            event_data = json.dumps(event_data)
        if explicit_time is not None:
            my_time = explicit_time
        explicit_time_tag = ""
        if my_time is not None and (isinstance(my_time, float) or isinstance(my_time, int)):
            explicit_time_tag = "<time>{}</time>".format(my_time)
        # escape didn't work. Updated to self reference to _escape ASA-22
        explicit_time_tag = ""
        eventxml = "<event>{}<data><![CDATA[{}]]></data><sourcetype>{}</sourcetype><source>{}</source><host>{}</host><done /></event>\n".format(
            explicit_time_tag, self._escape(event_data), self._escape(self.sourcetype()), self._escape(self.source()),
            self._escape(self.host()))
        self._print(eventxml)
        self.log.debug("printed an event")

    def print_multiple_events(self, event_data, time_field="timestamp"):
        self._multiple_events(event_data, time_field=time_field)

    def print_done_event(self):
        eventxml = "<event><data></data><sourcetype>{}</sourcetype><source>{}</source><host>{}</host><done/></event>\n".format(
            self._escape(self.sourcetype()), self._escape(self.source()), self._escape(self.host()))
        self._print(eventxml)
        self.log.debug("printed a done event")

    def print_error(self, s):
        tmp = self.sourcetype()
        self.sourcetype("{}:error".format(self._app_name))
        self.log.error("host={} sourcetype={} source={} {}".format(self.host(), self.sourcetype(), self.source(), s))
        self._print("<error><message>{}</message></error>".format(self._escape(s)))
        self.print_event("{}".format(s))
        self.sourcetype(tmp)

    def gen_date_string(self):
        st = time.localtime()
        tm = time.mktime(st)
        return time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime(tm))

    def guid(self):
        return "{}".format(uuid.uuid4())

    def validate_arguments(self):
        val_data = self._get_validation_data()
        try:
            self._validate_arguments(val_data)
        except Exception as e:
            self.print_error("Invalid configuration specified: {}".format(str(e)))
            sys.exit(1)
