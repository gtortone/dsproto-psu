#!/usr/bin/env python3

import sys
import midas
import midas.frontend
import pyvisa
from pyvisa.constants import StopBits, Parity
from pyvisa import constants

from psudriver import PSUModel, PSUDevice

class PSU(midas.frontend.EquipmentBase):

    def __init__(self, client, session, model):

        self.session = session
        self.psu = PSUDevice(PSUModel[model], session)

        equip_name = f'PSU{str(midas.frontend.frontend_index).zfill(2)}-{model}'

        default_common = midas.frontend.InitialEquipmentCommon()
        default_common.equip_type = midas.EQ_PERIODIC
        default_common.buffer_name = "SYSTEM"
        default_common.trigger_mask = 0
        default_common.event_id = 75
        default_common.period_ms = 2000
        default_common.read_when = midas.RO_ALWAYS
        default_common.log_history = 2      # history is enabled, data generated with period_ms frequency

        midas.frontend.EquipmentBase.__init__(self, client, equip_name, default_common);

        # FIXME
        self.psu.setVoltage(1, 2.5)
        self.psu.setCurrentLimit(1, 0.25)
        self.psu.setVoltage(2, 5.0)
        self.psu.setCurrentLimit(2, 0.50)
        self.psu.setVoltageRange(2, 'P60V')
        self.psu.output = 1

    def readout_func(self):
        print(f'{self.psu.brand} {self.psu.modelname}')
        print(f'OUT: {self.psu.output}')
        for ch in range(1, self.psu.nchannels+1):
            print(f'V{ch}: {self.psu.getVoltage(ch)}')
            print(f'VRANGE{ch}: {self.psu.getVoltageRange(ch)}')
            print(f'I{ch}: {self.psu.getCurrent(ch)}')
            print(f'ILIM{ch}: {self.psu.getCurrentLimit(ch)}')

class PSUFrontend(midas.frontend.FrontendBase):

    def __init__(self, session, model):
        if(midas.frontend.frontend_index == -1):
            client.msg("set frontend index with -i option", is_error=True)
            sys.exit(-1)
        midas.frontend.FrontendBase.__init__(self, f"PSU{str(midas.frontend.frontend_index).zfill(2)}")
        self.add_equipment(PSU(self.client, session, model))

if __name__ == "__main__":
    parser = midas.frontend.parser
    parser.add_argument("--port", default="/dev/ttyUSB0")
    parser.add_argument("--model", required=True, choices = [m.name for m in PSUModel])
    args = midas.frontend.parse_args()

    # lookup for PSU on USB port
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

    equip_name = f'PSU{str(midas.frontend.frontend_index).zfill(2)}-{model}'

    # check if a PSU frontend is running with same model and id
    client = midas.client.MidasClient("psu")

    if client.odb_exists(f"/Equipment/{equip_name}/Common/Frontend name"):
        fename = client.odb_get(f"/Equipment/{equip_name}/Common/Frontend name")

        if client.odb_get(f"/Equipment/{equip_name}"):
            for cid in client.odb_get(f'/System/Clients'):
                if client.odb_get(f'/System/Clients/{cid}/Name') == fename:
                    client.msg(f"{equip_name} already running on MIDAS server, please change frontend index")
                    sys.exit(-1)

    client.disconnect()

    fe = PSUFrontend(session, model)
    fe.run()

