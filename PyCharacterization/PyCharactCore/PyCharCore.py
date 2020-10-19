# -*- coding: utf-8 -*-
"""
Created on Wed Feb 19 10:57:58 2020

@author: Javier
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar  5 14:13:45 2019

@author: aguimera
"""
import PyqtTools.DaqInterface as DaqInt
import numpy as np
import PyCharactCore.HwConf.HwConfig as BoardConf


class ChannelsConfig():

    # DCChannelIndex[ch] = (index, sortindex)
    DCChannelIndex = None
    ACChannelIndex = None
    ChNamesList = None
    AnalogInputs = None
    DigitalOutputs = None
    MyConf = None
    AO2Out = None
    AO3Out = None

    # Events list
    DataEveryNEvent = None
    DataDoneEvent = None



    def _InitAnalogInputs(self):
        print('InitAnalogInputs')
        self.DCChannelIndex = {}
        self.ACChannelIndex = {}
        InChans = []
        index = 0
        sortindex = 0
        for ch in self.ChNamesList:
            if self.AcqDC:
                InChans.append(self.aiChannels[ch][0])
                self.DCChannelIndex[ch] = (index, sortindex)
                index += 1
                print(ch, ' DC -->', self.aiChannels[ch][0])
                print('SortIndex ->', self.DCChannelIndex[ch])
            if self.AcqAC:
                InChans.append(self.aiChannels[ch][1])
                self.ACChannelIndex[ch] = (index, sortindex)
                index += 1
                print(ch, ' AC -->', self.aiChannels[ch][1])
                print('SortIndex ->', self.ACChannelIndex[ch])
            sortindex += 1
        print('Input ai', InChans)

        self.AnalogInputs = DaqInt.ReadAnalog(InChans=InChans)
        # events linking
        self.AnalogInputs.EveryNEvent = self.EveryNEventCallBack
        self.AnalogInputs.DoneEvent = self.DoneEventCallBack

    def _InitAnalogOutputs(self, ChVds, ChVs, ChAo2, ChAo3):
        print('ChVds ->', ChVds)
        print('ChVs ->', ChVs)
        self.VsOut = DaqInt.WriteAnalog((ChVs,))
        self.VdsOut = DaqInt.WriteAnalog((ChVds,))
        if ChAo2:
            self.AO2Out = DaqInt.WriteAnalog((ChAo2,))
        if ChAo3:
            self.AO3Out = DaqInt.WriteAnalog((ChAo3,))

    def __init__(self, Channels,
                 AcqDC=True, AcqAC=True,
                 ChVds='ao0', ChVs='ao1',
                 ACGain=1.1e5, DCGain=10e3, Board='MB41'):
        print('InitChannels')
        # self._InitAnalogOutputs(ChVds=ChVds, ChVs=ChVs)

        self.ChNamesList = sorted(Channels)
        print(self.ChNamesList)
        self.AcqAC = AcqAC
        self.AcqDC = AcqDC
        self.ACGain = ACGain
        self.DCGain = DCGain
        print('Board---->', Board)

        self.MyConf = BoardConf.HwConfig[Board]
        self.aiChannels = self.MyConf['aiChannels']
        self.aoChannels = self.MyConf['aoChannels']
        self._InitAnalogOutputs(ChVds=self.aoChannels['ChVds'],
                                ChVs=self.aoChannels['ChVs'],
                                ChAo2=self.aoChannels['ChAo2'],
                                ChAo3=self.aoChannels['ChAo3'],
                                )

        self._InitAnalogInputs()
        # self.ClearSig = np.zeros((1, len(MyConf['ColOuts'])),
        #                 dtype=np.bool).astype(np.uint8)
        # self.ClearSig = np.hstack((ClearSig, ClearSig))

    def StartAcquisition(self, Vgs, Vds,
                         AnalogOutputs, **kwargs):
        print('StartAcquisition')
        print(AnalogOutputs)
        if AnalogOutputs:
            ChAo2 = AnalogOutputs['ChAo2']
            ChAo3 = AnalogOutputs['ChAo3']
        else:
            ChAo2 = None
            ChAo3 = None
        self.SetBias(Vgs=Vgs, Vds=Vds, ChAo2=ChAo2, ChAo3=ChAo3)


        EveryN = 1000
        self.AnalogInputs.ReadContData(Fs=100,
                                       EverySamps=EveryN)

    def SetBias(self, Vgs, Vds, ChAo2, ChAo3):
        print('ChannelsConfig SetBias Vgs ->', Vgs, 'Vds ->', Vds,
              'Ao2 ->', ChAo2, 'Ao3 ->', ChAo3,)
        self.VdsOut.SetVal(Vds)
        self.VsOut.SetVal(-Vgs)
        if self.AO2Out:
            self.AO2Out.SetVal(ChAo2)
        if self.AO3Out:
            self.AO3Out.SetVal(ChAo3)
        self.BiasVd = Vds-Vgs
        self.Vgs = Vgs
        self.Vds = Vds

    def _SortChannels(self, data, SortDict):
        # Sort by aianalog input
        (samps, inch) = data.shape
        aiData = np.zeros((samps, len(SortDict)))
        for chn, inds in sorted(SortDict.items()):
            aiData[:, inds[1]] = data[:, inds[0]]

        # Sort by digital columns
        aiData = aiData.transpose()
        # MuxData = np.ndarray(self.OutputShape)

        # nColumns = len(self.DigColumns)
        # for indB in range(self.nBlocks):
        #     startind = indB * self.nSampsCo * nColumns
        #     stopind = self.nSampsCo * nColumns * (indB + 1)
        #     Vblock = aiData[:, startind: stopind]
        #     ind = 0
        #     for chData in Vblock[:, :]:
        #         for Inds in self.SortDInds:
        #             MuxData[ind, :, indB] = chData[Inds]
        #             ind += 1
        # return aiData, MuxData
        return aiData

    def EveryNEventCallBack(self, Data):
        _DataEveryNEvent = self.DataEveryNEvent
        aiDataDC = None
        aiDataAC = None

        if _DataEveryNEvent is not None:
            if self.AcqDC:
                aiDataDC = self._SortChannels(Data, self.DCChannelIndex)
                aiDataDC = (aiDataDC-self.BiasVd) / self.DCGain
            if self.AcqAC:
                aiDataAC = self._SortChannels(Data, self.ACChannelIndex)
                aiDataAC = aiDataAC / self.ACGain

            _DataEveryNEvent(aiDataDC, aiDataAC)

    def DoneEventCallBack(self, Data):
        print('Done callback')

    def Stop(self):
        print('Stopppp')
        self.SetBias(Vgs=0, Vds=0, ChAo2=0, ChAo3=0)
        self.AnalogInputs.StopContData()


#    def __del__(self):
#        print('Delete class')
#        self.Inputs.ClearTask()
#
