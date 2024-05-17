import time
from enum import Enum

class PSUDevice:
    def __init__(self, session):
        self.session = session
        self.currch = 0
        self.postwritedelay = 0
        self.rangelist = [ 'LOW', 'HIGH' ]

    def query(self, cmd):
        res = ""
        #print(f'Q: {cmd}')
        try:
            res = self.session.query(cmd)
        except Exception as e:
            print(f'E: {e} - {res}')

        return res

    def write(self, cmd):
        #print(f'W: {cmd}')
        try:
            self.session.write(cmd)
        except Exception as e:
            print(f'E: {e} - {res}')
        # delay to avoid bus hangs on some PSU devices
        time.sleep(self.postwritedelay)     

    def init(self):
        None

    def reset(self):
        self.write("*RST")
        self.write("*CLS")

    def getVoltage(self, channel):
        self.channel = channel
        return self.voltage

    def setVoltageLimit(self, channel, value):
        self.channel = channel
        self.vset = value

    def getVoltageLimit(self, channel):
        self.channel = channel
        return self.vset

    def getCurrent(self, channel):
        self.channel = channel
        return self.current

    def setCurrentLimit(self, channel, value):
        self.channel = channel
        self.ilimit = value

    def getCurrentLimit(self, channel):
        self.channel = channel
        return self.ilimit

    def setVoltageRange(self, channel, value):
        self.channel = channel
        self.vrange = value

    def setVoltageRangeIndex(self, channel, index):
        if index in range(0, len(self.rangelist)):
            self.channel = channel
            self.vrange = self.rangelist[index]

    def getVoltageRange(self, channel):
        self.channel = channel
        return self.vrange

    def getVoltageRangeIndex(self, channel):
        return self.rangelist.index(self.getVoltageRange(channel))

    @property
    def output(self):
        return int(self.query(self.cmd["get"]["output"]))

    @output.setter
    def output(self, value):
        if value in ['ON', 'OFF'] or value in [0, 1]:
            self.write(f'{self.cmd["set"]["output"]} {value}')

    @property
    def channel(self):
        return self.currch

    @channel.setter
    def channel(self, value):
        if value != self.currch:
            if value in range(1, self.nchannels + 1):
                self.write(f'{self.cmd["set"]["channel"]} {value}')
                self.currch = value

    @property
    def voltage(self):
        return float(self.query(self.cmd["get"]["voltage"]))

    @property
    def vset(self):
        return float(self.query(self.cmd["get"]["vset"]))

    @vset.setter
    def vset(self, value):
        self.write(f'{self.cmd["set"]["vset"]} {value}')

    @property
    def current(self):
        return float(self.query(self.cmd["get"]["current"]))

    @property
    def ilimit(self):
        return float(self.query(self.cmd["get"]["ilimit"]))

    @ilimit.setter
    def ilimit(self, value):
        self.write(f'{self.cmd["set"]["ilimit"]} {value}')

    @property
    def vrange(self):
        return self.query(self.cmd["get"]["vrange"])

    @vrange.setter
    def vrange(self, value):
        if value in self.rangelist:
            self.write(f'{self.cmd["set"]["vrange"]} {value}')

    def getLastError(self):
        line = self.query(":SYST:ERR?")
        errorCode = line.split(',')[0]
        return (int(errorCode), line)

class PSUModel(Enum):
    E3649A = 'E3649A',
    E3631A = 'E3631A',            

class PSUKeysightE3649A(PSUDevice):
    def __init__(self, session):
        super().__init__(session)
        self.model = PSUModel.E3649A
        self.modelname = self.model.name
        self.brand = "Keysight"
        self.nchannels = 2
        self.rangelist = ['P35V', 'P60V']
        self.postwritedelay = 0.1

        self.settings = {
            "brand" : self.brand,
            "model": self.modelname,
            "output": False,
        }

        self.cmd = {
            "get" : {
                "channel" : "INST:NSEL?",
                "output" : "OUTPUT:STATE?",
                "voltage" : "MEAS?",
                "current" : "MEAS:CURR?",
                "vset" : "VOLT?",
                "ilimit" : "CURR?",
                "vrange" : "VOLT:RANGE?",
            },
            "set" : {
                "channel" : "INST:NSEL",
                "output" : "OUTPUT:STATE",
                "vset" : "VOLT",
                "ilimit" : "CURR",
                "vrange" : "VOLT:RANGE",
            }
        }

        self.reset()

    def debug(self):
        print(f'{self.brand} {self.modelname}')
        print(f'OUT: {self.output}')
        print("*")
        for ch in range(1, self.nchannels+1):
            print(f'V{ch}: {self.getVoltage(ch)}')
            print(f'I{ch}: {self.getCurrent(ch)}')
            print(f'VRANGE{ch}: {self.getVoltageRange(ch)}')
            print(f'ILIM{ch}: {self.getCurrentLimit(ch)}')
            print("-----------------------")

    def getSettingsSchema(self):
        self.settings["vset"] = [0.0] * self.nchannels
        self.settings["ilimit"] = [0.0] * self.nchannels
        self.settings["vrange"] = [0] * self.nchannels
        return self.settings

class PSUAgilentE3631A(PSUDevice):
    def __init__(self, session):
        super().__init__(session)
        self.model = PSUModel.E3631A
        self.modelname = self.model.name
        self.brand = "Agilent"
        self.nchannels = 3
        self.postwritedelay = 0.1

        self.settings = {
            "brand" : self.brand,
            "model": self.modelname,
            "output": False,
        }

        self.cmd = {
            "init" : "SYST:REM",
            "get" : {
                "channel" : "INST:NSEL?",
                "output" : "OUTPUT:STATE?",
                "voltage" : "MEAS?",
                "current" : "MEAS:CURR?",
                "vset" : "VOLT?",
                "ilimit" : "CURR?",
            },
            "set" : {
                "channel" : "INST:NSEL",
                "output" : "OUTPUT:STATE",
                "vset" : "VOLT",
                "ilimit" : "CURR",
            }
        }

        self.reset()
        self.init()

    def init(self):
        self.write(f'{self.cmd["init"]}') 

    def reset(self):
        super().reset()
        # reset and channel switching requires a delay of 500 ms
        time.sleep(0.5)

    def getLastError(self):
        time.sleep(0.5)
        return super().getLastError()

    def debug(self):
        print(f'{self.brand} {self.modelname}')
        print(f'OUT: {self.output}')
        print("*")
        for ch in range(1, self.nchannels+1):
            print(f'V{ch}: {self.getVoltage(ch)}')
            print(f'I{ch}: {self.getCurrent(ch)}')
            print(f'ILIM{ch}: {self.getCurrentLimit(ch)}')
            print("-----------------------")

    def getSettingsSchema(self):
        self.settings["vset"] = [0.0] * self.nchannels
        self.settings["ilimit"] = [0.0] * self.nchannels
        return self.settings

    @PSUDevice.channel.setter
    def channel(self, value):
        if value != self.currch:
            if value in range(1, self.nchannels + 1):
                self.write(f'{self.cmd["set"]["channel"]} {value}')
                self.currch = value
            # channel switching requires a delay of 500 ms
            time.sleep(0.5)                 

def PSUFactory(model, session):
    if not isinstance(model, PSUModel):
        raise TypeError
    if model == PSUModel.E3649A:
        return PSUKeysightE3649A(session)
    elif model == PSUModel.E3631A:
        return PSUAgilentE3631A(session)
        
