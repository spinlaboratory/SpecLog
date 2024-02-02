"""
Monitor.py: plotting data in real-time or static

1. Read log files
2. Plot live or static data
3. Show warning information

It use PyQt 6, there are some terms you need to know before modifying this script

1. 'name': the identification of a curve, and the key word to call the curve line and item. It can be the alias if the alias presents
2. 'item': the curve items, e.g Legend class from PyQt 6
3. 'line': the data line for plotting, it is a class from PyQt 6

Author: Yen-Chun Huang

Company: Bridge 12 Technologies, Inc
"""

import os 
import sys
import csv
from datetime import datetime
import numpy as _np
from PySide6.QtWidgets import QApplication
from PyQt6 import QtCore
import pyqtgraph as pg
from .loggerConfig import *
from .debugLog import *

dir_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
uiFile = dir_path + '/ui/plotting.ui'
uiclass, baseclass = pg.Qt.loadUiType(uiFile)

class MainWindow(uiclass, baseclass):
    def __init__(self, config_file: str = None):
        super().__init__()
        self.setupUi(self)
        # configuration file
        config = loggerConfig(config_file)
        self.settings = config.settings
        self.device_config = config.devices
        self.file_dir = self.settings['log_folder_location'] + '/B12TLOG/'
        self.commands = config.commands
        self.getAlias()
        self.getWarningValueByName()
        self.status_string = ''

        # debug log
        self.debugLogger = debugLog(config_file).logger     
    
        self.getData()
        self.setWarningStatusByName()
        self.getPenByName()
        self.getLine() # initialize plot

        self.hidden_list = self.all_names.copy()
        self.shown_list = []

        self.hiddenListWidget.addItems(self.hidden_list)
        self.hiddenToShown.clicked.connect(self.showItems) # button to move item from hidden widget to shown widget  
        self.shownToHidden.clicked.connect(self.hideItems) # button to move item from shown widget to hidden widget
        self.clearWarningText.clicked.connect(self.clearWarning) # button to clear warning message 
      
        self.timer = QtCore.QTimer()
        self.timer.setInterval(300) 
        self.timer.timeout.connect(self.printStatus)
        self.timer.timeout.connect(self.printWarning)
        self.timer.timeout.connect(self.updateData)
        self.timer.timeout.connect(self.plot)
        self.timer.start()


### ======================================================= Data Dictionary =======================================================
    def getData(self):
        '''
        Get data from logger files when monitor starts. It is not used for updating data reading
        '''
        self.all_data_by_name = {'Date': [], 'Time': [], 'Seconds': []}
        window_length = int(self.windowLength.text()) 
        self.file_list = [file for file in os.listdir(self.file_dir) if 'log_' in file][-10:]
        
        if not self.file_list: 
            self.debugLogger.error('Logged Data Not Found')
            return False

        # When the monitor starts or a new file presents
        for file in self.file_list:
            f = open(self.file_dir + file, 'r')
            names = f.readline().strip('\n').split(',')
            if names[0]:
                names = self.convertNames(names) # at this point, the name is used locally
                for data in csv.reader(f, delimiter = ','):
                    self.all_data_by_name = self.addDataToDict(names, data, self.all_data_by_name)
            
            if file != self.file_list[-1]: # close the file
                f.close()
            else: # leave the current file open for further reading
                # after reading all data, put the local names list to global
                self.current_file = file
                self.f = f
                self.names = names 
                self.window_length = window_length

            # for initial data dictionary
            self.all_names = [name for name in self.all_data_by_name.keys() if name not in ['Date', 'Time', 'Seconds']] # get list of data name except Date, Time and Seconds
            self.all_x = self.all_data_by_name['Seconds']
            self.data_by_name = {name: val[-1*window_length:] for name, val in self.all_data_by_name.items() if name not in ['Date', 'Time', 'Seconds']}
            self.x = self.all_x[-1* window_length:]
            x_ticks_density = window_length//10
            self.x_ticks = [(self.x[i], self.all_data_by_name['Time'][-1*window_length:][i]) for i in range(len(self.x))][::x_ticks_density]
            
    def updateData(self):
        '''
        Update data when new line appears or new file presents

        This is the data checking processing and used for live data
        '''
        window_length = int(self.windowLength.text())
        self.file_list = [file for file in os.listdir(self.file_dir) if 'log_' in file][-10:]
        if self.current_file != self.file_list[-1]:
            self.f.close() # when new file exist, close the previous file
            self.current_file = self.file_list[-1]
            self.f = open(self.file_dir + self.current_file, 'r')
            self.names = self.f.readline().strip('\n').split(',')
            self.names = self.convertNames(self.names) # convert names list from alias 

        line = self.f.readline().strip('\n')
        if line:
            self.all_data_by_name = self.addDataToDict(self.names, line.strip('\n').split(','), self.all_data_by_name)
            # self.all_x doesn't need to be updated because it is the reference to self.all_data_by_name['Seconds']
        
        if self.window_length != window_length or line:
            self.window_length = window_length
            self.data_by_name = {name: val[-1*window_length:] for name, val in self.all_data_by_name.items() if name not in ['Date', 'Time']}
            self.x = self.all_x[-1*window_length:]
            x_ticks_density = window_length//10
            self.x_ticks = [(self.x[i], self.all_data_by_name['Time'][-1*window_length:][i]) for i in range(len(self.x))][::x_ticks_density]
            self.ax.setTicks([self.x_ticks])
    
    def addDataToDict(self, names: list, data, d: dict):
        '''
        Add data to target dictionary based on name
        
        Args:
            names (list): list of key (name) to add to target dictionary
            data: csv read data
            d (dict): target dictionary to add data

        Return:
            d (dict): target dictionary with added data
        '''
        
        # convert name from alias:
        # temporary dictionary
        td = {name.strip(): val.strip() for name, val in zip(names, data)}
        # create empty list if key not exists in dictionary
        for name in td.keys():
            if name not in d.keys():
                d[name] = [_np.nan] * len(d['Date'])

        for name in d.keys():
            if name in ['Date', 'Time']:
                val = td[name].strip()
            elif name == 'Seconds':
                val = self.getXAxisFromTime(td['Date'].strip(), td['Time'].strip())
            elif name in td and td[name] != 'nan':
                try:
                    val = float(td[name])
                except:
                    val = int(td[name], base = 16) # convert 16-bit hex value 
            elif name:
                val = _np.nan

            if len(d[name]) > 5000:
                del d[name][0]
            
            d[name].append(val)
        del td # release memory
        return d  
    
### ======================================================= X-axis Processing =======================================================

    def getXAxisFromTime(self, date: str, time: str):
        '''
        Convert Date and Time string to the seconds from 1970/1/1
        
        Use seconds as X axis

        Args: 
            date (str): in format %Y-%m-%d
            time (str): in format %H:%M:%S
        
        Returns:
            seconds (int): seconds from 1970/1/1
        '''

        string = date + ' ' + time # in format '%Y-%m-%d %H:%M:%S'
        datetime_object = datetime.strptime(string, '%Y-%m-%d %H:%M:%S')
        delta = datetime_object - datetime(1970,1,1)

        return int(delta.total_seconds())
        
    def getLine(self):
        '''
        Initialize plotting and get line based on name
        '''
        self.line_by_name = {} # {name: line}
        for name, data in self.data_by_name.items(): # loop all names
            pen = self.pen_by_name[name] # set pen
            self.line_by_name[name] = self.graphWidget.plot(self.x, 
                                                           data,
                                                           name = name, 
                                                           pen = pen,
                                                           label = self.x_ticks
                                                           ) # initialize data plotting and get line for each name

        # styles = {"color": "red", "font-size": "18px"}
        self.graphWidget.setBackground("w")
        # self.graphWidget.setLabel('bottom', 'Time (min)', **styles)
        self.graphWidget.showGrid(x = True, y = True)
        self.legend = self.graphWidget.addLegend()
        self.ax = self.graphWidget.getAxis('bottom')
        self.ax.setTicks([self.x_ticks])

        return True
### ======================================================= Drawing Pen =======================================================
    def getPenByName(self):
        '''
        Set curve color and line style to pen

        Idea: loop color list. If color is the same, use different dash line
        1. loop the color list. e.g. 1%4 = 1 and 5%4 = 1, so the second and fifth element use the same color 
        2. loop the dash list. e.g. 1//4%4 = 0 and 5//4%4 = 1, so the second element doesn't have dash line but fifth element use dash line [16, 16]

        '''
        self.pen_by_name = {} #{name: pen}

        color_list_loop = ['#F37021', '#46812B', '#67AE3E', '#4D4D4F'] # can be extend
        dash_list_loop = [None, [16, 16], [8, 8], [4, 4]] # can be extend

        for index, name in enumerate(self.all_names):
            color = color_list_loop[index%len(color_list_loop)] # loop color list
            dash = dash_list_loop[index//len(color_list_loop)%len(dash_list_loop)] # loop dash line list if same color
            self.pen_by_name[name] = pg.mkPen(color = color, dash = dash) # set to pen by name
        
        return True

### ======================================================= Plotting =======================================================
    def plot(self):
        '''
        Plotting data 
        '''
        for name in self.all_names: 
            if name in self.shown_list: # plot line in shown widget

                if not self.legend.getLabel(self.line_by_name[name]): # if not legend, add legend 
                    self.legend.addItem(self.line_by_name[name], name) 

                self.line_by_name[name].setData(self.x, self.data_by_name[name])       
            else: # hide line in hidden widget
                self.legend.removeItem(name) # remove legend
                self.line_by_name[name].setData([], []) # display empty line

### ======================================================= List Widget Interaction =======================================================
    def hideItems(self):
        '''
        Move items from shown list to hidden list, and from shown widget to hidden widget
        '''
        selected = self.shownListWidget.selectedItems() # multi selection
        for item in selected:
            row = self.shownListWidget.row(item) # get row
            self.hiddenListWidget.addItem(self.shownListWidget.takeItem(row)) # remove item from shown widget to hidden widget 
            self.shown_list.remove(item.text()) # add the item from hidden list
            self.hidden_list.append(item.text()) # remove the item to the shown list
        
        return True

    def showItems(self):
        '''
        Move items from hidden list to shown list, and from hidden widget to shown widget
        '''

        selected = self.hiddenListWidget.selectedItems() # multi selection
        for item in selected:
            row = self.hiddenListWidget.row(item) # get row
            self.shownListWidget.addItem(self.hiddenListWidget.takeItem(row)) # remove item from hidden widget to shown widget 
            self.hidden_list.remove(item.text()) # remove the item from hidden list
            self.shown_list.append(item.text()) # add the item to the shown list

        return True

### =======================================================Alias Related=======================================================
    def getAlias(self, name: str = None):
        '''
        Get alias and assign it to the name

        Args:
            name (str, option): if name is provided, return the alias, otherwise get alias by name dict

        Returns:
            alias (str): an alias
        '''
        if not name: # generate alias dictionary
            self.alias_by_name = {} # {name: alias}
            for device in self.device_config:
                for name, info in self.commands[device].items():
                    if info['alias']:
                        self.alias_by_name[name] = info['alias']
                    else:
                        self.alias_by_name[name] = name

            return True
        else:
            return self.alias_by_name[name] # this is the special case that the name is actually variable name 
    
    def convertNames(self, names: list):
        '''
        Convert a list of name to a list of alias
        Args:
            Names (list): a list of name
        
        Returns:
            Names (list): a list of name from alias
        '''

        for i in range(len(names)):
            if names[i].strip() in ['Date', 'Time', 'Seconds']: # not consider x-axis labels
                pass
            else:
                names[i] = self.getAlias(names[i].strip()) # strip white space in case
            
        return names

### =======================================================Status Related=======================================================
    def printStatus(self):
        '''
        Print the status of logger and devices
        '''
        
        current_exe = os.popen('wmic process get description').read().strip().replace(' ', '').split('\n\n')
        if 'pyB12logger_running.exe' in current_exe:
            string = 'Logger Enable\n'
        else:
            string = 'Logger Disable\n'
        
        for device in self.device_config:
            if self.device_config[device]['device_status'] == False:
                string += device + ' Disable\n'
            else:
                temp = device + ' Enable\n'
                for name in self.commands[device]:
                    name = self.getAlias(name)
                    if self.data_by_name[name][-1] in [_np.nan]: # check the last data point, please refer to np.nan equality
                        temp = device + ' Disable\n'
                        break
                string += temp

        if self.status_string != string:
            self.status_string = string
            self.textIndicator.clear()
            self.textIndicator.appendPlainText(self.status_string)

### ======================================================= Warning Related =======================================================
    def getWarningValueByName(self):
        '''
        Get warning values
        '''
        self.min_by_name = {}
        self.max_by_name = {}
        self.static_by_name = {}
        for device in self.device_config:
            for name, info in self.commands[device].items():
                name = self.getAlias(name) # convert to alias
                self.min_by_name[name] = info['min'] 
                self.max_by_name[name] = info['max']
                self.static_by_name[name] = info['static']

    def setWarningStatusByName(self):
        '''
        Set warning status to True if the warning has been displayed
        '''

        self.warning_status_by_name = {name: False for name in self.data_by_name}

                
    def printWarning(self):
        '''
        Print warning if the value is not in range
        '''
        for name in self.data_by_name:
            
            if name not in ['Date', 'Time', 'Seconds']:
                warning_status = False
                minimum = self.min_by_name[name]
                maximum = self.max_by_name[name]
                static = self.static_by_name[name]

                
                if static:
                    if self.data_by_name[name][-1] != static:
                        warning_status = True
                
                if minimum:
                    if self.data_by_name[name][-1] > minimum:
                        warning_status = True
            
                if maximum:
                    if self.data_by_name[name][-1] < maximum:
                        warning_status = True

                if warning_status and not self.warning_status_by_name[name]: # warning begins
                    current_time = self.all_data_by_name['Date'][-1] + ' ' + self.all_data_by_name['Time'][-1]
                    self.warning_status_by_name[name] = True
                    string = current_time + ': ' + name + ' error!!!'
                    self.warningText.appendPlainText(string)

                elif not warning_status and self.warning_status_by_name[name]: # warning ends
                    current_time = self.all_data_by_name['Date'][-1] + ' ' + self.all_data_by_name['Time'][-1]
                    self.warning_status_by_name[name] = False
                    string = current_time + ': ' + name + ' error clean!!!'
                    self.warningText.appendPlainText(string)
        
    def clearWarning(self):
        '''
        Clear warning information
        '''

        self.warningText.clear()

        return True

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()