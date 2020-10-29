# -*- coding: utf-8 -*-
"""
Created on Wed Feb 19 10:56:29 2020

@author: Javier
"""

from PyQt5 import Qt
import pyqtgraph.parametertree.parameterTypes as pTypes
import numpy as np
import PyCharactCore.PyCharAcqCore as CoreMod
import PyCharactCore.HwConf.HwConfig as BoardConf
import copy


SampSettingConf = ({'title': 'Channels Config',
                    'name': 'ChsConfig',
                    'type': 'group',
                    'children': (
                                 # {'title': 'Acquire DC',
                                 #  'name': 'AcqDC',
                                 #  'type': 'bool',
                                 #  'value': True},
                                 # {'title': 'Acquire AC',
                                 #  'name': 'AcqAC',
                                 #  'type': 'bool',
                                 #  'value': False},
                                 {'title': 'Gain DC',
                                  'name': 'DCGain',
                                  'type': 'float',
                                  'value': 10e3,
                                  'siPrefix': True, },
                                 {'title': 'Gain AC',
                                  'name': 'ACGain',
                                  'type': 'float',
                                  'value': 1e6,
                                  'siPrefix': True, },
                                 {'tittle': 'Selected Board',
                                  'name': 'Board',
                                  'type': 'list',
                                  'values': ['MainBoard_8x8',
                                             'MainBoard',
                                             'MainBoard_16x16',
                                             'Mos2',
                                             'MB41',
                                             'MB42',
                                             'MainBoard_v3'], },
                                 {'tittle': 'Row Channels',
                                  'name': 'Channels',
                                  'type': 'group',
                                  'children': (), },

                                 {'tittle': 'Columns Channels',
                                  'name': 'DigColumns',
                                  'type': 'group',
                                  'children': (), }

                                 ), },

                   {'name': 'Sampling Settings',
                    'type': 'group',
                    'children': ({'title': 'Sampling Frequency',
                                  'name': 'Fs',
                                  'type': 'float',
                                  'value': 30e3,
                                  'step': 100,
                                  'siPrefix': True,
                                  'suffix': 'Hz'},
                                 {'title': 'Column Samples',
                                  'name': 'nSampsCo',
                                  'type': 'int',
                                  'value': 200,
                                  'step': 1,
                                  'limits': (1, 10000)},
                                 {'title': 'Acquired Blocks',
                                  'name': 'nBlocks',
                                  'type': 'int',
                                  'value': 200,
                                  'step': 10,
                                  'limits': (10, 10000)},
                                 {'title': 'Averaging',
                                  'name': 'nAvg',
                                  'type': 'int',
                                  'value': 5,
                                  'step': 1,
                                  'limits': (1, 10)},
                                 {'title': 'Interrup Time',
                                  'name': 'Inttime',
                                  'type': 'float',
                                  'value': 0.10,
                                  'step': 0.01,
                                  'limits': (0.10, 50),
                                  'siPrefix': True,
                                  'suffix': 's',
                                  'readonly': True},
                                 {'title': 'Fs by Channel',
                                  'name': 'FsxCh',
                                  'type': 'float',
                                  'value': 1e4,
                                  'step': 100,
                                  'siPrefix': True,
                                  'suffix': 'Hz',
                                  'readonly': True},
                                 # {'title': '_Vds',
                                 #  'name': 'Vds',
                                 #  'type': 'float',
                                 #  'value': 0.05,
                                 #  'step': 0.01,
                                 #  'limits': (-0.1, 0.1)},
                                 # {'title': '_Vgs',
                                 #  'name': 'Vgs',
                                 #  'type': 'float',
                                 #  'value': 0.1,
                                 #  'step': 0.1,
                                 #  'limits': (-0.1, 0.5)},
                                 {'tittle': 'Analog Outputs',
                                  'name': 'AnalogOutputs',
                                  'type': 'group',
                                  'children': (), }, ), }
                   )

ChannelParam = {'name': 'Chx',
                'type': 'bool',
                'value': True}

AnalogOutParam = {'name': 'Aox',
                  'type': 'float',
                  'value': 0.1}

###############################################################################


class SampSetParam(pTypes.GroupParameter):
    NewConf = Qt.pyqtSignal()

    Columns = []
    Rows = []
    Acq = {}
    HwSettings = {}


    def __init__(self, **kwargs):
        super(SampSetParam, self).__init__(**kwargs)
        self.addChildren(SampSettingConf)

        self.SampSet = self.param('Sampling Settings')
        self.Fs = self.SampSet.param('Fs')
        self.FsxCh = self.SampSet.param('FsxCh')
        self.SampsCo = self.SampSet.param('nSampsCo')
        self.nBlocks = self.SampSet.param('nBlocks')
        self.AnalogOutputs = self.SampSet.param('AnalogOutputs')

        self.ChsConfig = self.param('ChsConfig')
        self.Config = self.ChsConfig.param('Board')
        self.RowChannels = self.ChsConfig.param('Channels')
        self.ColChannels = self.ChsConfig.param('DigColumns')

        # Init Settings
        # self.on_Acq_Changed()
        self.on_Row_Changed()
        self.on_Col_Changed()
        self.on_Fs_Changed()
        self.on_Ao_Changed()

        print(self.children())
        # Signals
        self.Config.sigTreeStateChanged.connect(self.Hardware_Selection)
        self.RowChannels.sigTreeStateChanged.connect(self.on_Row_Changed)
        self.ColChannels.sigTreeStateChanged.connect(self.on_Col_Changed)
        self.AnalogOutputs.sigTreeStateChanged.connect(self.on_Ao_Changed)
        # self.ChsConfig.param('AcqAC').sigValueChanged.connect(self.on_Acq_Changed)
        # self.ChsConfig.param('AcqDC').sigValueChanged.connect(self.on_Acq_Changed)
        self.Fs.sigValueChanged.connect(self.on_Fs_Changed)
        self.SampsCo.sigValueChanged.connect(self.on_Fs_Changed)
        self.nBlocks.sigValueChanged.connect(self.on_Fs_Changed)

    def Hardware_Selection(self):
        print('Hardware_Selection')
        for k in BoardConf.HwConfig:
            if k == self.Config.value():
                self.HwSettings = BoardConf.HwConfig[k]
        self.GetChannelsChildren()
        self.GetColsChildren()
        self.GetAnalogOutputs()
        self.on_Fs_Changed()

    def GetChannelsChildren(self):
        print('GetChannelsChildren')
        if self.HwSettings:
            self.RowChannels.clearChildren()
            for i in sorted(self.HwSettings['aiChannels']):
                cc = copy.deepcopy(ChannelParam)
                cc['name'] = i
                print(i)
                self.RowChannels.addChild(cc)

    def GetColsChildren(self):
        print('GetColsChildren')
        print(self.ColChannels)
        if self.HwSettings:
            self.ColChannels.clearChildren()

            if self.HwSettings['ColOuts']:
                if type(self.HwSettings['ColOuts']) == list:
                    print('do nothing')
                else:
                    for i in sorted(self.HwSettings['ColOuts']):
                        cc = copy.deepcopy(ChannelParam)
                        cc['name'] = i
                        self.ColChannels.addChild(cc)

    def GetAnalogOutputs(self):
        print('GetAnalogOutputs')
        if self.HwSettings:
            self.AnalogOutputs.clearChildren()
            for i, k in sorted(self.HwSettings['aoChannels'].items()):
                print(i, k)
                if any([i == 'ChAo2', i == 'ChAo3']) and k is not None:
                    cc = copy.deepcopy(AnalogOutParam)
                    cc['name'] = i
                    self.AnalogOutputs.addChild(cc)

    # def on_Acq_Changed(self):
    #     for p in self.ChsConfig.children():
    #         if p.name() is 'AcqAC':
    #             self.Acq[p.name()] = p.value()
    #         if p.name() is 'AcqDC':
    #             self.Acq[p.name()] = p.value()
    #     self.NewConf.emit()

    def on_Fs_Changed(self):
        Ts = 1/self.Fs.value()
        FsxCh = 1/(Ts*self.SampsCo.value())
        IntTime = (1/(FsxCh)*self.nBlocks.value())
        self.SampSet.param('FsxCh').setValue(FsxCh)
        self.SampSet.param('Inttime').setValue(IntTime)

    def on_Row_Changed(self):
        self.Rows = []
        for p in self.RowChannels.children():
            if p.value() is True:
                self.Rows.append(p.name())
        self.NewConf.emit()

    def on_Col_Changed(self):
        self.Columns = []
        for p in self.ColChannels.children():
            if p.value() is True:
                self.Columns.append(p.name())
        self.on_Fs_Changed()
        self.NewConf.emit()

    def on_Ao_Changed(self):
        self.Ao = {}
        for p in self.AnalogOutputs.children():
            self.Ao[p.name()] = p.value()
        self.NewConf.emit()

    def on_Ao_Changed(self):
        self.Ao = {}
        for p in self.AnalogOutputs.children():
            print(p.name(), 'namep')
            self.Ao[p.name()] = p.value()

        self.NewConf.emit()
        if 'ChAo2' in self.Ao:
            self.Ao2 = self.AnalogOutputs.param('ChAo2')
        else: self.Ao2 = None
        if 'ChAo3' in self.Ao:       
            self.Ao3 = self.AnalogOutputs.param('ChAo3')
        else:
            self.Ao3 = None

    def GetRowNames(self):
        Ind = 0
        RowNames = {}

        # if self.ChsConfig.param('AcqDC').value():
        for Row in self.Rows:
            RowNames[Row] = Ind
            Ind += 1

        # if self.ChsConfig.param('AcqAC').value():
        #     for Row in self.Rows:
        #         RowNames[Row + 'AC'] = Ind
        #         Ind += 1

        return RowNames

    def GetChannelsNames(self):
        Ind = 0
        ChannelNames = {}
        ChannelsDCNames = {}

        # if self.ChsConfig.param('AcqDC').value():
        for Row in self.Rows:
            ChannelsDCNames[Row] = Ind                   
            for Col in self.Columns:
                ChannelNames[Row + Col] = Ind
                Ind += 1

        # if self.ChsConfig.param('AcqAC').value():
        #     for Row in self.Rows:
        #         for Col in self.Columns:
        #             ChannelNames[Row + Col + 'AC'] = Ind
        #             Ind += 1

        return ChannelNames, ChannelsDCNames

    def GetSampKwargs(self):
        GenKwargs = {}
        for p in self.SampSet.children():
            print(p.name(), '-->', p.value())
            if p.name() == 'AnalogOutputs':
                GenKwargs[p.name()] = self.Ao
                print(self.Ao)
            else:
                GenKwargs[p.name()] = p.value()
        print(GenKwargs)
        return GenKwargs

    def GetChannelsConfigKwargs(self):
        ChanKwargs = {}
        for p in self.ChsConfig.children():
            if p.name() == 'Channels':
                ChanKwargs[p.name()] = self.Rows
            elif p.name() == 'DigColumns':
                ChanKwargs[p.name()] = self.Columns
            else:
                ChanKwargs[p.name()] = p.value()

        return ChanKwargs

###############################################################################


class DataAcquisitionThread(Qt.QThread):
    NewMuxData = Qt.pyqtSignal()

    def __init__(self, ChannelsConfigKW, SampKw, AvgIndex=5):
        super(DataAcquisitionThread, self).__init__()
        self.DaqInterface = CoreMod.ChannelsConfig(**ChannelsConfigKW)
        self.DaqInterface.DataEveryNEvent = self.NewData
        self.SampKw = SampKw
        print('SampKWKWKW')
        print(SampKw)
        self.AvgIndex = AvgIndex

    def run(self, *args, **kwargs):
        self.DaqInterface.StartAcquisition(**self.SampKw)
        loop = Qt.QEventLoop()
        loop.exec_()

    def NewData(self, aiDataDC, aiDataAC):
        if aiDataAC is not None:
            print('AC--DC')       
            self.aiData = aiDataDC
            self.aiDataAC = aiDataAC
        else:
            self.aiData = aiDataDC

        self.NewMuxData.emit()
