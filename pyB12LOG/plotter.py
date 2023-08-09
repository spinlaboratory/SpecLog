"""
pyB12LOG: The logging program for instrumentations

Author: Yen-Chun Huang

Company: Bridge 12 Technologies, Inc
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import csv
import datetime
from matplotlib.widgets import Button, RadioButtons, CheckButtons, Slider 
from .config.config import CONFIG

class plotter:
    def __init__(self, max_pnts = 1e4):
        deviceConfigDirHome = CONFIG['CONFIG']['log_folder_location'][1:-1]
        self.logDir = deviceConfigDirHome + '/B12TLOG/'
        self.header = None
        self.items = None
        self.hashDict = {}
        self.log_list = os.listdir(self.logDir)
        self.f = None
        self.current_log = None
        self.log_index = 1 # debug log is always index 0
        self.max_pnts = int(max_pnts)
        self.update_figure = True

        self.logRead()
        self.plot()

    def logRead(self):
        self.log_list = os.listdir(self.logDir)
        while self.current_log != self.log_list[-1]: 
            self.current_log = self.log_list[self.log_index] # update current log
            if 'log_' in self.current_log:
                self.current_log = self.current_log
                self.f = open(self.logDir + self.current_log, 'r')
                
                self.items = self.f.readline().strip('\n').split(',')
                for x in self.items:
                    if x.strip() not in self.hashDict: # if new item is found
                        self.hashDict[x.strip()] = [0] * len(self.hashDict['Date']) if self.hashDict else [] # take care if new item appears with old log, then put all 0 to the front

                for data in csv.reader(self.f, delimiter = ','): # O(1)
                    self.hashDict = self.hashDict_append(data, self.hashDict) # O(n)
            self.log_index += 1
        self.items = list(self.hashDict.keys())[2:] # get all headers/items

    def hashDict_append(self, info, hashDict):
        for index, key in enumerate(hashDict.keys()):
            if key == 'Date':
                val = info[index]
            elif key == 'Time':
                val = info[index].strip() # not necessary to convert string to time in plotting
            else:
                val = float(info[index])
            
            hashDict[key].append(val)
        return hashDict
    
    def plot(self):
        items = self.items
        self.time_length = len(self.hashDict['Time'])
        if self.time_length < self.max_pnts: 
            self.pnts = self.time_length//2
        else:
            self.pnts = self.max_pnts//2
            
        x = [i for i in range(1, self.pnts + 1)]
        x_ticks = [x[0], x[self.pnts//2], x[-1]]
        x_label = [self.hashDict['Date'][-self.pnts:][0] +'\n'+ self.hashDict['Time'][-self.pnts:][0], 
                   self.hashDict['Date'][-self.pnts:][self.pnts//2] +'\n'+ self.hashDict['Time'][-self.pnts:][self.pnts//2], 
                   self.hashDict['Date'][-self.pnts:][-1] +'\n'+ self.hashDict['Time'][-self.pnts:][-1]]
        ys = [self.hashDict[item][-self.pnts:] for item in items]

        color_lists = ['#F37021', '#46812B', '#4D4D4F', '#A7A9AC'] * (len(items) // 4) 

        # init figure
        fig = plt.figure(1, figsize = (16,12))
        plt.subplots_adjust(left=0.25, bottom = 0.25)
        ax = fig.add_subplot(1,1,1)
        update_require = 0

        # initial plotting
        lines_list = []
        for index, (y, color) in enumerate(zip(ys, color_lists)):
            l0, = ax.plot(x, y, color, label = items[index])
            lines_list.append(l0) # this is for checkbutton
        ax.set_xticks(x_ticks)
        ax.set_xticklabels(x_label)
        ax.grid(ls = ':')
        ax.set_xlabel('Time')

        # checkbutton settings
        lines_by_label = {l.get_label(): l for l in lines_list}               
        line_colors = [l.get_color() for l in lines_by_label.values()]
        self.visibility_by_label = {l.get_label(): l.get_visible() for l in lines_list}

        rax = fig.add_axes([0.01, 0.4, 0.2, 0.15])
        check = CheckButtons(
            ax=rax,
            labels=lines_by_label.keys(),
            actives=[l.get_visible() for l in lines_by_label.values()],
            label_props={'color': line_colors},
            frame_props={'edgecolor': line_colors},
            check_props={'facecolor': line_colors},
        )
        
        def callback(label):
            self.visibility_by_label[label] = not self.visibility_by_label[label]
            self.update_figure = True

        check.on_clicked(callback)

        # slider bar
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

        def update(val):
            self.slider_pnts = int(sTime.val)
            self.update_figure = True
        
        sTime.on_changed(update)

        # reset
        resetax = plt.axes([0.8, 0.08, 0.1, 0.04])
        button = Button(resetax, 'Reset', color='lightgoldenrodyellow', hovercolor='0.975')

        def reset(event):
            sTime.reset()
            self.update_figure = True
        button.on_clicked(reset)

        while(plt.fignum_exists(1)):

            self.logRead() # check if new log creates
            # where = self.f.tell() # (option) f current position of pointer
            line = self.f.readline().strip('\n')
            if line: # if there is non-empty new line
                self.hashDict_append(line.strip('\n').split(','), self.hashDict)
                self.time_length = len(self.hashDict['Time'])
                self.update_figure = True        

            if self.update_figure:    
                # updates plotting information       
                self.pnts = self.time_length if self.time_length < self.max_pnts else self.max_pnts
                self.pnts = min(self.slider_pnts, self.pnts)
      
                x = [i for i in range(1, self.pnts + 1)]
                x_ticks = [x[0], x[self.pnts//2], x[-1]]
                x_label = [self.hashDict['Date'][-self.pnts:][0] +'\n'+ self.hashDict['Time'][-self.pnts:][0], 
                           self.hashDict['Date'][-self.pnts:][self.pnts//2] +'\n'+ self.hashDict['Time'][-self.pnts:][self.pnts//2], 
                           self.hashDict['Date'][-self.pnts:][-1] +'\n'+ self.hashDict['Time'][-self.pnts:][-1]]
                ys = [self.hashDict[item][-self.pnts:] for item in items]
                self.slider_bar_updates = False

                # self.f.seek(where) # (option) find current pointer
                ax.clear()
                ax.grid(ls = ':')
                for index, (y, color) in enumerate(zip(ys, color_lists)):
                    label = items[index]
                    if self.visibility_by_label[label]:
                        ax.plot(x, y, color, label = label)

                ax.set_xticks(x_ticks)
                ax.set_xticklabels(x_label)
                ax.set_xlabel('Time')

                self.update_figure = False

            plt.pause(0.01) # showing new plot
    
        plt.show()