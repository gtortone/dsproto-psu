#!/usr/bin/env python3

import sys
import midas
import midas.frontend
import midas.event
from pyvisa import ResourceManager, constants

from psudriver import PSUModel, PSUDevice, PSUFactory
from utils import flatten_dict

class PSU(midas.frontend.EquipmentBase):

    def __init__(self, client, model):
        
        default_common = midas.frontend.InitialEquipmentCommon()
        default_common.equip_type = midas.EQ_PERIODIC
        default_common.buffer_name = "SYSTEM"
        default_common.trigger_mask = 0
        default_common.event_id = 75
        default_common.period_ms = 5000   # event data frequency update (in milliseconds) 
        default_common.read_when = midas.RO_ALWAYS
        default_common.log_history = 1  

        equip_name = f'PSU-{model}-{str(midas.frontend.frontend_index).zfill(2)}'
        self.psu = PSUFactory(PSUModel[model])

        midas.frontend.EquipmentBase.__init__(self, client, equip_name, default_common, self.psu.getSettingsSchema());

        port = self.settings['port']

        if port == "":
            self.client.msg(f"please set port device to /Equipment/{equip_name}/Settings/port", is_error=True)
            self.client.communicate(1000)
            sys.exit(-1)

        # lookup for PSU on USB port
        rm = ResourceManager()
        dev = f'ASRL{port}::INSTR'

        self.session = None
        try:
            self.session = rm.open_resource(dev, baud_rate = 9600, data_bits = 7, parity = constants.Parity.even, 
                        flow_control = constants.VI_ASRL_FLOW_NONE, stop_bits = constants.StopBits.two)
        except Exception as e:
            self.client.communicate(1000)
            self.client.msg(f"{e}", is_error=True)
            sys.exit(-1)

        self.session.read_termination = '\r\n'
        self.session.write_termination = '\n'

        readmodel = None
        try:
            readmodel = self.session.query('*CLS; *IDN?').split(',')[1]
        except Exception as e:
            self.client.msg(f"No device found on {port}", is_error=True)
            self.client.communicate(1000)
            sys.exit(-1)

        if model == readmodel: 
            self.client.msg(f"PSU {model} found on {port}")
        else:
            self.client.msg(f"PSU {model} not found on {port}", is_error=True)
            self.client.communicate(1000)
            sys.exit(-1)

        self.psu.setSession(self.session)
        self.psu.reset()
        self.psu.init()

        self.updateODB()

    def debug(self):
        self.psu.debug()

    def readout_func(self):
        #self.debug()
        #self.updateODB()
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
                if('vrange' in settings):
                    settings['vrange'][ch] = self.psu.getVoltageRangeIndex(ch+1)
            except Exception as e:
                print(e)
        settings['output'] = self.psu.output
        settings['port'] = self.settings['port']

        if(settings != self.settings):
            local_settings = flatten_dict(settings)
            odb_settings = flatten_dict(self.settings)
            for k,v in local_settings.items():
                if k == 'name':
                    continue
                if local_settings[k] != odb_settings[k]:
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

        error = self.psu.getLastError()
        if error[0] != 0:
            self.client.msg(error[1], is_error=True)

class PSUFrontend(midas.frontend.FrontendBase):

    def __init__(self, model):
        if(midas.frontend.frontend_index == -1):
            print("set frontend index with -i option")
            sys.exit(-1)

        midas.frontend.FrontendBase.__init__(self, f"PSU-{model}-{str(midas.frontend.frontend_index).zfill(2)}")
        self.add_equipment(PSU(self.client, model))

if __name__ == "__main__":
    parser = midas.frontend.parser
    parser.add_argument("--model", required=True, choices = [m.value[0] for m in PSUModel])
    args = midas.frontend.parse_args()

    equip_name = f'PSU-{args.model}-{str(midas.frontend.frontend_index).zfill(2)}'

    # check if a PSU frontend is running with same model and id
    with midas.client.MidasClient("psu") as c:

        if c.odb_exists(f"/Equipment/{equip_name}/Common/Frontend name"):
            fename = c.odb_get(f"/Equipment/{equip_name}/Common/Frontend name")

            clients = c.odb_get(f'/System/Clients', recurse_dir=False)
            for cid in clients:
                client_name = ""
                try:
                    client_name = c.odb_get(f'/System/Clients/{cid}/Name')
                except Exception as e:
                    continue

                if client_name == fename:
                    c.msg(f"{equip_name} already running on MIDAS server, please change frontend index")
                    sys.exit(-1)

        c.odb_delete("/Programs/psu")

    fe = PSUFrontend(args.model)
    fe.run()
    
