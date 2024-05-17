#!/usr/bin/env python3

import time
import warnings
warnings.simplefilter('ignore')

from pyvisa import ResourceManager, constants

class PSU:
    def __init__(self, session):
        self.session = session
        self.session.write("*RST")
        self.session.write("*CLS")
        time.sleep(1)

    def idn(self):
        return self.session.query('*IDN?')


pslist = []
rm = ResourceManager()

for resource in rm.list_resources():
    if rm.resource_info(resource).interface_type == constants.InterfaceType.asrl:
        print("OK")
        session = rm.open_resource(resource, baud_rate = 9600, data_bits = 7, parity = constants.Parity.even,
                flow_control = constants.VI_ASRL_FLOW_NONE, stop_bits = constants.StopBits.two)
        session.read_termination = '\r\n'
        session.write_termination = '\n'

        pslist.append(PSU(session))

for psu in pslist:
    print(psu.idn())
