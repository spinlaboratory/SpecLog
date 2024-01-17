"""
pyB12LOG: The logging program for instrumentations

monitor.py: plotting data in real-time or static

Author: Yen-Chun Huang

Company: Bridge 12 Technologies, Inc
"""

import os
import subprocess
import numpy as _np
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import csv
from collections import Counter
from matplotlib.widgets import Button, RadioButtons, CheckButtons, Slider, TextBox
from .config.config import CONFIG
from configparser import ConfigParser

class monitor:
    def __init__(self, number_of_file = 10):
        deviceConfigDirHome = CONFIG['CONFIG']['log_folder_location'][1:-1]
        self.logDir = deviceConfigDirHome + '/B12TLOG/'

        self.deviceConfigDirFile = deviceConfigDirHome +'/B12TLOG_Config/device_config.cfg'
        self.deviceConfig = ConfigParser()

        self.commandConfigFile = deviceConfigDirHome +'/B12TLOG_Config/command.cfg'
        self.commandConfig = ConfigParser()

        self.header = None
        self.hashDict = {}
        self.log_list = os.listdir(self.logDir)
        self.f = None
        self.log_index = 0
        self.current_log = None
        self.update_figure = True
        self.static_figure = False
        # self.update_visibility = False
        self.selected_file = False
        self.selected_date = False
        self.current_selected_file = None
        self.number_of_file = number_of_file

        self.last_device_dict = {}
        self._update_status()
        self.logRead()
        self.max_pnts = len(self.hashDict['Date'])
        self.plot()

    def logRead(self):
        del self.log_list # release memory
        self.log_list = [log for log in os.listdir(self.logDir) if 'log_' in log][-1*self.number_of_file:]
        while self.current_log != self.log_list[-1]: 
            if self.log_index < self.number_of_file:
                self.current_log = self.log_list[self.log_index] # update current log
            else:
                self.current_log = self.log_list[-1]
            self.f = open(self.logDir + self.current_log, 'r')
            self.keys = self.f.readline().strip('\n').split(',')
            self.hashDict = self._hashDict_values_length_keeper(self.keys, self.hashDict, 'Date')
            for data in csv.reader(self.f, delimiter = ','): # O(1)
                self.hashDict = self._hashDict_append(self.keys, data, self.hashDict) 
            self.log_index += 1

        self.items = list(self.hashDict.keys())[2:] # get all headers/items
    
    def plot(self):
        self.time_length = len(self.hashDict['Time'])
        if self.time_length < self.max_pnts: 
            self.pnts = self.time_length//2
        else:
            self.pnts = self.max_pnts//2
        
        x, x_ticks, x_label, ys = self._get_plot_values(self.hashDict, self.pnts, self.items)

        self.color_lists = ['#F37021', '#46812B', '#4D4D4F', '#A7A9AC'] * (len(self.items) // 4 + 1) 

        # init figure
        plt.ion()
        fig = plt.figure(1, figsize = (16,12))
        plt.subplots_adjust(left=0.25, bottom = 0.25)
        ax = fig.add_subplot(1,1,1)
        self.visibility_by_label = {}
        self.lines_by_label = {}
        line_colors = []
        self.line_weight = {}
        self.update_require = 0

        # initial plotting
        for index, (y, color) in enumerate(zip(ys, self.color_lists)):
            l, = ax.plot(x, y, color, label = self.items[index])
            self.lines_by_label[l.get_label()] = l
            line_colors.append(color)
            self.line_weight[l.get_label()] = 'bold'
            self.visibility_by_label[l.get_label()] = l.get_visible() 
        ax.set_xticks(x_ticks)
        ax.set_xticklabels(x_label)
        ax.grid(ls = ':')
        ax.set_xlabel('Time')

        # check buttons for showing curves
        rax = fig.add_axes([0.01, 0.4, 0.2, 0.15])
        check = CheckButtons(
            ax=rax,
            labels=self.lines_by_label.keys(),
            actives=[l.get_visible() for l in self.lines_by_label.values()],
            label_props={'color': line_colors, 'fontweight': list(self.line_weight.values())},
            frame_props={'edgecolor': line_colors},
            check_props={'facecolor': line_colors},
        )
        
        def callback(label):
            self.visibility_by_label[label] = not self.visibility_by_label[label]
            self.line_weight[label] = 'light' if self.visibility_by_label[label] == False else 'bold'
            # self.update_visibility = True
            self.update_figure = True

            if self.static_figure == True:
                self.ln = self.lines_by_label[label]
                self.ln.set_visible(not self.ln.get_visible())
                fig.canvas.draw_idle()

        check.on_clicked(callback)

        # check buttons for showing status of devices
        rax_device = fig.add_axes([0.01, 0.8, 0.2, 0.15])
        check_device = CheckButtons(
            ax = rax_device,
            labels= list(self.current_device_dict.keys()),
            actives = list(self.current_device_dict.values()),
            # label_props={'color': line_colors},
            # frame_props={'edgecolor': line_colors},
            # check_props={'facecolor': line_colors},
        )

        def callback_device(label):
            self.current_device_dict[label] = not self.current_device_dict[label]
            if label != 'Logger':
                address = self.address_dict[label]
                self.deviceConfig[address]['device_status'] = str(self.current_device_dict[label])
            elif label == 'Logger':
                current_exe = os.popen('wmic process get description').read().strip().replace(' ', '').split('\n\n')
                hashDict = Counter(current_exe)
                if 'pyB12logger_running.exe' not in hashDict and self.current_device_dict[label] == True:
                    subprocess.Popen('pyB12logger_running.exe', creationflags = subprocess.CREATE_NO_WINDOW)
                    print('pyB12logger started')
                elif 'pyB12logger_running.exe' in hashDict and self.current_device_dict[label] == False:
                    os.system("taskkill /im pyB12logger_running.exe /F")
                    print('pyB12logger stopped')
            
            with open(self.deviceConfigDirFile, 'w') as conf: ## Change configuration file
                self.deviceConfig.write(conf)

        check_device.on_clicked(callback_device)

        # slider bar and reset for zooming
        self.slider_pnts = int(self.max_pnts / 2)
        slider_ax = fig.add_axes([0.25, 0.15, 0.65, 0.03], facecolor = '#F37021')
        sTime = Slider(
            ax=slider_ax,
            label='Zoom',
            valmin= 2,
            valmax = self.max_pnts,
            valinit = int(self.max_pnts / 2),
        )
        sTime.valtext.set_visible(False)
        def zoom_update(val):
            self.slider_pnts = int(sTime.val)
            self.update_figure = True
            self.static_figure = False
            self.selected_file = False
            self.selected_date = False
        sTime.on_changed(zoom_update)

        # slider bar and reset for selecting files
        file_slider_ax = fig.add_axes([0.25, 0.10, 0.65, 0.03], facecolor = '#F37021')
        sFile = Slider(
            ax=file_slider_ax,
            label='Files',
            valmin = 0,
            valmax = self.number_of_file,
            valinit = 0,
        )
        sFile.valtext.set_visible(False)

        def file_update(val):
            self.selected_file_reverse_index = int(sFile.val)
            self.selected_file = True if self.selected_file_reverse_index else False
            self.static_figure = False # it is false because the update is required, and it will be set to True once update is finished
            self.update_figure = True
        sFile.on_changed(file_update)

        # textbox for plotting specific range
        axbox = fig.add_axes([0.05, 0.1, 0.15, 0.075])
        text_box = TextBox(axbox, "Date\n", textalignment="center")

        def submit(date):
            self.dict_by_date = self._logs_by_date(date)
            self.selected_date = True
            self.update_figure = True
            self.static_figure = False # it is false because the update is required, and it will be set to True once update is finished

        text_box.on_submit(submit)

        ## reset
        resetax = plt.axes([0.92, 0.15, 0.03, 0.03])
        reset_button = Button(resetax, 'Reset', color='lightgoldenrodyellow', hovercolor='0.975')

        def reset(event):
            sTime.reset()
            sFile.reset()
            self.update_figure = True
            self.static_figure = False
            self.selected_file = False
            self.selected_date = False
        reset_button.on_clicked(reset)

        fig.show() # inital plotting
        while(plt.fignum_exists(1)):
            self._update_status()
            self._update_device_check_button(check_device)
            # print({'fontweight': list(self.line_weight.values())})
            check.set_label_props({'fontweight': list(self.line_weight.values())})
            self.logRead() # check if new log creates
            # where = self.f.tell() # (option) f current position of pointer
            line = self.f.readline().strip('\n')
            if line: # if there is non-empty new line
                self.hashDict = self._hashDict_append(self.keys, line.strip('\n').split(','), self.hashDict)
                self.time_length = len(self.hashDict['Time'])
                self.update_figure = True        

            if self.update_figure and not self.static_figure: 
                if not self.selected_file and not self.selected_date:
                # real-time figure
                ## updates plotting information       
                    self.pnts = self.time_length if self.time_length < self.max_pnts else self.max_pnts
                    self.pnts = min(self.slider_pnts, self.pnts)

                    x, x_ticks, x_label, ys = self._get_plot_values(self.hashDict, self.pnts, self.items)
                    
                # plot static
                elif self.selected_file:
                    if self.selected_file_reverse_index > len(self.log_list): # avoid out of range
                        self.selected_file_reverse_index = len(self.log_list)
                    self.current_selected_file = self.log_list[-1 * self.selected_file_reverse_index] # self.log_list is constantly being updated
                    self.selected_file_dict = {key: [] for key in self.hashDict.keys()}
                    file = open(self.logDir + self.current_selected_file, 'r')
                    file.readline() # skip 1st line 
                    self.file_length = 0
                    for data in csv.reader(file, delimiter = ','): # O(1)
                        self.selected_file_dict = self._hashDict_append(self.keys, data, self.selected_file_dict) # O(n)
                        self.file_length += 1                   
                    
                    x, x_ticks, x_label, ys = self._get_plot_values(self.selected_file_dict, self.file_length, self.items, ticks = 10)
                    self.static_figure = True # update figure only once

                elif self.selected_date:
                    x, x_ticks, x_label, ys = self._get_plot_values(self.dict_by_date, len(self.dict_by_date['Date' ]), self.items, ticks = 10)
                    self.static_figure = True # update figure only once

                # self.f.seek(where) # (option) find current pointer
                ax.clear() # clean figure
                del self.lines_by_label # release memory
                self.lines_by_label = {}
                for index, (y, color) in enumerate(zip(ys, self.color_lists)):
                    label = self.items[index]
                    if self.visibility_by_label[label]:
                        l, = ax.plot(x, y, color, label = label)
                    else:
                        l, = ax.plot([], [], label = label)
                    l.set_visible(self.visibility_by_label[label])
                    self.lines_by_label[l.get_label()] = l
                ax.set_xticks(x_ticks)
                ax.set_xticklabels(x_label)
                ax.set_xlabel('Time')
                ax.grid(ls = ':')
                if self.selected_file:
                    ax.set_title(self.current_selected_file)
                elif self.selected_date:
                    ax.set_title('pyB12monitor\n%s - %s' %(self.dict_by_date['Date'][0] + ' ' + self.dict_by_date['Time'][0], self.dict_by_date['Date'][-1] + ' ' + self.dict_by_date['Time'][-1]))
                else:
                    ax.set_title('pyB12monitor')

                self.update_figure = False
                # self.update_visibility = False

                del x_ticks
                del x_label
                del ys

            fig.canvas.flush_events() # showing new plot by flushing event

    def _hashDict_values_length_keeper(self, keys, d, checker):
        '''
        This function is to make sure all lists in the dictionary have same length
        Args:
            keys: a new list of dictionary key
            d: current dictionary
            checker: the key in the dictionary to check the length of all lists

        Return:
            d: the dictionary that contains same length of lists
        '''
        for key in keys:
            key = key.strip()
            if key not in d: # if new item is found
                d[key] = [0] * len(d[checker]) if d else [] # take care if new item appears with old log, then put all 0 to the front
        return d

    def _hashDict_append(self, keys, data, d, memory_reduce = True):
        '''
        This function is to read file from csv and add data to dictionary
        Args:
            items: the items in the current file
            data: a new data from current file
            d: existing dictionary

        Return:
            d: the appended dictionary

        '''
        td = {key.strip(): val.strip() for key, val in zip(keys, data)}
        for key in d.keys():
            if key == 'Date' or key == 'Time':
                val = td[key].strip()
            elif key in td and td[key].strip() != 'nan':
                try:
                    val = float(td[key])
                except:
                    val = int(td[key], base = 16) # convert 16-bit hex value
            else:
                val = _np.nan
            
            if len(d[key]) > 2000 and memory_reduce:
                del d[key][0] 
            d[key].append(val)
        return d
    
    def _get_plot_values(self, dict, pnts, items, ticks = 5):
        '''
        Arg: 
            dict: the dictionary of data
            pnts: number of pnts to plot
            items: the items in the dictionary to plot (exclude time and date)
            ticks: the number of ticks for plotting

        return:
            x: a list from 1 to the number of pnts + 1
            x_ticks: a list with size of 3
            x_label: the x labels of date and time
            ys: a list that contains multiple lists.

        '''
        x = list(range(pnts))
        step = pnts // (ticks-1)
        times = 0
        x_ticks = []
        x_label = []
        while times < ticks - 1:
            index = times * step
            x_ticks.append(x[index])
            x_label.append(dict['Date'][-pnts:][index] + '\n' + dict['Time'][-pnts:][index])
            times += 1
        x_ticks.append(x[-1])
        x_label.append(dict['Date'][-pnts:][-1] + '\n' + dict['Time'][-pnts:][-1])
        ys = [dict[item][-pnts:] for item in items]

        return x, x_ticks, x_label, ys
    
    def _logs_by_date(self, date):
        '''
        This function generates the temporary dictionary by selected date

        Args:
            date: a string of date in 'YYYYMMDD' or 'YYYYMMDD - YYYYMMDD'

        Return:
            dict_by_date: a temporary dictionary by date
        '''
        dict_by_date = {key: [] for key in self.hashDict.keys()}
        date_list = date.replace(' ', '').split('-')
        if len(date_list) < 1 or len(date_list) > 2:
            return
        
        complete_log_list = [log for log in os.listdir(self.logDir) if 'log_' in log]

        start_date = date_list[0]
        log_list_by_date = [log for log in complete_log_list if start_date in log]
        start_log_index = complete_log_list.index(log_list_by_date[0]) - 1
        start_log_index = start_log_index if start_log_index >= 0 else 0 # if start_log_index < 0, force to 0
        log_list_by_date = [complete_log_list[start_log_index]] + log_list_by_date # add the one more log to get complete log because the first log may start in the middle of the date
        if len(date_list) == 2:
            end_date = date_list[1]
            if len(end_date) != len(start_date) or int(end_date) <= int(start_date):
                return
            
            last_log_index = [index for index, log in enumerate(complete_log_list) if end_date in log][-1]
            if not last_log_index:
                return 
            
            else:
                log_list_by_date = complete_log_list[start_log_index: last_log_index + 1]

        for log in log_list_by_date:
            file = open(self.logDir + log, 'r')
            keys = file.readline().strip('\n').split(',')
            self.hashDict = self._hashDict_values_length_keeper(keys, dict_by_date, 'Date')
            for data in csv.reader(file, delimiter = ','): # O(1)
                dict_by_date = self._hashDict_append(keys, data, dict_by_date, memory_reduce = False) # O(n)
        return dict_by_date

    def _update_status(self):
        '''
        Check logger status and device status
        '''
        current_exe = os.popen('wmic process get description').read().strip().replace(' ', '').split('\n\n')
        self.current_device_dict = {'Logger' : True if 'pyB12logger_running.exe' in current_exe else False}
        self.address_dict = {}
        self.deviceConfig.read(self.deviceConfigDirFile)
        self.commandConfig.read(self.commandConfigFile)
        addresses = self.deviceConfig['GENERAL']['device_addresses'].replace(' ', '').split(',')
        for address in addresses:
            model_number = self.deviceConfig[address]['model_number'].replace("'", '')
            if model_number in self.commandConfig.keys():
                self.current_device_dict[model_number] = eval(self.deviceConfig[address]['device_status'].strip())
                self.address_dict[model_number] = address
                
        if self.current_device_dict != self.last_device_dict: # some updates occur
            self.last_device_dict = self.current_device_dict.copy()

    def _update_device_check_button(self, check: matplotlib.widgets.CheckButtons):
        '''
        Logic status check on the logger and devices and set status to check buttons
        '''

        check.eventson = False
        status = check.get_status()
        for i, (check_status, device_status) in enumerate(zip(status, self.current_device_dict.values())):
            if (check_status != device_status):
                check.set_active(i) # Toggle       

        check.eventson = True

        


