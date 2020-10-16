#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar  5 14:13:45 2019

@author: aguimera
"""
import PyqtTools.DaqInterface as DaqInt
import numpy as np
import PyTMCore.HwConf.HwConfig as BoardConf


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

    def _InitDigitalOutputs(self):
        print('InitDigitalOutputs')
        print(self.DigColumns)
        DOChannels = []

        # for digc in sorted(self.DigColumns):
        for k, v in self.doColumns.items():
            DOChannels.append(v[0])
            if len(v) > 1:
                DOChannels.append(v[1])
                
        print(DOChannels)

        self.DigitalOutputs = DaqInt.WriteDigital(Channels=DOChannels)

    def _InitAnalogOutputs(self, ChVds, ChVs, ChAo2, ChAo3):
        print('ChVds ->', ChVds)
        print('ChVs ->', ChVs)
        self.VsOut = DaqInt.WriteAnalog((ChVs,))
        self.VdsOut = DaqInt.WriteAnalog((ChVds,))
        if ChAo2:
            self.AO2Out = DaqInt.WriteAnalog((ChAo2,))
        if ChAo3:
            self.AO3Out = DaqInt.WriteAnalog((ChAo3,))

    def __init__(self, Channels, DigColumns,
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
        self.doColumns = self.MyConf['ColOuts']
        self.aoChannels = self.MyConf['aoChannels']
        self._InitAnalogOutputs(ChVds=self.aoChannels['ChVds'],
                                ChVs=self.aoChannels['ChVs'],
                                ChAo2=self.aoChannels['ChAo2'],
                                ChAo3=self.aoChannels['ChAo3'],
                                )

        self._InitAnalogInputs()
        self.DigColumns = sorted(DigColumns)
        self._InitDigitalOutputs()

        MuxChannelNames = []
        for Row in self.ChNamesList:
            for Col in self.DigColumns:
                MuxChannelNames.append(Row + Col)
        self.MuxChannelNames = MuxChannelNames
        print(self.MuxChannelNames)

        if self.AcqAC and self.AcqDC:
            self.nChannels = len(self.MuxChannelNames)*2
        else:
            self.nChannels = len(self.MuxChannelNames)

    def StartAcquisition(self, Fs, nSampsCo, nBlocks, Vgs, Vds,
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
        self.SetDigitalOutputs(nSampsCo=nSampsCo)
        print('DSig set')
        self.nBlocks = nBlocks
        self.nSampsCo = nSampsCo
#        self.OutputShape = (nColumns * nRows, nSampsCh, nblocs)
        self.OutputShape = (len(self.MuxChannelNames), nSampsCo, nBlocks)
        EveryN = len(self.DigColumns)*nSampsCo*nBlocks
        self.AnalogInputs.ReadContData(Fs=Fs,
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

    def SetDigitalOutputs(self, nSampsCo):
        hwLinesMap = {}
        for ColName, hwLine in self.doColumns.items():
            il = int(hwLine[0][4:])
            hwLinesMap[il] = (ColName, hwLine)
        
        # Gen inverted control output, should be the next one of the digital line ('lineX', 'lineX+1')
        if len(self.doColumns[ColName]) > 1:
            GenInvert = True
        else:
            GenInvert = False

        # Gen sorted indexes for demuxing
        SortIndDict = {}
        for ic, coln in enumerate(sorted(self.DigColumns)):
            SortIndDict[coln] = ic
        
        DOut = np.array([], dtype=np.bool)
        SortDInds = np.zeros((len(self.DigColumns), nSampsCo), dtype=np.int64)
        SwitchOrder = 0
        for il, (nLine, (LineName, hwLine)) in enumerate(sorted(hwLinesMap.items())):
            Lout = np.zeros((1, nSampsCo*len(self.DigColumns)), dtype=np.bool)    
            if LineName in self.DigColumns:
                # print(il, nLine, hwLine, LineName)
                Lout[0, nSampsCo * SwitchOrder: nSampsCo * (SwitchOrder + 1)] = True
                SortDInds[SortIndDict[LineName], : ] = np.arange(nSampsCo * SwitchOrder,
                                                             nSampsCo * (SwitchOrder + 1) )
                SwitchOrder += 1
            
            if GenInvert:
                Cout = np.vstack((Lout, ~Lout))
            else:
                Cout = Lout        
            DOut = np.vstack((DOut, Cout)) if DOut.size else Cout

        SortDIndsL = [inds for inds in SortDInds]

        self.SortDInds = SortDInds
        self.DigitalOutputs.SetContSignal(Signal=DOut.astype(np.uint8))

    def _SortChannels(self, data, SortDict):
        # Sort by aianalog input
        (samps, inch) = data.shape
        aiData = np.zeros((samps, len(SortDict)))
        for chn, inds in sorted(SortDict.items()):
            aiData[:, inds[1]] = data[:, inds[0]]

        # Sort by digital columns
        aiData = aiData.transpose()
        MuxData = np.ndarray(self.OutputShape)

        nColumns = len(self.DigColumns)
        for indB in range(self.nBlocks):
            startind = indB * self.nSampsCo * nColumns
            stopind = self.nSampsCo * nColumns * (indB + 1)
            Vblock = aiData[:, startind: stopind]
            ind = 0
            for chData in Vblock[:, :]:
                for Inds in self.SortDInds:
                    MuxData[ind, :, indB] = chData[Inds]
                    ind += 1
        return aiData, MuxData

    def EveryNEventCallBack(self, Data):
        _DataEveryNEvent = self.DataEveryNEvent

        if _DataEveryNEvent is not None:
            if self.AcqDC:
                aiDataDC, MuxDataDC = self._SortChannels(Data,
                                                         self.DCChannelIndex)
                aiDataDC = (aiDataDC-self.BiasVd) / self.DCGain
                MuxDataDC = (MuxDataDC-self.BiasVd) / self.DCGain
            if self.AcqAC:
                aiDataAC, MuxDataAC = self._SortChannels(Data,
                                                         self.ACChannelIndex)
                aiDataAC = aiDataAC / self.ACGain
                MuxDataAC = MuxDataAC / self.ACGain

            if self.AcqAC and self.AcqDC:
                aiData = np.vstack((aiDataDC, aiDataAC))
                MuxData = np.vstack((MuxDataDC, MuxDataAC))
                _DataEveryNEvent(aiData, MuxData)
            elif self.AcqAC:
                _DataEveryNEvent(aiDataAC, MuxDataAC)
            elif self.AcqDC:
                _DataEveryNEvent(aiDataDC, MuxDataDC)

    def DoneEventCallBack(self, Data):
        print('Done callback')

    def Stop(self):
        print('Stopppp')
        self.SetBias(Vgs=0, Vds=0, ChAo2=0, ChAo3=0)
        self.AnalogInputs.StopContData()
        if self.DigitalOutputs is not None:
            print('Clear Digital')
#            self.DigitalOutputs.SetContSignal(Signal=self.ClearSig)
            self.DigitalOutputs.ClearTask()
            self.DigitalOutputs = None


#    def __del__(self):
#        print('Delete class')
#        self.Inputs.ClearTask()
#
