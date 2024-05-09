from enum import Enum
from pyvisa.constants import StopBits, Parity
from pyvisa import constants

class PSUModel(Enum):
    E3649A = 'E3649A',
    E3631A = 'E3631A',            

class PSUDevice:

    def __init__(self, model: PSUModel, session):
        if not isinstance(model, PSUModel):
            raise TypeError

        self.model = model
        self.session = session
        self.modelname = self.model.name

        if model == PSUModel.E3649A:
            self.brand = 'Keysight'
            self.nchannels = 2
            self.rangelist = ['P35V', 'P60V']
        elif model == PSUModel.E3631A:
            self.brand = 'Agilent'
            self.nchannels = 3
            self.rangelist = ['P6V', 'P25V', 'N25V']

        self.settings = {
            "brand" : self.brand,
            "model": self.modelname,
            "output": False,
        }

    def getSettingsSchema(self):
        self.settings["vset"] = [0.0] * self.nchannels
        self.settings["ilimit"] = [0.0] * self.nchannels
        return self.settings

    def getVoltage(self, channel):
        self.channel = channel
        return self.voltage

    def setVoltage(self, channel, value):
        self.channel = channel
        self.vset = value

    def getCurrent(self, channel):
        self.channel = channel
        return self.current

    def setCurrentLimit(self, channel, value):
        self.channel = channel
        self.ilimit = value

    def getCurrentLimit(self, channel):
        return self.ilimit

    def setVoltageRange(self, channel, value):
        self.channel = channel
        self.vrange = value

    def getVoltageRange(self, channel):
        self.channel = channel
        return self.vrange

    @property
    def output(self):
        return int(self.session.query('OUTPUT:STATE?'))

    @output.setter
    def output(self, value):
        if value in ['ON', 'OFF'] or value in [0, 1]:
            self.session.write(f'OUTPUT:STATE {value}')

    @property
    def channel(self):
        s = self.session.query('INST:NSEL?')
        return int(s[-1])

    @channel.setter
    def channel(self, value):
        if value in range(1, self.nchannels + 1):
            self.session.write(f'INST:NSEL {value}')

    @property
    def voltage(self):
        return float(self.session.query('MEAS?'))

    @property
    def vset(self):
        return float(self.session.query('VOLT?'))

    @vset.setter
    def vset(self, value):
        self.session.write(f'VOLT {value}')

    @property
    def current(self):
        return float(self.session.query('MEAS:CURR?'))

    @property
    def ilimit(self):
        return float(self.session.query('CURR?'))

    @vset.setter
    def ilimit(self, value):
        self.session.write(f'CURR {value}')

    @property
    def vrange(self):
        return self.session.query('VOLT:RANGE?')

    @vrange.setter
    def vrange(self, value):
        if value in self.rangelist:
            self.session.write(f'VOLT:RANGE {value}')
