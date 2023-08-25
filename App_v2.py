import typing
from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtWidgets import QWidget
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
import sys  # We need sys so that we can pass argv to QApplication
import os
import time
import random

import serial
import serial.tools.list_ports

import json 
import pickle as pkl

import wandb

# key = "b2feb8c598557c25c8924b3f3dc0351f498b2a8a"
# wandb.init(project="test")

# for i in range(10):
#     wandb.log({"metric": random.random()})

def createDir(path):
    try:
        os.makedirs(path)
    except:
        pass

with open("flags.json", "r") as f:
    flags = json.load(f)

plotsInfo = [
                {"name": "velocidad vs time", "yAxis": "velocidad", "xAxis":"time", "x": 0, "y": 0}, 
                {"name": "encoderD vs time", "yAxis": "encoderD", "xAxis":"time", "x":0, "y":1}, 
                {"name":"encoderI vs time", "yAxis":"encoderI", "xAxis":"time", "x":1, "y":0}, 
                {"name":"velocidad vs encoderD", "yAxis":"velocidad", "xAxis":"encoderD", "x":1, "y":1}
            ]

LDataStream =   [
                {"name":"inicio", "numBytes": 1, "indexData": 0}, 
                {"name":"encoderI", "numBytes": 2, "indexData": 1}, 
                {"name":"encoderD", "numBytes": 2, "indexData": 2}, 
                {"name":"velocidad", "numBytes": 2, "indexData": 3}, 
                {"name":"flag", "numBytes": 1, "indexData": 4},
                {"name":"time", "numBytes": 4, "indexData": 5}, 
                {"name":"fin", "numBytes": 1, "indexData": 6}
                ]

LKeyBindings = [{"desc": "Start the run", "key": "S", "command":"P"}, {"desc": "Stop the run", "key": "Esc", "command":"S"}, {"desc": "Increase velocity", "key": "Up", "command":""}, {"desc": "Decrease velocity", "key": "Down", "command":""}, {"desc": "Toggle start/stop", "key": "Space", "command":""}] # , {"desc": "Save the project", "key": "Ctrl+S", "command":None}, {"desc": "Open a project", "key": "Ctrl+O", "command":None}]

name2key = {"A":QtCore.Qt.Key.Key_A, "B":QtCore.Qt.Key.Key_B, "C":QtCore.Qt.Key.Key_C, "D":QtCore.Qt.Key.Key_D, "E":QtCore.Qt.Key.Key_E, "F":QtCore.Qt.Key.Key_F, "G":QtCore.Qt.Key.Key_G, "H":QtCore.Qt.Key.Key_H, "I":QtCore.Qt.Key.Key_I, "J":QtCore.Qt.Key.Key_J, "K":QtCore.Qt.Key.Key_K, "L":QtCore.Qt.Key.Key_L, "M":QtCore.Qt.Key.Key_M, "N":QtCore.Qt.Key.Key_N, "O":QtCore.Qt.Key.Key_O, "P":QtCore.Qt.Key.Key_P, "Q":QtCore.Qt.Key.Key_Q, "R":QtCore.Qt.Key.Key_R, "S":QtCore.Qt.Key.Key_S, "T":QtCore.Qt.Key.Key_T, "U":QtCore.Qt.Key.Key_U, "V":QtCore.Qt.Key.Key_V, "W":QtCore.Qt.Key.Key_W, "X":QtCore.Qt.Key.Key_X, "Y":QtCore.Qt.Key.Key_Y, "Z":QtCore.Qt.Key.Key_Z, "0":QtCore.Qt.Key.Key_0, "1":QtCore.Qt.Key.Key_1, "2":QtCore.Qt.Key.Key_2, "3":QtCore.Qt.Key.Key_3, "4":QtCore.Qt.Key.Key_4, "5":QtCore.Qt.Key.Key_5, "6":QtCore.Qt.Key.Key_6, "7":QtCore.Qt.Key.Key_7, "8":QtCore.Qt.Key.Key_8, "9":QtCore.Qt.Key.Key_9, "Enter":QtCore.Qt.Key.Key_Return, "Space":QtCore.Qt.Key.Key_Space, "Up":QtCore.Qt.Key.Key_Up, "Down":QtCore.Qt.Key.Key_Down, "Left":QtCore.Qt.Key.Key_Left, "Right":QtCore.Qt.Key.Key_Right, "Esc":QtCore.Qt.Key.Key_Escape, "Ctrl":QtCore.Qt.Key.Key_Control, "Alt":QtCore.Qt.Key.Key_Alt, "Shift":QtCore.Qt.Key.Key_Shift}

class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)                
        self.plotsInfo = plotsInfo
        self.LDataStream = LDataStream

        for plot in self.plotsInfo:
            plot["legend"] = {}


        self.timer = pg.QtCore.QTimer()
        self.timer.timeout.connect(self.update)

        # toolbar
        fileMenu = QtWidgets.QMenu("&Options", self)
        self.menuBar().addMenu(fileMenu)

        # - add open project inside the options menu
        openProjectAction = fileMenu.addAction("Open project")
        openProjectAction.setShortcut("Ctrl+O")
        openProjectAction.triggered.connect(self.open_project)
        fileMenu.addAction(openProjectAction)

        # - add save project inside the options menu
        saveProjectAction = fileMenu.addAction("Save project")
        saveProjectAction.setShortcut("Ctrl+S")
        saveProjectAction.triggered.connect(self.save_project)
        fileMenu.addAction(saveProjectAction)

        # - add a separator
        fileMenu.addSeparator()

        # - add a check box for saving in wandb
        self.checkBoxWandb = QtGui.QAction("Save in wandb", self, checkable=True)
        fileMenu.addAction(self.checkBoxWandb)
        self.checkBoxWandb.setChecked(False)
        self.checkBoxWandb.triggered.connect(self.connectWandb)

        # - add a separator
        fileMenu.addSeparator()

        # - add key bindings inside the options menu
        keyBindingsAction = fileMenu.addAction("Key bindings")
        keyBindingsAction.setShortcut("Ctrl+K")
        keyBindingsAction.triggered.connect(self.keyBindings)


        plotsMenu = QtWidgets.QMenu("&Plots", self)
        self.menuBar().addMenu(plotsMenu)

        # - add change Layout inside the plots menu
        changeLayoutAction = plotsMenu.addAction("Change layout")
        changeLayoutAction.setShortcut("Ctrl+L")
        changeLayoutAction.triggered.connect(self.change_layout)
        plotsMenu.addAction(changeLayoutAction)

        dataStreamMenu = QtWidgets.QMenu("&Data stream", self)
        self.menuBar().addMenu(dataStreamMenu)

        # - add start reading inside the data stream menu
        changeDataStreamAction = dataStreamMenu.addAction("Change data stream")
        changeDataStreamAction.setShortcut("Ctrl+R")
        changeDataStreamAction.triggered.connect(self.changeDataStream)
        dataStreamMenu.addAction(changeDataStreamAction)

        # add a help menu
        helpMenu = QtWidgets.QMenu("&Help", self)
        self.menuBar().addMenu(helpMenu)
        self.helpAction = helpMenu.addAction("Help")
        self.helpAction.setShortcut("Ctrl+H")
        self.helpAction.triggered.connect(self.help)

        # MAIN SCREEN
        self.mainwidget = QtWidgets.QWidget()
        self.setCentralWidget(self.mainwidget)

        # VERTICAL LAYOUT
        self.mainlayout = QtWidgets.QVBoxLayout()
        self.mainwidget.setLayout(self.mainlayout)

        self.ConsoleGridLayout = QtWidgets.QHBoxLayout()
        self.mainlayout.addLayout(self.ConsoleGridLayout)

        # - add the grid
        self.grid = QtWidgets.QGridLayout()
        self.ConsoleGridLayout.addLayout(self.grid)

        # add a console
        self.ConsoleLayout = QtWidgets.QVBoxLayout()
        self.ConsoleGridLayout.addLayout(self.ConsoleLayout)

        # add the master plot
        self.masterPlot = MasterPlot(self)
        self.masterPlot.setStyleSheet("border: 1px solid black;background-color: rgb(230, 230, 255);")
        self.masterPlot.setFixedHeight(300)
        self.ConsoleLayout.addWidget(self.masterPlot)

        # add the console text
        self.ConsoleLabel = QtWidgets.QLabel("CONSOLE")
        self.ConsoleLabel.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        self.ConsoleLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.ConsoleLayout.addWidget(self.ConsoleLabel)
        
        self.checkBoxLayout = QtWidgets.QHBoxLayout()
        self.checkBoxLayout.setContentsMargins(10, 0, 10, 0)
        self.ConsoleLayout.addLayout(self.checkBoxLayout)
        self.checkBoxLayout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        self.checkBox = QtWidgets.QCheckBox("Print data bytes")
        self.checkBox.setChecked(False)
        self.checkBoxLayout.addWidget(self.checkBox)
        self.printBytes = self.checkBox.isChecked()
        self.checkBox.stateChanged.connect(lambda: setattr(self, "printBytes", self.checkBox.isChecked()))

        self.ConsoleText = ScrollLabel(self)
        self.ConsoleText.setText("11:42:00  -  This is the console")
        self.ConsoleText.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        self.ConsoleText.setContentsMargins(10, 10, 10, 10)
        # self.ConsoleText.setFixedWidth(300)
        self.ConsoleHeight = self.ConsoleText.height()
        self.ConsoleLayout.addWidget(self.ConsoleText)

        self.LConsoleText = []

        self.console = Console(self)
        self.ConsoleLayout.addWidget(self.console)


        # - add the BOTTOM LAYOUT
        self.bottomlayout = QtWidgets.QHBoxLayout()
        self.mainlayout.addLayout(self.bottomlayout)

        # - - add interval spin box
        self.bottomlayout.addWidget(QtWidgets.QLabel("Interval of messages (ms):"))
        self.timerInterval = 50
        self.intervalSpinBox = QtWidgets.QSpinBox()
        self.intervalSpinBox.setRange(20, 100000)
        self.intervalSpinBox.setValue(self.timerInterval)
        self.timer.setInterval(self.intervalSpinBox.value())
        self.bottomlayout.addWidget(self.intervalSpinBox)
        self.intervalSpinBox.valueChanged.connect(lambda: self.changeInterval(self.intervalSpinBox.value()))

        # - - add separator
        self.bottomlayout.addStretch()

        # - - add start button
        self.startButton = QtWidgets.QPushButton("Start")
        self.bottomlayout.addWidget(self.startButton)
        self.startButton.clicked.connect(self.startRun)

        # - - add stop button
        self.stopButton = QtWidgets.QPushButton("Stop")
        self.bottomlayout.addWidget(self.stopButton)
        self.stopButton.clicked.connect(self.stopRun)

        # - - add clear button
        self.clearButton = QtWidgets.QPushButton("Clear")
        self.bottomlayout.addWidget(self.clearButton)
        self.clearButton.clicked.connect(self.clear)

        # - - add separator
        self.bottomlayout.addStretch()

        # - - add combo box
        self.bottomlayout.addWidget(QtWidgets.QLabel("COM Port:"))
        self.comPort = QtWidgets.QComboBox()
        ListOfAvailablePorts = serial.tools.list_ports.comports()
        for port in ListOfAvailablePorts:
            self.comPort.addItem(port.device)
        
        self.comPort.setCurrentIndex(4) # tests
        self.bottomlayout.addWidget(self.comPort)

        # - - add connect button
        self.connectButton = QtWidgets.QPushButton("Connect")
        self.bottomlayout.addWidget(self.connectButton)

        self.connectButton.clicked.connect(self.connect_bt)

        # - - add disconnect button
        self.disconnectButton = QtWidgets.QPushButton("Disconnect")
        self.bottomlayout.addWidget(self.disconnectButton)
        self.disconnectButton.clicked.connect(self.disconnect_bt)
        self.disconnectButton.hide()

        self.create_layout()

        self.gen = self.get_value()

        self.saveFolder = "./"
        self.saveName = "run1"

        self.board = None
        self.counter = 0

        self.listsFlags = []
        self.startSaving = False

        self.velocidad = 20

        self.chrInicio = ord("#")
        self.chrFin = ord("$")

        self.LKeyBindings = LKeyBindings

        self.saveFolder = "./Runs/"

    def help(self):
        # create a window and show a scrollable text with the help
        self.helpWindow = QtWidgets.QWidget()
        self.helpWindow.setWindowTitle("Help")
        self.helpWindow.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        self.helpWindow.show()

        self.helpWindowLayout = QtWidgets.QVBoxLayout()
        self.helpWindow.setLayout(self.helpWindowLayout)

        self.helpText = ScrollLabel(always = "top")
        # make the scroll always at the top
        self.helpText.verticalScrollBar().setValue(0)
        with open("help.txt", "r") as f:
            self.helpText.setText(f.read())

        self.helpText.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        self.helpText.setContentsMargins(10, 10, 10, 10)
        self.helpWindowLayout.addWidget(self.helpText)

    def keyBindings(self):
        print("key bindings")
        self.keyBindingsWindow = LayoutWindow(self, tab = "key")
        self.keyBindingsWindow.show()

    def connectWandb(self):
        if self.checkBoxWandb.isChecked():
            self.update_console("Connecting to wandb. . . ")
            wandb.login()
        else:
            self.update_console("Disconnecting from wandb. . . ")
            wandb.finish()

    # if the key "s" is pressed start saving the data
    def keyPressEvent(self, e):
        # if e.key() == QtCore.Qt.Key.Key_S:
        #     self.startRun()
        
        # if e.key() == QtCore.Qt.Key.Key_Escape:
        #     self.stopRun()
        
        # if e.key() == QtCore.Qt.Key.Key_Space:
        #     if self.timer.isActive():
        #         self.stopRun()
        #     else:
        #         self.startRun()

        # # if the down arrow is pressed put the velocity to -10
        # if e.key() == QtCore.Qt.Key.Key_Down:
        #     if self.velocidad > 10:
        #         self.send_command("V"+str(self.velocidad-10))
        
        # if e.key() == QtCore.Qt.Key.Key_Up:
        #     if self.velocidad < 100:
        #         self.send_command("V"+str(self.velocidad+10))

        # if e.key() == QtCore.Qt.Key.Key_Return:
        #     print("enter")
        #     self.update_console(self.console.text(), recived = False)
        #     self.console.setText("")

        for key in self.LKeyBindings:
            if e.key() == name2key[key["key"]]:
                self.update_console(key["command"], recived = True)
                # self.send_command(key["command"])


    def startRun(self):
        self.timer.start()
        # self.send_command("P")
        if self.checkBoxWandb.isChecked():
            self.startSaving = True
            wandb.init(project="test")

    def stopRun(self):
        print("stopping run. . . ")
        self.timer.stop()
        try:
            self.send_command("S")
        except:
            print("There is no board connected")
        if self.checkBoxWandb.isChecked():
            wandb.finish()
            self.startSaving = False

    def addMasterPlot(self):
        self.plotsInfo.append({"name": "master", "yAxis": self.plotsInfo[0]["yAxis"], "xAxis": self.plotsInfo[0]["xAxis"], "x": 2, "y": 0})
        self.plotsInfo[-1]["legend"] = {}

    def changeInterval(self, value):
        self.timerInterval = max(20, value)
        self.intervalSpinBox.setValue(self.timerInterval)
        self.timer.setInterval(self.timerInterval)

        print("Interval changed to", self.timerInterval, "ms")

    def changeDataStream(self):
        # open a new window with the data stream options
        self.dataStreamWindow = LayoutWindow(self, tab = "data")
        self.dataStreamWindow.show()

    def update_layout(self, plotsInfo):
        print("updating layout. . . ")
        self.plotsInfo = plotsInfo

        self.create_layout()

    def create_layout(self):
        for plot in self.plotsInfo:
            plot["graph"] = Graph(self, plot)
            plot["graph"].plt.setLabel("left", plot["yAxis"])
            plot["graph"].plt.setLabel("bottom", plot["xAxis"])
            plot["data"] = plot["graph"].plt.plot([], [])
            plot["graph"].plt.setTitle(plot["name"])
            # look if the plot has a key "color" if not create it
            try:
                plot["color"]
            except KeyError:
                plot["color"] = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

            if plot["name"] == "master":
                self.graphCheckLayout.addWidget(plot["graph"])
            
            else:
                self.grid.addWidget(plot["graph"], plot["x"], plot["y"])

        for plot in self.plotsInfo:
            plot["other_graphs"] = [p["graph"] for p in self.plotsInfo if p != plot]
            plot["graph"].other_graphs = plot["other_graphs"]

    def update_master_plot(self):
        # look for the master plot 
        for plot in self.plotsInfo:
            if plot["name"] == "master":
                mstPlot = plot

        # for i, data in enumerate(self.LDataStream):
            # if self.checkBox2.isChecked():
                

    def change_layout(self):
        # open a new window with the layout options
        self.layoutWindow = LayoutWindow(self, tab = "plots")
        self.layoutWindow.show()

    def save_project(self):
        print("Saving project. . . ")

        filename = self.saveFolder + self.saveName + time.strftime("%Y%m%d-%H%M%S") + ".pkl"

        createDir("./" + self.saveFolder)

        # open the file dialog
        filename = QtWidgets.QFileDialog.getSaveFileName(self, "Save project", "./"+filename, "Project files (*.pkl)")[0]

        # save the data
        self.save(filename)

    def open_project(self):
        print("opening project. . . ")

        # open the file dialog
        filename = QtWidgets.QFileDialog.getOpenFileName(self, "Open project", "./"+self.saveFolder, "Project files (*.pkl)")[0]
        print("opening", filename)

        # open the file
        with open(filename, "rb") as f:
            data = pkl.load(f)

        # print(data["Lflags"])

        # clear the graphs
        self.clear()

        self.plotsInfo = data["plotsInfo"]
        self.LDataStream = data["LDataStream"]

        self.create_layout()

        # load the data
        for plot in self.plotsInfo:
            plot["data"].setData(data["plotsInfo"][self.plotsInfo.index(plot)]["DataX"], data["plotsInfo"][self.plotsInfo.index(plot)]["DataY"], pen = pg.mkPen(color = data["plotsInfo"][self.plotsInfo.index(plot)]["color"], width=2))
            plot["legend"] = {}
            plot["xAxis"] = data["plotsInfo"][self.plotsInfo.index(plot)]["xAxis"]
            plot["yAxis"] = data["plotsInfo"][self.plotsInfo.index(plot)]["yAxis"]

        # load the flags
        for flag in data["Lflags"]:
            self.mark({"time": flag[0], "flag": flag[1]}, zeroStart = True)

        # change the title of the window with the filename
        self.mainwidget.setWindowTitle(filename)

    def connect_bt(self):
        print("connecting to " + self.comPort.currentText())
        self.board = serial.Serial(self.comPort.currentText(), baudrate = 9600)
        
        print("connected to " + self.comPort.currentText() + " successfully")

        self.connectButton.hide()
        self.disconnectButton.show()

    def disconnect_bt(self):
        print("disconnecting from " + self.comPort.currentText())
        try:
            self.board.close()
        except AttributeError:
            print("There is no board connected")
    
        self.timer.stop()
        self.connectButton.show()
        self.disconnectButton.hide()

    def clear(self):
        # iterate over the self.plotInfo and clear the data
        for plot in self.plotsInfo:
            plot["graph"].plt.clear()
            plot["data"] = plot["graph"].plt.plot([], [])
            plot["legend"] = {}

        self.counter = 0

        self.listsFlags = []

        self.LConsoleText = []
        self.ConsoleText.setText("")

        # clear the master plot
        self.masterPlot.clear()

        # self.legendItems = [{} for i in range(len(self.LGraphs))]

    def update(self):
        self.send_command("U")

        try:
            data = next(self.gen)

            if data is None:
                return
            
            # save to wandb
            if self.startSaving and self.checkBoxWandb.isChecked():
                wandb.log(data)

            if self.counter == 0: 
                self.initialTime = data["time"]
                self.flag = data["flag"]

            elif data["flag"] != self.flag:
                self.flag = data["flag"]
                self.mark(data)

            if self.counter == 0:
                self.initialTime = data["time"]

            data["time"] = data["time"] - self.initialTime

            # iterate over the self.plotInfo and update the data
            for plot in self.plotsInfo:
                self.show_plot(plot["data"], data[plot["xAxis"]], data[plot["yAxis"]] , plot["color"])

            self.counter += 1
        
        except StopIteration:
            self.finish()

    def finish(self):
        self.timer.stop()
        print("Done")
        self.save()
        
    def save(self, filename = None):
        # save using the time as the name        
        print("Saving data in " + filename)
        
        D = {}
        D["Lflags"] = self.listsFlags
        D["LDataStream"] = self.LDataStream

        plotsInfoReduced = []
        for plot in self.plotsInfo:
            plotsInfoReduced.append({"name": plot["name"], "yAxis": plot["yAxis"], "x": plot["x"], "y": plot["y"], "DataX": plot["data"].getData()[0], "DataY": plot["data"].getData()[1], "color": plot["color"], "xAxis": plot["xAxis"]})

        D["plotsInfo"] = plotsInfoReduced
        
        with open(filename, "wb") as f:
            pkl.dump(D, f)

        print("Data saved")        

    def mark(self, data, zeroStart = False, showInOther = None):
        if zeroStart:
            time = data["time"]
        else: 
            time = data["time"] - self.initialTime
        
        # print("marking at", time)
        try:
            flg = flags[str(data["flag"])]
        except KeyError:
            flg = {"name": "unknown", "color": "(255, 125, 0)"}
        
        try:
            color = eval(flg["color"])
        except NameError: 
            color = flg["color"]

        penSettings = pg.mkPen(color = color, width=1, style= QtCore.Qt.PenStyle.DashLine)

        for plot in self.plotsInfo:
            if showInOther == None or showInOther == plot["graph"]:

                dottedLine = pg.InfiniteLine(angle=90, movable=False, pen=penSettings, pos=time, name = flg["name"])
                
                plot["graph"].plt.addItem(dottedLine, ignoreBounds=True)

                dottedLine.opts = {"pen": penSettings, "name": flg["name"]}
                
                if flg["showInLegend"]:
                    legend = plot["graph"].plt.addLegend()

                    if flg["name"] not in plot["legend"].keys():
                        legend.addItem(dottedLine, flg["name"])
                
                plot["legend"][flg["name"]] = dottedLine

        self.listsFlags.append(((time), data["flag"])) 

    def get_value(self):
        data = {}
        while True:
            correctData = False
            for element in sorted(self.LDataStream, key=lambda x: x["indexData"]):
                data[element["name"]] = self.read_bytes(element["numBytes"])

                if data[element["name"]] is None:
                    print("no hay datos que leer")
                    self.update_console("no hay datos que leer")
                    correctData = False
                    break

                else:
                    correctData = True

            if correctData and data["inicio"] != self.chrInicio:
                print("inicio trama incorrecto:", data, "esperado:", self.chrInicio, "recibido:", data["inicio"])
                # self.update_console("inicio trama incorrecto: " + str(data))
                correctData = False
                yield None
            
            elif correctData and data["fin"] != self.chrFin:
                print("fin trama incorrecto:", data)
                # self.update_console("fin trama incorrecto: " + str(data))
                yield None

                if self.printBytes:
                    self.update_console
            
            elif correctData:
                yield data
            
            else:
                yield None

    # def show_master_plot(self, masterPlot):
        




    def show_plot(self, line_plot, newx, newy, color):
        try:
            x = list(line_plot.getData()[0])+[newx]
            y = list(line_plot.getData()[1])+[newy]

        except TypeError:
            x = [newx]
            y = [newy]
        
        # to make the line of the plot wider do this:
        # line_plot.setPen(pg.mkPen(color = color, width=2))
        line_plot.setData(x, y, pen = pg.mkPen(color = color, width=2))

    def read_bytes(self, numBytes):
        if self.board.in_waiting < numBytes:
            return None

        list = [ord(self.board.read()) for i in range(numBytes)]
        if self.printBytes:
            self.update_console("  ".join([str(i) for i in list]))
        # print([i for i in list])
        return int.from_bytes(list, byteorder="little")

    def closeEvent(self, e):
        print("closing")
        try:
            self.board.close()
        except AttributeError:
            print("There is no board connected")

        self.timer.stop()
        e.accept()
    
    def update_console(self, text, recived = True):
        if recived:
            colText = "blue"
        else:
            colText = "red"
            # send the command
            self.send_command(text)

        self.LConsoleText.append([time.strftime("%H:%M:%S"), text, colText])
        
        # show the last x lines that fit in the console
        self.ConsoleText.setText("")
        for i in self.LConsoleText[::]:
            # print(len(self.ConsoleText.text().split("\n"))*self.ConsoleText.fontMetrics().height() + self.ConsoleText.fontMetrics().height() + 80, self.ConsoleHeight, self.ConsoleText.fontMetrics().height())
            # if (len(self.ConsoleText.text().split("\n"))*self.ConsoleText.fontMetrics().height() + self.ConsoleText.fontMetrics().height() + 80) < self.ConsoleHeight:
            self.ConsoleText.setText(self.ConsoleText.text() + '<font color=#808080>' + i[0] + '</font>' + "  -  " + '<font color='+i[2]+'>' + i[1]  +  '</font>'+ "<br>")

    # to be able to use rbg colors in html
    # <font color= 

    def send_command(self, command):
        # print("sending command", command)
        self.board.write(command.encode())
        if command == "P":
            self.startSaving = True

        if "V" in command:
            self.velocidad = int(command[1:])
            print("velocidad", self.velocidad)


class Graph(pg.GraphicsLayoutWidget):
    def __init__(self, parent = None, plot = None):
        super().__init__()
        self.plt = self.addPlot()

        self.proxy = pg.SignalProxy(self.plt.scene().sigMouseMoved, slot=self.mouseMoved, rateLimit=200)

        self.vLine = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('b', width=1, alpha=0.7))
        self.plt.addItem(self.vLine, ignoreBounds=True)

        self.parent = parent
        self.doubleClickFlag = -1

        self.doubleClickPos = []

        self.label = pg.TextItem(text="x=%0.1f,   y=%0.1f" % (0,0), color=(255, 255, 255))

        # self.hLine = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('w', width=1), label='{value:0.1f}')
        # self.plt.addItem(self.hLine, ignoreBounds=True)

        # self.other_graphs = plot["other_graphs"]

    def mouseMoved(self, evt):
        pos = evt[0]

        if self.vLine not in self.plt.items:
            self.plt.addItem(self.vLine, ignoreBounds=True)
            self.vLine.show()

        if self.plt.sceneBoundingRect().contains(pos):
            mousePoint = self.plt.vb.mapSceneToView(pos)
            x, y = int(mousePoint.x()), int(mousePoint.y())
            self.vLine.setPos(x)

            if len(self.doubleClickPos) == 2:
                difference = self.doubleClickPos[1] - self.doubleClickPos[0]
                self.label.setText("x=%0.1f,   y=%0.1f" % (x, y) + "\n" + "Δ = " + str(difference))

            else:
                self.label.setText("x=%0.1f,   y=%0.1f" % (x, y))
            num = (self.plt.getViewBox().state["viewRange"][1][1])*0.05
            # print(num, self.plt.getViewBox().state["viewRange"])
            self.label.setPos(x, y-num)
            self.plt.addItem(self.label, ignoreBounds=True)

            for g in self.other_graphs:
                if g.vLine not in g.plt.items:
                    g.plt.addItem(g.vLine, ignoreBounds=True)
                    g.vLine.show()
                g.vLine.setPos(x)
        
        else:
            self.plt.removeItem(self.vLine)
            self.vLine.hide()

            for g in self.other_graphs:
                g.plt.removeItem(g.vLine)
                g.vLine.hide()
            
            self.plt.removeItem(self.label)


    def mouseDoubleClickEvent(self, e):

        # get the position of the mouse
        pos = QtCore.QPointF(e.pos())
       
        if self.plt.sceneBoundingRect().contains(pos):
            mousePoint = self.plt.vb.mapSceneToView(pos)
            x, y = int(mousePoint.x()), int(mousePoint.y())

            if len(self.doubleClickPos) == 0:
                self.doubleClickFlag = -1

            if len(self.doubleClickPos) == 1:
                self.doubleClickFlag = -2
                difference = x - self.doubleClickPos[0]
                self.label.setText(self.label.toPlainText() +  "\nΔ = " + str(difference))

            elif len(self.doubleClickPos) == 2:
                self.parent.listsFlags.remove((self.doubleClickPos[0], -1))
                self.parent.listsFlags.remove((self.doubleClickPos[1], -2))

                for g in self.parent.plotsInfo:
                    if g["graph"] == self:
                        g["legend"][flags["-1"]["name"]].hide()
                        g["legend"][flags["-2"]["name"]].hide()

                        g["legend"].pop(flags["-1"]["name"])
                        g["legend"].pop(flags["-2"]["name"])

                        print(g["legend"])
                    
                
                self.label.setText(self.label.toPlainText().split("\n")[0])



            if len(self.doubleClickPos) < 2:
                self.parent.mark({"time": x, "flag": self.doubleClickFlag}, zeroStart = True, showInOther = self)
                self.doubleClickPos.append(x)
            
            else:
                self.doubleClickPos = []
                self.doubleClickFlag = -1


class LayoutWindow(QtWidgets.QWidget):
    def __init__(self, parent: QWidget, tab = "plots"):
        super().__init__()

        self.setWindowTitle("Change layout")

        # add tabs to the window
        self.tabs = QtWidgets.QTabWidget()

        # set the window to 700x500
        self.resize(700, 500)

        self.mainLayout = QtWidgets.QVBoxLayout()
        self.setLayout(self.mainLayout)
        self.mainLayout.addWidget(self.tabs)

        self.tabPlots = QtWidgets.QWidget()
        self.tabData = QtWidgets.QWidget()
        self.tabKey = QtWidgets.QWidget()

        self.tabs.addTab(self.tabPlots, "Plots")
        self.tabs.addTab(self.tabData, "Data")
        self.tabs.addTab(self.tabKey, "Key")
        
        self.tabs.setCurrentIndex({"plots": 0, "data": 1, "key": 2}[tab])

        # TAB PLOTS
        self.mainLayoutPlots = QtWidgets.QVBoxLayout()
        self.tabPlots.setLayout(self.mainLayoutPlots)

        self.grid = QtWidgets.QGridLayout()
        self.mainLayoutPlots.addLayout(self.grid)

        self.tabPlots.setContentsMargins(50, 50, 50, 50)

        self.LGraphs = []
        self.plotsInfo = parent.plotsInfo
        self.LDataStream = parent.LDataStream

        self.widgetsPlots = [[] for i in range(len(self.plotsInfo))]

        self.nPlots = 0

        xy = []
        for plot in self.plotsInfo:
            self.new_plot(plot["x"], plot["y"])
            xy.append((plot["x"], plot["y"]))


        maxX = sorted(self.plotsInfo, key = lambda x:x["x"])[-1]["x"]
        maxY = sorted(self.plotsInfo, key = lambda x:x["y"])[-1]["y"]
        
        for x in range(maxX+1):
            for y in range(maxY+1):
                if (x,y) not in xy:
                    self.new_plot(x, y)

        self.create_add_button(self.grid.rowCount(), self.grid.columnCount())

        # - add save layout button
        self.saveLayoutButton = QtWidgets.QPushButton("Save layout")
        self.mainLayoutPlots.addWidget(self.saveLayoutButton)
        self.saveLayoutButton.clicked.connect(self.save_layout)

        self.parent = parent

        # TAB DATA
        layout = QtWidgets.QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        container = QtWidgets.QWidget()
        container.setLayout(layout)

        # add the drag and drop widget
        self.dragLayoutData = DragWidget(orientation=QtCore.Qt.Orientation.Vertical, parent=self)

        self.LDataStream = parent.LDataStream
        for i, data in enumerate(self.LDataStream):
            item = DragItem(data, self)
            self.dragLayoutData.add_item(item)

        self.dragLayoutData.orderChanged.connect(print)
        layout.addWidget(self.dragLayoutData)

        # add a button to add new data
        self.buttonData = QtWidgets.QPushButton("Add new data")
        self.buttonData.clicked.connect(self.addStream)
        layout.addWidget(self.buttonData)

        self.mainLayoutData = QtWidgets.QVBoxLayout()
        self.tabData.setLayout(self.mainLayoutData)

        self.mainLayoutData.addWidget(container)

        # TAB KEY
        self.mainLayoutKey = QtWidgets.QVBoxLayout()
        self.tabKey.setLayout(self.mainLayoutKey)
        self.tabKey.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        
        self.LKeyBindings = parent.LKeyBindings
        # self.keyBindings = parent.keyBindings
        # self.keyBindingsWindow = parent.keyBindingsWindow

        # add a label for each column each says "Description", "Key", "Command"
        self.keyBindingsLayout = QtWidgets.QHBoxLayout()
        self.mainLayoutKey.addLayout(self.keyBindingsLayout)

        self.desc = QtWidgets.QLabel("\t\t     Description")
        self.desc.setFixedWidth(200)
        self.desc.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        self.keyBindingsLayout.addWidget(self.desc)

        self.keyLabel = QtWidgets.QLabel("\t     Key")
        self.keyLabel.setFixedWidth(100)
        self.keyLabel.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        self.keyBindingsLayout.addWidget(self.keyLabel)

        self.commandLabel = QtWidgets.QLabel("\t\t\tCommand")
        self.commandLabel.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        self.keyBindingsLayout.addWidget(self.commandLabel)
        
        # self.setContentsMargins(10, 10, 10, 10)
        # self.keyBindingsLayout.setSize

        self.allCommandsLayout = QtWidgets.QVBoxLayout()
        self.mainLayoutKey.addLayout(self.allCommandsLayout)


        for key in self.LKeyBindings:
            self.allCommandsLayout.addWidget(CommandWidget(key, self))

        # add and "add new key binding" button
        self.buttonKey = QtWidgets.QPushButton("Add new key binding")
        self.buttonKey.clicked.connect(self.addKey)
        self.mainLayoutKey.addWidget(self.buttonKey)


    def addKey(self):
        #delete the button to add
        self.LKeyBindings.append({"key": "", "command": "", "desc": ""})
        self.allCommandsLayout.addWidget(CommandWidget(self.LKeyBindings[-1], self))

        # add the button again
        # self.mainLayoutKey.addWidget(self.buttonKey)


    def addStream(self):
        item = DragItem({"name": None, "numBytes": 2, "indexData": len(self.LDataStream)})
        self.dragLayoutData.add_item(item)

    def ChangeLayout(self):
        print("Change layout")

    def ChangeDataStream(self):
        print("Change data stream")

    def save_layout(self):
        self.parent.update_layout(self.plotsInfo)
        self.close()
        
    def new_plot(self, x, y):
        if len(self.plotsInfo) <= self.nPlots:
            self.plotsInfo.append({"name": "unknown", "yAxis": "velocidad", "x": x, "y": y, "xAxis": "time", "legend": {}, "color": (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))})
            self.widgetsPlots.append([])

        id_num = self.nPlots
            
        self.vLayout = QtWidgets.QVBoxLayout()
        self.grid.addLayout(self.vLayout, x, y)        
        self.vLayout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.vLayout.setContentsMargins(40, 40, 40, 40)

        self.hLayout = QtWidgets.QHBoxLayout()
        self.vLayout.addLayout(self.hLayout)

        self.namePlot = QtWidgets.QLineEdit()
        self.namePlot.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.namePlot.setPlaceholderText("Name of the plot")
        self.namePlot.setText(self.plotsInfo[self.nPlots]["name"])
        self.hLayout.addWidget(self.namePlot)
        self.namePlot.textChanged.connect(lambda: self.update_plots_info(id_num))
        
        self.hLayout2 = QtWidgets.QHBoxLayout()
        self.vLayout.addLayout(self.hLayout2)

        self.hLayout2.addStretch()
        self.hLayout2.addWidget(QtWidgets.QLabel("X Axis:"))
        self.YCombo = QtWidgets.QComboBox()
        self.YCombo.addItems([e["name"] for e in self.LDataStream])
        self.YCombo.setCurrentText(self.plotsInfo[self.nPlots]["yAxis"])
        self.YCombo.currentTextChanged.connect(lambda: self.update_plots_info(id_num))
        self.hLayout2.addWidget(self.YCombo)
        self.hLayout2.addStretch()

        self.hLayout3 = QtWidgets.QHBoxLayout()
        self.vLayout.addLayout(self.hLayout3)

        self.hLayout3.addStretch()
        self.hLayout3.addWidget(QtWidgets.QLabel("Y Axis:"))
        self.XCombo = QtWidgets.QComboBox()
        # self.XCombo2.addItems([e["name"] for e in self.LDataStream])
        self.XCombo.addItems([e["name"] for e in self.LDataStream])
        self.XCombo.setCurrentText("time")
        self.XCombo.currentTextChanged.connect(lambda: self.update_plots_info(id_num))
        self.hLayout3.addWidget(self.XCombo)
        self.hLayout3.addStretch()

        self.hLayout4 = QtWidgets.QHBoxLayout()
        self.vLayout.addLayout(self.hLayout4)

        # add a label that says "color:"
        self.hLayout4.addWidget(QtWidgets.QLabel("Color:"))

        # add 3 spin boxes for the rgb values
        self.colorPlot = QtWidgets.QSpinBox()
        self.colorPlot.setRange(0, 255)
        self.colorPlot.setValue(self.plotsInfo[self.nPlots]["color"][0])
        self.hLayout4.addWidget(self.colorPlot)
        self.colorPlot.valueChanged.connect(lambda: self.update_plots_info(id_num))

        self.colorPlot2 = QtWidgets.QSpinBox()
        self.colorPlot2.setRange(0, 255)
        self.colorPlot2.setValue(self.plotsInfo[self.nPlots]["color"][1])
        self.hLayout4.addWidget(self.colorPlot2)
        self.colorPlot2.valueChanged.connect(lambda: self.update_plots_info(id_num))

        self.colorPlot3 = QtWidgets.QSpinBox()
        self.colorPlot3.setRange(0, 255)
        self.colorPlot3.setValue(self.plotsInfo[self.nPlots]["color"][2])
        self.hLayout4.addWidget(self.colorPlot3)
        self.colorPlot3.valueChanged.connect(lambda: self.update_plots_info(id_num))

        self.widgetsPlots[self.nPlots] = [self.namePlot, self.YCombo, self.XCombo, self.colorPlot, self.colorPlot2, self.colorPlot3]
        self.nPlots += 1



    def update_plots_info(self, i):
        self.plotsInfo[i]["name"] = self.widgetsPlots[i][0].text()
        self.plotsInfo[i]["yAxis"] = self.widgetsPlots[i][1].currentText()
        self.plotsInfo[i]["xAxis"] = self.widgetsPlots[i][2].currentText()
        self.plotsInfo[i]["color"] = (self.widgetsPlots[i][3].value(), self.widgetsPlots[i][4].value(), self.widgetsPlots[i][5].value())
        print(self.plotsInfo[i]["color"], i)

    def create_add_button(self, x, y):
        self.buttonBot = QtWidgets.QPushButton("add plot")
        color = QtGui.QColor(123,249,135)
        self.buttonBot.setStyleSheet("background-color: {}".format(color.name()))
        self.grid.addWidget(self.buttonBot, x, 0, 1, y)
        self.buttonBot.clicked.connect(lambda: self.new_row())
        

        self.buttonRight = QtWidgets.QPushButton("add plot")
        color = QtGui.QColor(123,249,135)
        self.buttonRight.setStyleSheet("background-color: {}".format(color.name()))
        self.grid.addWidget(self.buttonRight, 0, y, x, 1)
        self.buttonRight.clicked.connect(lambda: self.new_col())
        self.buttonRight.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Expanding)


    def new_row(self):
        for i in range(self.grid.columnCount()-1):
            self.new_plot(self.grid.rowCount()-1, i)
        
        self.remove_add_buttons()
        self.create_add_button(self.grid.rowCount(), self.grid.columnCount()-1)

    
    def remove_add_buttons(self):
        self.buttonBot.deleteLater()
        self.buttonRight.deleteLater()

    def new_col(self):
        for i in range(self.grid.rowCount()-1):
            self.new_plot(i, self.grid.columnCount()-1)

        self.remove_add_buttons()
        self.create_add_button(self.grid.rowCount()-1, self.grid.columnCount())

        
class DragItem(QtWidgets.QWidget):

    def __init__(self, streamInfo = None, parent = None):
        super().__init__()

        # self.setContentsMargins(25, 5, 25, 5)
        # self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        # self.setStyleSheet("border: 1px solid black;")
        self.name = streamInfo["name"]
        self.bytes = streamInfo["numBytes"]

        self.IconItemLayout = QtWidgets.QHBoxLayout()
        self.setLayout(self.IconItemLayout)

        # add an image to the widget
        self.dragImg = QtGui.QPixmap("icons/drag.png")
        self.label = QtWidgets.QLabel()
        self.IconItemLayout.addWidget(self.label)
        self.label.setFixedSize(30, 30)
        self.label.setScaledContents(True)
        # self.label.hide()

        self.setMouseTracking(True)

        self.vLayout = QtWidgets.QVBoxLayout()      
        self.vLayout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.vLayout.setContentsMargins(20, 20, 50, 20)
        self.IconItemLayout.addLayout(self.vLayout)

        self.hLayout = QtWidgets.QHBoxLayout()
        self.vLayout.addLayout(self.hLayout)

        self.namePlot = QtWidgets.QLineEdit()
        self.namePlot.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.namePlot.setPlaceholderText("Name of data:")
        if self.name != None:
            self.namePlot.setText(self.name)
        self.hLayout.addWidget(self.namePlot)
        self.namePlot.textChanged.connect(self.update_data_stream_info)

        self.hLayout.addWidget(QtWidgets.QLabel("Nº bytes:"))
        self.numBytes = QtWidgets.QSpinBox()
        self.numBytes.setRange(1, 8)
        self.numBytes.setValue(self.bytes)
        self.numBytes.valueChanged.connect(self.update_data_stream_info)
        self.hLayout.addWidget(self.numBytes)

        self.streamInfo = streamInfo
        self.parent = parent 

        # add an x to remove the item
        self.xImg = QtGui.QPixmap("icons/x.png")
        self.xButton = QtWidgets.QPushButton()
        self.IconItemLayout.addWidget(self.xButton)
        self.setStyleSheet("QPushButton {border: none;}")
        # when pushed
        self.xButton.clicked.connect(self.deleteLater)

    def deleteLater(self):
        self.parent.LDataStream.remove(self.streamInfo)
        self.parent.dragLayoutData.removeWidget(self)
        super().deleteLater()

    def update_data_stream_info(self):
        self.streamInfo["name"] = self.namePlot.text()
        self.streamInfo["numBytes"] = self.numBytes.value()

    def enterEvent(self, e) -> None:
        self.label.setPixmap(self.dragImg)
        self.xButton.setIcon(QtGui.QIcon(self.xImg))

    def leaveEvent(self, e):
        self.label.clear()
        self.xButton.setIcon(QtGui.QIcon())

    def set_data(self, data):
        self.data = data

    def mousePressEvent(self, e):
        if e.button() == QtCore.Qt.MouseButton.LeftButton:
            self.drag_start_position = e.pos()
            self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ClosedHandCursor))

    def mouseMoveEvent(self, e):

        if e.buttons() == QtCore.Qt.MouseButton.LeftButton:
            drag = QtGui.QDrag(self)
            mime = QtCore.QMimeData()
            drag.setMimeData(mime)

            pixmap = QtGui.QPixmap(self.size())
            self.render(pixmap)
            drag.setPixmap(pixmap)

            drag.exec(QtCore.Qt.DropAction.MoveAction)

class DragWidget(QWidget):
    """
    Generic list sorting handler.
    """

    orderChanged = QtCore.pyqtSignal(list)

    def __init__(self, orientation=QtCore.Qt.Orientation.Vertical, parent = None):
        super().__init__()
        self.setAcceptDrops(True)

        # Store the orientation for drag checks later.
        self.orientation = orientation

        if self.orientation == QtCore.Qt.Orientation.Vertical:
            self.blayout = QtWidgets.QVBoxLayout()
        else:
            self.blayout = QtWidgets.QHBoxLayout()

        self.setLayout(self.blayout)

        self.LDataStream = parent.LDataStream

    def dragEnterEvent(self, e):
        e.accept()

    def dropEvent(self, e):
        pos = e.position() # why QDropEvent object has no attribute 'pos'? bc 
        widget = e.source()

        for n in range(self.blayout.count()):
            # Get the widget at each index in turn.
            w = self.blayout.itemAt(n).widget()
            if self.orientation == QtCore.Qt.Orientation.Vertical:
                # Drag drop vertically.
                drop_here = pos.y() < w.y() + w.size().height() // 2
            else:
                # Drag drop horizontally.
                drop_here = pos.x() < w.x() + w.size().width() // 2

            if drop_here:
                # We didn't drag past this widget.
                # insert to the left of it.
                self.blayout.insertWidget(n-1, widget)
                self.orderChanged.emit(self.get_item_data())
                break

        e.accept()


    def add_item(self, item):
        self.blayout.addWidget(item)


    def get_item_data(self):
        data = []
        for n in range(self.blayout.count()):
            # Get the widget at each index in turn.
            w = self.blayout.itemAt(n).widget()
            data.append(w.name)
        
        for item in self.LDataStream:
            item["indexData"] = data.index(item["name"])

        return data, self.LDataStream
    
    def removeWidget(self, widget):
        self.blayout.removeWidget(widget)

class Console(QtWidgets.QPlainTextEdit):
    def __init__(self, parent = None):
        super().__init__()

        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        self.setFixedHeight(30)
        self.setContentsMargins(10, 10, 10, 10)
        self.setPlaceholderText("Write here. . .")
        self.parent = parent

    # when the enter key is pressed, send the text to the console
    def keyPressEvent(self, e):
        if e.key() == QtCore.Qt.Key.Key_Return:
            print(self.parent)
            self.parent.update_console(self.toPlainText(), recived = False)
            self.clear()
            print("enter pressed")

        else:
            super().keyPressEvent(e)

class ScrollLabel(QtWidgets.QScrollArea):

    # constructor
    def __init__(self, always = "bot", *args, **kwargs):
        QtWidgets.QScrollArea.__init__(self, *args, **kwargs)
        # QtWidgets.QLabel.__init__()

        # making widget resizable
        self.setWidgetResizable(True)

        # making qwidget object
        content = QWidget(self)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        self.setWidget(content)


        # vertical box layout
        lay = QtWidgets.QVBoxLayout(content)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)

        # creating label
        self.label = QtWidgets.QLabel(content)

        # setting alignment to the text
        self.label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignBottom)
        self.label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        self.label.setContentsMargins(10, 10, 10, 10)
        
        self.setStyleSheet("QLabel { background-color : rgb(223, 223, 223)}")

        # making label multi-line
        self.label.setWordWrap(True)

        # adding label to the layout
        lay.addWidget(self.label)
                
        self.textstr = ""

        # make the scroll always at the bottom
        if always == "bot":
            self.verticalScrollBar().rangeChanged.connect(lambda: self.verticalScrollBar().setValue(self.verticalScrollBar().maximum()))

    def height(self):
        return self.label.height()

    # the setText method
    def setText(self, text):
        self.label.setText(text)
        self.textstr = text

    def text(self):
        return self.textstr

class CommandWidget(QtWidgets.QWidget):
    def __init__(self, keyDict, parent = None):
        super().__init__()

        self.desc = keyDict["desc"]
        self.key = keyDict["key"]
        self.command = keyDict["command"]

        self.keyDict = keyDict

        self.parent = parent

        self.setStyleSheet("border: 1px solid black;background-color: rgb(223, 223, 223);")
        self.setContentsMargins(20, 10, 20, 10)

        self.allLayout = QtWidgets.QHBoxLayout()
        self.setLayout(self.allLayout)
        self.setFixedHeight(80)

        self.allLayout2 = QtWidgets.QHBoxLayout()
        self.allLayout.addLayout(self.allLayout2)

        self.descLabel = QtWidgets.QLabel(self.desc)
        self.allLayout2.addWidget(self.descLabel)
        self.descLabel.setStyleSheet("border: 0px solid black;")
        self.descLabel.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        self.descLabel.setFixedWidth(200)
        self.descLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)
        

        # self.hLayout.addStretch()

        # self.hLayout.addWidget(QtWidgets.QLabel("Key:"))

        self.keyLabel = QtWidgets.QLabel(str(self.key))
        self.allLayout2.addWidget(self.keyLabel)

        self.keyLabel.setStyleSheet("border: 0px solid black;")
        self.keyLabel.setFixedWidth(100)
        self.keyLabel.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        self.keyLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)

        self.changeKeyButton = QtWidgets.QPushButton("Change")
        self.allLayout2.addWidget(self.changeKeyButton)
        self.changeKeyButton.clicked.connect(self.change_key)

        # self.allLayout2.addStretch()

        self.command2sendlabel = QtWidgets.QPlainTextEdit()
        # self.command2sendlabel.setReadOnly(True)
        self.command2sendlabel.setViewportMargins(5, 5, 0, 0)
        self.command2sendlabel.setPlainText(self.command)
        self.allLayout2.addWidget(self.command2sendlabel)
        self.command2sendlabel.setStyleSheet("border: 0px solid black;background-color: white;")
        self.command2sendlabel.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        # self.command2sendlabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)

        self.command2sendlabel.textChanged.connect(lambda: self.update_command(self.command2sendlabel.toPlainText()))
        self.changeKeyButton.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)

        # add the x to delete the command
        self.xImg = QtGui.QPixmap("icons/x.png")
        self.xButton = QtWidgets.QPushButton()
        self.allLayout.addWidget(self.xButton)
        self.xButton.setStyleSheet("QPushButton {border: none;}")
        # self.setStyleSheet("QPushButton {border: none;}")
        # when pushed
        self.xButton.clicked.connect(self.deleteLater)
        self.xButton.setIcon(QtGui.QIcon(self.xImg))

    def deleteLater(self):
        self.parent.LKeyBindings.remove(self.keyDict)
        self.parent.allCommandsLayout.removeWidget(self)
        super().deleteLater()

    def change_key(self):
        self.keyLabel.setText("press a key")
        self.changeKeyButton.setText("")
        self.changeKeyButton.setStyleSheet("border: 0px solid black; background-color: white;")
        # self.changeKeyButton.hide()

    def keyPressEvent(self, e):
        # print(self.command, e.text())
        if self.keyLabel.text() == "press a key":
            self.keyLabel.setText((str(e.text())).upper())
            self.keyDict["key"] = str(e.text()).upper()
            self.changeKeyButton.setStyleSheet("border: 1px solid black; background-color: rgb(223, 223, 223);")
            self.changeKeyButton.setText("Change")


    def update_command(self, text):
        self.keyDict["command"] = text
        
        print(self.parent.LKeyBindings)

class MasterPlot(QtWidgets.QWidget):
    def __init__(self, parent=None, plot=None):
        super().__init__(parent)

        self.setStyleSheet("border: 1px solid black;background-color: rgb(230, 230, 255);")
        # self.

        self.graphCheckLayout = QtWidgets.QVBoxLayout()
        self.setLayout(self.graphCheckLayout)

        # add a check box for each possible y axis
        self.checkBoxLayout2 = QtWidgets.QHBoxLayout()
        # self.checkBoxLayout2.setContentsMargins(10, 0, 10, 0)
        self.graphCheckLayout.addLayout(self.checkBoxLayout2)
        self.checkBoxLayout2.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        self.graph = Graph(self, plot)
        self.graphCheckLayout.addWidget(self.graph)

        self.graph.other_graphs = []

        for i, plot in enumerate(parent.plotsInfo):
            self.checkBox2 = QtWidgets.QCheckBox(plot["name"])
            self.checkBox2.setChecked(False)
            self.checkBox2.setStyleSheet("border: 0px solid black;")
            self.checkBoxLayout2.addWidget(self.checkBox2)
            self.checkBox2.stateChanged.connect(self.update_graph)
        
        self.LPlot = []
        for plot in parent.plotsInfo:
            self.LPlot.append([[], []])

        self.parent = parent

    def update_graph(self):
        # print the name and state of all the checkboxes
        self.what2Plot = []
        for i in range(self.checkBoxLayout2.count()):
            # self.LPlot[i]["graph"].setVisible(self.checkBoxLayout2.itemAt(i).widget().isChecked())
            print(self.checkBoxLayout2.itemAt(i).widget().text(), self.checkBoxLayout2.itemAt(i).widget().isChecked())
            # self.what2Plot[self.checkBoxLayout2.itemAt(i).widget().text()] = self.checkBoxLayout2.itemAt(i).widget().isChecked()
        
        self.graph.plt.clear()
        for i, plot in enumerate(self.parent.plotsInfo):
            try:
                if self.checkBoxLayout2.itemAt(i).widget().isChecked():
                    self.graph.plt.plot(*plot["data"].getData(), pen=pg.mkPen(color = plot["color"], width = 2), name = plot["name"])
            except:
                pass

        # add legend
        self.graph.plt.addLegend()

    def clear(self):
        self.graph.plt.clear()
        self.graph.plt.addLegend()

def main():
    app = QtWidgets.QApplication(sys.argv)
    main = MainWindow()
    main.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()


pyinstaller --windowed --add-data 