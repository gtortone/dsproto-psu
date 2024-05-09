#!/usr/bin/env python3

import sys
import midas
import midas.frontend
import pyvisa
from pyvisa.constants import StopBits, Parity
from pyvisa import constants

class PSU(midas.frontend.EquipmentBase):

    def __init__(self, client, session, model):

        self.session = session
        self.model = model

        if(midas.frontend.frontend_index == -1):
            client.msg("set frontend index with -i option", is_error=True)
            sys.exit(-1)

        equip_name = f'PSU-{model}-{str(midas.frontend.frontend_index).zfill(2)}'

        default_common = midas.frontend.InitialEquipmentCommon()
        default_common.equip_type = midas.EQ_PERIODIC
        default_common.buffer_name = "SYSTEM"
        default_common.trigger_mask = 0
        default_common.event_id = 3
        default_common.period_ms = 2000
        default_common.read_when = midas.RO_ALWAYS
        default_common.log_history = 2      # history is enabled, data generated with period_ms frequency

        midas.frontend.EquipmentBase.__init__(self, client, equip_name, default_common);

    def readout_func(self):
        None

class PSUFrontend(midas.frontend.FrontendBase):

    def __init__(self, session, model):
        midas.frontend.FrontendBase.__init__(self, "PSU")
        self.add_equipment(PSU(self.client, session, model))

if __name__ == "__main__":
    parser = midas.frontend.parser
    parser.add_argument("--port", default="/dev/ttyUSB0")
    parser.add_argument("--model", required=True, choices = ['E3649A', 'E3631A'])
    args = midas.frontend.parse_args()

    rm = pyvisa.ResourceManager()
    dev = f'ASRL{args.port}::INSTR'
    session = rm.open_resource(dev, baud_rate = 9600, data_bits = 7, parity = Parity.even, 
                flow_control = constants.VI_ASRL_FLOW_NONE, stop_bits = StopBits.two)
    session.read_termination = '\n'
    session.write_termination = '\n'

    try:
        model = session.query('*IDN?').split(',')[1]
    except Exception as e:
        print(f"E: {e}")
        sys.exit(-1)

    if model == args.model: 
        print(f"I: PSU {model} found on {args.port}")
    else:
        print(f"E: PSU {args.model} not found on {args.port}")
        sys.exit(-1)

    fe = PSUFrontend(session, model)
    fe.run()

