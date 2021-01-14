
# -*- coding: utf-8 -*-
"""
Created on Wed Feb 19 10:26:32 2020

@author: Javier
"""
#

from __future__ import print_function
from PyQt5 import Qt
from qtpy.QtWidgets import (QHeaderView, QCheckBox, QSpinBox, QLineEdit,
                            QDoubleSpinBox, QTextEdit, QComboBox,
                            QTableWidget, QAction, QMessageBox, QFileDialog,
                            QInputDialog)

from qtpy import QtWidgets, uic
import numpy as np
import time
import os
import sys
from pyqtgraph.parametertree import Parameter, ParameterTree

import PyqtTools.FileModule as FileMod
import PyqtTools.Mux_CharacterizationModule as Charact

from PyqtTools.CharactPlot import CharactPlotter as Plotter

import PyCharactCore.PyCharAcqThread as AcqMod


class MainWindow(Qt.QWidget):
    ''' Main Window '''

    def __init__(self):
        super(MainWindow, self).__init__()

        self.threadAcq = None
        self.threadSave = None
        self.threadPlotter = None
        self.threadPSDPlotter = None
        self.threadPlotterRaw = None
        self.threadCharact = None
        self.RefreshGrapg = None

        layout = Qt.QVBoxLayout(self)

        self.btnAcq = Qt.QPushButton("Start Acq!")
        layout.addWidget(self.btnAcq)

        self.SamplingPar = AcqMod.SampSetParam(name='SampSettingConf')
        self.Parameters = Parameter.create(name='App Parameters',
                                           type='group',
                                           children=(self.SamplingPar,))

        self.SwParams = Charact.SweepsConfig(QTparent=self, name='Sweeps Configuration')
        self.Parameters.addChild(self.SwParams)

        self.treepar = ParameterTree()
        self.treepar.setParameters(self.Parameters, showTop=False)
        self.treepar.setWindowTitle('pyqtgraph example: Parameter Tree')

        layout.addWidget(self.treepar)

        self.setGeometry(750, 40, 500, 900)
        self.setWindowTitle('MainWindow')

        self.btnAcq.clicked.connect(self.on_btnStart)

        self.FileParameters = FileMod.SaveFileParameters(QTparent=self,
                                                          name='Record File')

        self.ConfigParameters = FileMod.SaveSateParameters(QTparent=self,
                                                           name='Configuration File')
        self.Parameters.addChild(self.ConfigParameters)

    def on_btnStart(self):
        if self.threadAcq is None:
            self.GenKwargs = self.SamplingPar.GetSampKwargs()
            GenChanKwargs = self.SamplingPar.GetChannelsConfigKwargs()

            # Characterization part
            self.SweepsKwargs = self.SwParams.GetConfigSweepsParams()
            self.DcSaveKwargs = self.SwParams.GetSaveSweepsParams()

            # PSD Parameters
            self.PSDKwargs = self.SwParams.GetPSDParams()[0]
            self.AC = self.SwParams.GetPSDParams()[1]
            GenChanKwargs['AcqAC'] = self.AC
            self.SweepsKwargs['ACenable'] = self.AC

            # Acquisition part
            self.threadAcq = AcqMod.DataAcquisitionThread(ChannelsConfigKW=GenChanKwargs,
                                                          SampKw=self.GenKwargs,
                                                          # AvgIndex=AvgIndex,
                                                          )

            self.threadAcq.NewMuxData.connect(self.on_NewSample)
            DigColumns = self.threadAcq.DaqInterface.DigColumns

            if self.threadAcq.DaqInterface.doColumns:
                ChannelsNames = self.SamplingPar.GetChannelsNames()[0]
                if self.threadAcq.DaqInterface.doColumns['Col01'] is None:
                    self.DO, IndexDigitalLines = self.threadAcq.DaqInterface.GetDecoderSignal()
                else:
                    self.DO, IndexDigitalLines = self.threadAcq.DaqInterface.SetDigitalOutputs()
            else: 
                IndexDigitalLines = None
                ChannelsNames = self.SamplingPar.GetChannelsNames()[1]
            
            DCChannelsNames = self.SamplingPar.GetChannelsNames()[1]
            print(DCChannelsNames)
            print('IndexDigitalLines', IndexDigitalLines)
            print('ChannelsNames', ChannelsNames)
            print(len(ChannelsNames))

            self.threadCharact = Charact.StbDetThread(
                                                      nChannels=len(DCChannelsNames),
                                                      ChnName=ChannelsNames,
                                                      DigColumns=DigColumns,
                                                      IndexDigitalLines=IndexDigitalLines,
                                                      PlotterDemodKwargs=self.PSDKwargs,
                                                      # PlotterDemodKwargs=self.PsdPlotParams.GetParams(),
                                                       **self.SweepsKwargs)

            self.threadCharact.NextVg.connect(self.on_NextVg)
            self.threadCharact.NextVd.connect(self.on_NextVd)
            self.threadCharact.NextDigital.connect(self.on_NextDigital)
            self.threadCharact.CharactEnd.connect(self.on_CharactEnd)

            self.threadCharact.RefreshPlots.connect(self.on_RefreshPlots)

            self.GenKwargs['Vgs'] = self.threadCharact.NextVgs
            self.GenKwargs['Vds'] = self.threadCharact.NextVds

            if self.threadAcq.DaqInterface.DOSwitch:
                print('SwitchDigitalBoard')
                self.threadCharact.EventCalcAC = self.SwitchSignal

            if self.threadAcq.DaqInterface.doColumns:
                print('DigitalSignalllll---->', self.DO)
                time.sleep(4)
                if len(self.DO.shape) == 1:
                    signal = self.DO
                else:
                    signal = self.DO[:, 0]

                self.threadAcq.DaqInterface.DigitalOutputs.SetDigitalSignal(Signal=signal)

            if self.AC:
                DevACVals = self.threadCharact.SaveDCAC.DevACVals
            else:
                DevACVals = None
            self.CharPlot = Plotter(self.threadCharact.SaveDCAC.DevDCVals,
                                    DevACVals)

            self.threadCharact.start()
            self.threadAcq.start()
            self.CharPlot.start()

            self.btnAcq.setText("Stop Gen")
            self.OldTime = time.time()
            self.Tss = []
        else:
            self.threadAcq.DaqInterface.Stop()
            self.threadAcq = None

            if self.threadCharact is not None:
                self.threadCharact.stop()
                self.threadCharact = None

            self.btnAcq.setText("Start Gen")

    def on_NewSample(self):
        ''' Visualization of streaming data-WorkThread. '''
        Ts = time.time() - self.OldTime
        self.Tss.append(Ts)
        self.OldTime = time.time()

        if self.threadCharact is not None: #Flag estable and ACenable
            print('on_NewSample')
            if self.threadCharact.Stable and self.threadCharact.ACenable:
                self.threadCharact.AddData(self.threadAcq.aiDataAC.transpose())

                # self.CharPlot.RefreshPlot(VgInd=self.threadCharact.VgIndex,
                #                           VdInd=self.threadCharact.VdIndex)

            else:
                self.threadCharact.AddData(self.threadAcq.aiData.transpose())

                # self.CharPlot.RefreshPlot(VgInd=self.threadCharact.VgIndex,
                #                           VdInd=self.threadCharact.VdIndex)


        print('sample time', Ts, np.mean(self.Tss))

    def on_NextVg(self):
        if self.SamplingPar.Ao2:
            Ao2 = self.SamplingPar.Ao2.value()
            Ao3 = self.SamplingPar.Ao3.value()
        else:
            Ao2 = None
            Ao3 = None
        # self.CharPlot.RefreshPlot(VgInd=self.threadCharact.VgIndex,
        #                           VdInd=self.threadCharact.VdIndex)

        self.threadAcq.DaqInterface.SetBias(Vgs=self.threadCharact.NextVgs,
                                            Vds=self.threadCharact.NextVds,
                                            ChAo2=Ao2,
                                            ChAo3=Ao3)
        print('NEXT VGS SWEEP')

    def on_NextVd(self):
        if self.SamplingPar.Ao2:
            Ao2 = self.SamplingPar.Ao2.value()
            Ao3 = self.SamplingPar.Ao3.value()
        else:
            Ao2 = None
            Ao3 = None

        # self.CharPlot.RefreshPlot(VgInd=self.threadCharact.VgIndex,
        #                           VdInd=self.threadCharact.VdIndex)

        self.threadAcq.DaqInterface.SetBias(Vgs=self.threadCharact.NextVgs,
                                            Vds=self.threadCharact.NextVds,
                                            ChAo2=Ao2,
                                            ChAo3=Ao3)

    def on_NextDigital(self):
        print('on_NextDigital')
        print(self.threadCharact.DigIndex)
        NewDigitalSignal = self.DO[:, self.threadCharact.DigIndex]
        print(NewDigitalSignal, '--NewDigitalSignal--', self.threadCharact.DigIndex)
        self.threadAcq.DaqInterface.DigitalOutputs.SetDigitalSignal(Signal=NewDigitalSignal)
        if self.SamplingPar.Ao2:
            Ao2 = self.SamplingPar.Ao2.value()
            Ao3 = self.SamplingPar.Ao3.value()
        else:
            Ao2 = None
            Ao3 = None
        self.threadAcq.DaqInterface.SetBias(Vgs=self.threadCharact.NextVgs,
                                            Vds=self.threadCharact.NextVds,
                                            ChAo2=Ao2,
                                            ChAo3=Ao3)

    def on_RefreshPlots(self):
        print('Refresh Plots')
        self.CharPlot.RefreshPlot(VgInd=self.threadCharact.VgIndex,
                                  VdInd=self.threadCharact.VdIndex)


    def SwitchSignal(self, Signal):
        print('SWITCHDCDCDC')
        AC = np.array([1, 1, 1, 1, 1, 1, 1, 1, 1], dtype=np.uint8)
        DC = np.array([0, 1, 0, 0, 0, 0, 0, 0, 0], dtype=np.uint8)
        if Signal == 'AC':
            print('AC')
            self.threadAcq.DaqInterface.SwitchOut.SetDigitalSignal(Signal=AC)
        if Signal == 'DC':
            self.threadAcq.DaqInterface.SwitchOut.SetDigitalSignal(Signal=DC)

    def on_CharactEnd(self):
        print('END Charact')
        self.threadCharact.NextVg.disconnect()
        self.threadCharact.NextVd.disconnect()
        self.threadCharact.CharactEnd.disconnect()
        CharactDCDict = self.threadCharact.DCDict
        CharactACDict = self.threadCharact.ACDict

        self.threadCharact.SaveDCAC.SaveDicts(Dcdict=CharactDCDict,
                                              Acdict=CharactACDict,
                                              **self.DcSaveKwargs)
        self.threadAcq.NewMuxData.disconnect()
        
        self.threadAcq.DaqInterface.Stop()
        self.threadAcq.terminate()
        self.threadAcq = None

        if self.threadSave is not None:
            self.threadSave.terminate()
            self.threadSave = None

        if self.threadPlotter is not None:
            self.threadPlotter.terminate()
            self.threadPlotter = None


def main():
    import argparse
    import pkg_resources

    # Add version option
    __version__ = pkg_resources.require("PyqtTools")[0].version
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', action='version',
                        version='%(prog)s {version}'.format(
                            version=__version__))
    parser.parse_args()

    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()