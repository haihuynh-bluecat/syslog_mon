# Copyright 2019 BlueCat Networks (USA) Inc. and its affiliates
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
# http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
from functools import partial
from multiprocessing import Pool
from pysnmp.hlapi import *
from config import *
from map_protocol import (
    AUTH_PROTOCOL,
    PRIV_PROTOCOL
)
from snmp_password_process import (
    decrypt_password
)
import json
from Config.map_oid import (
    MAP_OID
)
basedir = os.path.dirname(__file__)
sys.path.append(basedir)
from common import get_engine_id


def empty_to_none(value):
    if value.strip() == "" or value is None:
        return None
    return value


def get_udp_transport_target(transport_target, port):
    """
    "   Check and return UdpTransportTarget conform ipv4 or ipv6
    """
    if ":" in transport_target:
        return Udp6TransportTarget((transport_target, port))
    else:
        return UdpTransportTarget((transport_target, port))


def send_trap(cond, level, keypair, msg, err_type, host, destination):
    engine_id = str(get_engine_id())
    try:
        errorIndication, errorStatus, errorIndex, varBinds = next(
            sendNotification(
                SnmpEngine(OctetString(hexValue=engine_id)),
                UsmUserData(destination["userName"],
                            authKey=empty_to_none(decrypt_password(destination['authKey'])),
                            privKey=empty_to_none(decrypt_password(destination['privKey'])),
                            authProtocol=AUTH_PROTOCOL[empty_to_none(destination['authProtocol'])],
                            privProtocol=PRIV_PROTOCOL[empty_to_none(destination['privProtocol'])]),
                get_udp_transport_target(destination["transportTarget"], destination["port"]),
                ContextData(),
                'trap',
                NotificationType(
                    ObjectIdentity(MAP_OID[err_type]["OID"])
                ).addVarBinds(
                    (MAP_OID[err_type]["bcnSyslogMonAlarmCond"], OctetString(cond)),
                    (MAP_OID[err_type]["bcnSyslogMonAlarmSeverity"], Integer(level)),
                    (MAP_OID[err_type]["bcnSyslogMonKeyPair"], OctetString(keypair)),
                    (MAP_OID[err_type]["bcnSyslogMonHostInfo"], OctetString(host)),
                    (MAP_OID[err_type]["bcnSyslogMonAlarmMsg"], OctetString(msg))
                )
            )
        )
    except KeyError as key_error:
        logger.error(
            "Send_trap:Not found {0}".format(key_error)
        )
    except Exception as ex:
        logger.error(
            "Send_trap:{0}".format(ex)
        )

    if errorIndication:
        logger.error(
            "Send_trap:{0}".format(errorIndication)
        )



if __name__ == '__main__':
    cond = sys.argv[1]
    level = sys.argv[2]
    keypair = sys.argv[3]
    message = ' '.join(string for string in sys.argv[4])
    err_type = sys.argv[5]
    host = sys.argv[6]
    pool = Pool(processes=5)
    sendTrapFunc = partial(send_trap, cond, level, keypair, message, err_type, host)
    basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
    with open(basedir + '/Config/snmp_config.json') as f:
        DESTINATIONS = json.load(f)
    pool.map(sendTrapFunc, DESTINATIONS)
    pool.close()

