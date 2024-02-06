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
from PySide6.QtWidgets import QApplication, QFileDialog
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

        # get files from directionary 
        self.getFiles()
        self.getData()
        self.setWarningStatusByName()
        self.getPenByName()
        self.getLine() # initialize plot

        # Shown items
        if not self.loadDisplaySettings():
            self.saveDisplaySettings() # initial saving

        self.hiddenListWidget.addItems(self.hidden_list) 
        self.shownListWidget.addItems(self.shown_list) # self.shown_list is used for displaying data

        # Buttons and Menu settings
        self.hiddenToShown.clicked.connect(self.showItems) # button to move item from hidden widget to shown widget  
        self.shownToHidden.clicked.connect(self.hideItems) # button to move item from shown widget to hidden widget
        self.clearWarningText.clicked.connect(self.clearWarning) # button to clear warning message
        self.setPlotType()

        self.timer = QtCore.QTimer()
        self.timer.setInterval(300) 
        self.timer.timeout.connect(self.printStatus)
        self.timer.timeout.connect(self.printWarning)
        self.timer.timeout.connect(self.updateFiles)
        self.timer.timeout.connect(self.updateData)
        self.timer.timeout.connect(self.plot)
        self.timer.start()

### ======================================================= Log Data Files  =======================================================
    def getFiles(self):
        '''
        Get files from directory
        '''
        self.all_file_list = [file for file in os.listdir(self.file_dir) if 'log_' in file]
        self.file_list = self.all_file_list[-30:]   
        return True

    def updateFiles(self):
        '''
        update files from directory
        '''
        file = list(os.listdir(self.file_dir))[-1] 
        if file != self.all_file_list[-1]:
            # check if file format is correct
            if 'log_' in file:
                self.all_file_list.append(file)
                self.file_list[1:].append(file)
                return True

        else:
            return False
        
### ======================================================= Data Dictionary =======================================================
    def getData(self):
        '''
        Get data from logger files when monitor starts. It is not used for updating data reading
        '''
        self.all_data_by_name = {'Date': [], 'Time': [], 'Seconds': []}
        window_length = self.windowLength.value()
        
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
        
        if self.current_file != self.file_list[-1]:
            self.f.close() # when new file exist, close the previous file
            self.current_file = self.file_list[-1]
            self.f = open(self.file_dir + self.current_file, 'r')
            self.names = self.f.readline().strip('\n').split(',')
            self.names = self.convertNames(self.names) # convert names list from alias 

        self.line = self.f.readline().strip('\n')
        if self.line:
            self.all_data_by_name = self.addDataToDict(self.names, self.line.strip('\n').split(','), self.all_data_by_name)
            # self.all_x doesn't need to be updated because it is the reference to self.all_data_by_name['Seconds']
        
        if self.plot_type:
            self.livePlot()

        else:
            self.staticPlot()
        
    def livePlot(self):
        '''
        Choose to plot data in live
        it is always updating

        Modification Suggestions: might add a condition: '# if self.window_length != window_length or self.line or [change_from_static_to_live]:'
        
        '''
        window_length = self.windowLength.value()
        if self.window_length != window_length:
            self.saveDisplaySettings() # update the window length
        self.window_length = window_length
        self.data_by_name = {name: val[-1*window_length:] for name, val in self.all_data_by_name.items() if name not in ['Date', 'Time']}
        self.x = self.all_x[-1*window_length:]
        x_ticks_density = window_length//10 + 1
        self.x_ticks = [(self.x[i], self.all_data_by_name['Time'][-1*window_length:][i]) for i in range(len(self.x))][::x_ticks_density]
        self.ax.setTicks([self.x_ticks])

        return self.plot_type
    
    def staticPlot(self):
        if self.static_update_request:
            if self.selected_data_by_date:
                if self.time_is_valid: # only update plot when time is valid, 'OK' button is pressed, and file is not selected
                    index = self.static_index
                    self.data_by_name = {name: val[index[0]:index[1]] for name, val in self.all_data_by_name.items() if name not in ['Date', 'Time']}
                    self.x = self.all_x[index[0]:index[1]]
                    x_ticks_density = (index[1] - index[0])//10 + 1
                    self.x_ticks = [(self.x[i], self.all_data_by_name['Time'][index[0]:index[1]][i]) for i in range(len(self.x))][::x_ticks_density]
                    self.ax.setTicks([self.x_ticks])
                    self.static_update_request = False # just update the static figure once
                
            elif self.selected_data_by_file: # only update when time when 'OK' button is pressed and file is selected 
                self.data_by_name = {name: val for name, val in self.temp_data_by_name.items() if name not in ['Date', 'Time']}
                self.x = self.temp_data_by_name['Seconds']
                x_ticks_density = len(self.x)//10 + 1
                self.x_ticks = [(self.x[i], self.temp_data_by_name['Time'][i]) for i in range(len(self.x))][::x_ticks_density]
                self.ax.setTicks([self.x_ticks])
                self.static_update_request = False # just update the static figure once

        return self.plot_type
    
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

            if len(d[name]) > 100000:
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
            self.line_by_name[name] = self.graphWidget.plot([], 
                                                           [],
                                                           name = name, 
                                                           pen = pen,
                                                           label = self.x_ticks
                                                           ) # initialize data plotting and get line for each name

        self.graphWidget.setBackground("w")
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
            self.pen_by_name[name] = pg.mkPen(color = color, dash = dash, width = 2) # set to pen by name
        
        return True

### ================================================ Set Static or Live plot ===============================================
    def setPlotType(self):
        '''
        The setToStatic button will set the static plot
        The setToLive button will set the live plot
        By default, the plot is live
        '''
        self.plot_type = True # plot is live 
        self.setToStatic.clicked.connect(self.setStatic) # ok button to set static by date
        self.setToLive.clicked.connect(self.setLive) # reset button to set plot back to live
        self.loadFile.triggered.connect(self.loadStaticFile) # menu bar for file selection
    
    def setStatic(self):
        '''
        Set plot type to static if the input is valid, or give the error and set plot type back to live
        '''
        self.getSelectedDataRangeByDate()
        self.selected_data_by_file = False
        self.selected_data_by_date = True

    def setLive(self):
        self.plot_type = True
        self.selected_data_by_file = False
        self.selected_data_by_date = False
        self.static_update_request = False

    
### =============================================== Static Plot by File Name ===============================================
    def loadStaticFile(self):
        '''
        Load file from menu bar
        '''
        filename, ext = QFileDialog.getOpenFileName(caption = 'Import File', dir = self.file_dir, filter = '*.csv')
        if filename and 'log_': # if a file is selected and file is valid
            try:
                self.temp_data_by_name = {'Date': [], 'Time': [], 'Seconds': []}
                f = open(filename, 'r')
                names = f.readline().strip('\n').split(',')
                names = self.convertNames(names)
                for data in csv.reader(f, delimiter = ','):
                    self.temp_data_by_name = self.addDataToDict(names, data, self.temp_data_by_name)
                f.close()
                self.plot_type = False
                self.static_update_request = True
                self.selected_data_by_file = True
                self.selected_data_by_date = False

                return True
            except:
                self.warningText.appendPlainText('The selected file is invalid or compromised.')

        self.static_update_request = False
        self.selected_data_by_file = False
        return False
    
### ================================================= Static Plot by Date ==================================================
    def getSelectedDataRangeByDate(self):
        '''
        Use formatted input dates to calculated the index range, and give the index for staticPlot function 
        '''
        self.time_is_valid = True # initial True and force to False if input time is not valid. This value is used for making a new static plot
        
        # Get time in seconds in a list [start_time, end_time]

        # Value explains 
        # False: the incorrect format that will give the warning message, and the plot will not be static until the input is correct
        # None: the not given value, eg. [1, None] means 1 s to the moment when user click ok and plot is static
        # seconds (int): the seconds converted from formatted input. eg. [500, 1500] means 500 s to 1500 s

        # The format is yyyymmddHHMM, where yyyy is complete year, mm is complete month, dd is complete day, HH is hour in 24 hour format, and MM is minutes
        # Hours and minutes are optional, the rest are required
        # If the Input and string 'yyyymmddHHMM' or empty, it will assign None to list

        self.static_time_range = [self.returnSeconds(self.startTime.text().strip()), self.returnSeconds(self.endTime.text().strip())] 

        if self.static_time_range[0] == False or self.static_time_range[1] == False: # input time format is incorrect
            self.warningText.appendPlainText('Static input time is not valid')
            self.time_is_valid = False 

        else:
            # convert seconds to the index of nearest value in self.all_x (all data x-axis)
            self.static_index = [self.binary_search(self.all_x, self.static_time_range[0]), self.binary_search(self.all_x, self.static_time_range[1])]
            
            if not self.static_index[0]: # force None to 0 for start time if no input is given
                self.static_index[0] = 0
            if not self.static_index[1]: # force None to the last index in current data x-axis for end time if no input is given
                self.static_index[1] = len(self.all_x) - 1

            if self.static_index[1] == 0: # the end time error which leads to single points
                self.warningText.appendPlainText('Static input time is not valid: end time is earlier than the logging start time')
                self.time_is_valid = False

            if self.static_index[0] >= self.static_index[1]: # the end time error which leads to indexing issue
                self.warningText.appendPlainText('Static input time is not valid: end time should be later than start time')
                self.time_is_valid = False            
                    
            self.plot_type = False # make plot type to static
            self.static_update_request = True # only update static data when 'OK' button is pressed.

        return True

    def returnSeconds(self, time: str):
        '''
        Check if a time string is valid in format yyyymmdd or yyyymmddHH or yyyymmddHHMM or empty and return seconds
        '''

        # check empty
        if time == 'yyyymmddHHMM' or not time: # by default or not given
            return None
        
        # check length:
        if len(time) not in [len('yyyymmdd'), len('yyyymmddHH'), len('yyyymmddHHMM')]: # incorrect length
            return False
        
        if len(time) == len('yyyymmdd'): 
            try:
                datetime_object = datetime.strptime(time, '%Y%m%d')
            except:
                return False

        elif len(time) == len('yyyymmddHH'):
            try:
                datetime_object = datetime.strptime(time, '%Y%m%d%H')
            except:
                return False
        
        elif len(time) == len('yyyymmddHHMM'):
            try:
                datetime_object = datetime.strptime(time, '%Y%m%d%H%M')
            except:
                return False
        else:
            return False

        delta = datetime_object - datetime(1970,1,1) # use 1970/1/1 as reference 

        return int(delta.total_seconds())    
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
    def saveDisplaySettings(self):
        '''
        This will save hidden and shown items and window length in the file called 'display_settings.txt'
        format:
        1st line: 'hidden[, item1][, item2]....'
        2nd line: 'shown[, item3][, item4]....'
        3rd line: 'window length,[window_length]'
        '''

        hidden_list = ['hidden']
        hidden_list.extend(self.hidden_list)
        hidden_string = ','.join(hidden_list) + '\n'
        shown_list = ['shown']
        shown_list.extend(self.shown_list)
        shown_string = ','.join(shown_list) + '\n'
        window_length_string = 'window length,' + self.windowLength.text()
        f = open(self.file_dir + 'display_settings.txt', 'w')
        f.write(hidden_string + shown_string + window_length_string)
        f.close()

        return True
    
    def loadDisplaySettings(self):
        '''
        This will load hidden item and shown item settings
        return True if loading successfully, else False
        '''
        if 'display_settings.txt' in os.listdir(self.file_dir):
            self.hidden_list = []
            self.shown_list = []
            f = open(self.file_dir + 'display_settings.txt', 'r')
            hidden_list = f.readline().strip('\n').split(',')[1:] # remove 'hidden' 
            shown_list = f.readline().strip('\n').split(',')[1:] # remove 'shown'
            window_length = f.readline().strip('\n').split(',')[1] # get window length in str
            self.windowLength.setValue(int(window_length))
            f.close()
            for name in self.all_names:
                if name in shown_list: 
                    self.shown_list.append(name)
                else: # in the case that the item is hidden or hasn't been set up
                    self.hidden_list.append(name)
            return True
        else: # if the file not exist, copy all names to hidden list
            self.hidden_list = self.all_names.copy() 
            self.shown_list = []
            return False        

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
        
        self.saveDisplaySettings() # save current setting
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

        self.saveDisplaySettings() # save current setting
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
                    if self.all_data_by_name[name][-1] in [_np.nan] or 'pyB12logger_running.exe' not in current_exe: # check the last data point, please refer to np.nan equality
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
        for name in self.all_data_by_name:
            
            if name not in ['Date', 'Time', 'Seconds']:
                warning_status = False
                minimum = self.min_by_name[name]
                maximum = self.max_by_name[name]
                static = self.static_by_name[name]

                if static:
                    if self.all_data_by_name[name][-1] != static:
                        warning_status = True
                
                if minimum:
                    if self.all_data_by_name[name][-1] < minimum:
                        warning_status = True
            
                if maximum:
                    if self.all_data_by_name[name][-1] > maximum:
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
        for name in self.data_by_name:
            if name not in ['Date', 'Time', 'Seconds']:
                self.warning_status_by_name[name] = False
        self.warningText.clear()

        return True
    
### ======================================================= Internal Used Functions ====================================================
    def binary_search(self, array, value):
        '''
        It is used for searching the index of closest value in a given array. The method is binary search, faster in large array

        Please be notified that the array has been sorted already. The return is modified to get the index

        Reference: https://www.geeksforgeeks.org/find-closest-number-array/
        '''
        if value == None:
            return None
        
        n = len(array)
        if value < array[0]:
            return 0
        elif value > array[-1]:
            return n - 1
        
        i = 0 # lower limit
        j = n # upper limit

        while (i < j):
            mid = (i + j) //2

            if array[mid] == value:
                return mid
            
            if value < array[mid]: # in the case value is on the left side of array
                if (mid > 0 and value > array[mid-1]): # array[mid] > value > array[mid - 1]  
                    return self.get_closest(mid-1, mid, value, array)
                
                j = mid # move upper limit to mid

            else: # in the case value is on the right side of array
                if (mid < n -1 and value < array[mid + 1]):  # array[mid] < value < array[mid + 1]  
                    return self.get_closest(1, mid+1, value, array)
                
                i = mid + 1 # move lower limit to mid

        return mid

                
    def get_closest(self, index1, index2, target, array):
        if (target - array[index1] >= array[index2] - target):
            return index2
        else:
            return index1

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()