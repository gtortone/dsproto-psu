#!/usr/bin/env python3

import sys
import midas
import midas.frontend
import midas.event
import pyvisa
from pyvisa.constants import StopBits, Parity
from pyvisa import constants

from psudriver import PSUModel, PSUDevice, PSUFactory

class PSU(midas.frontend.EquipmentBase):

    def __init__(self, client, session, model):

        self.session = session
        self.psu = PSUFactory(PSUModel[model], session)

        equip_name = f'PSU-{model}-{str(midas.frontend.frontend_index).zfill(2)}'

        default_common = midas.frontend.InitialEquipmentCommon()
        default_common.equip_type = midas.EQ_PERIODIC
        default_common.buffer_name = "SYSTEM"
        default_common.trigger_mask = 0
        default_common.event_id = 75
        default_common.period_ms = 5000   # event data frequency update (in milliseconds) 
        default_common.read_when = midas.RO_ALWAYS
        default_common.log_history = 1  

        midas.frontend.EquipmentBase.__init__(self, client, equip_name, default_common, self.psu.getSettingsSchema());
        
        self.updateODB()

    def debug(self):
        print(f'{self.psu.brand} {self.psu.modelname}')
        print(f'OUT: {self.psu.output}')
        print("*")
        for ch in range(1, self.psu.nchannels+1):
            print(f'V{ch}: {self.psu.getVoltage(ch)}')
            print(f'VRANGE{ch}: {self.psu.getVoltageRange(ch)}')
            print(f'I{ch}: {self.psu.getCurrent(ch)}')
            print(f'ILIM{ch}: {self.psu.getCurrentLimit(ch)}')
            print("-----------------------")

    def readout_func(self):
        self.updateODB()
        event = midas.event.Event()
        V = []
        I = []
        VLIM = []
        ILIM = []
        for ch in range(1, self.psu.nchannels+1):
            try:
                V.append(self.psu.getVoltage(ch))
                I.append(self.psu.getCurrent(ch))
                VLIM.append(self.psu.getVoltageLimit(ch))
                ILIM.append(self.psu.getCurrentLimit(ch))
            except Exception as e:
                print(e)

        event.create_bank('VOLT', midas.TID_FLOAT, V)
        event.create_bank('CURR', midas.TID_FLOAT, I)
        event.create_bank('VLIM', midas.TID_FLOAT, VLIM)
        event.create_bank('ILIM', midas.TID_FLOAT, ILIM)
        event.create_bank('OUTP', midas.TID_INT32, [int(self.psu.output)])

        return event

    def updateODB(self):
        settings = self.psu.getSettingsSchema()
        for ch in range(0, self.psu.nchannels):
            try:
                settings['vset'][ch] = self.psu.getVoltageLimit(ch+1)
                settings['ilimit'][ch] = self.psu.getCurrentLimit(ch+1)
                settings['vrange'][ch] = self.psu.getVoltageRangeIndex(ch+1)
            except Exception as e:
                print(e)
        settings['output'] = self.psu.output

        if(settings != self.settings):
            for k,v in settings.items():
                if settings[k] != self.settings[k]:
                    self.client.odb_set(f'{self.odb_settings_dir}/{k}', v, remove_unspecified_keys=False)

    def detailed_settings_changed_func(self, path, idx, new_value):
        if path == f'{self.odb_settings_dir}/vset':
            self.psu.setVoltageLimit(idx+1, new_value)
        elif path == f'{self.odb_settings_dir}/ilimit':
            self.psu.setCurrentLimit(idx+1, new_value)
        elif path == f'{self.odb_settings_dir}/output':
            self.psu.output = new_value
        elif path == f'{self.odb_settings_dir}/vrange':
            if idx == -1:
                return
            self.psu.setVoltageRangeIndex(idx+1, new_value)

class PSUFrontend(midas.frontend.FrontendBase):

    def __init__(self, session, model):
        if(midas.frontend.frontend_index == -1):
            client.msg("set frontend index with -i option", is_error=True)
            sys.exit(-1)
        midas.frontend.FrontendBase.__init__(self, f"PSU-{model}")
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
    session.read_termination = '\r\n'
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

    equip_name = f'PSU-{model}-{str(midas.frontend.frontend_index).zfill(2)}'

    # check if a PSU frontend is running with same model and id
    with midas.client.MidasClient("psu") as c:

        if c.odb_exists(f"/Equipment/{equip_name}/Common/Frontend name"):
            fename = c.odb_get(f"/Equipment/{equip_name}/Common/Frontend name")

            if c.odb_get(f"/Equipment/{equip_name}"):
                for cid in c.odb_get(f'/System/Clients'):
                    if c.odb_get(f'/System/Clients/{cid}/Name') == fename:
                        c.msg(f"{equip_name} already running on MIDAS server, please change frontend index")
                        sys.exit(-1)

    fe = PSUFrontend(session, model)
    fe.run()
    
