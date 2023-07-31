import numpy as np
import matplotlib.pyplot as plt
import csv

class plotter:
    def __init__(self, log):
        self.log = log
        self.header = None
        self.items = None
        self.hashDict = None
        self.f = None
        
        self.logRead()
    
    def logRead(self):
        self.f = open(self.log, 'r')
        self.header = self.f.readline().strip('\n').split(',')
        self.items = self.f.readline().strip('\n').split(',')
        self.hashDict ={x.strip(): [] for x in self.items}
        
        for info in csv.reader(self.f, delimiter = ','): # O(1)
            self.hashDict = self.hashDict_append(info, self.hashDict) # O(n)

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
    
    def plot(self, item, pnts):

        x_label = [self.hashDict['Time'][-pnts:][i] if i in [0,pnts/2, pnts-1] else '' for i in range(pnts)]
        x = [i for i in range(1, pnts + 1)]
        y = self.hashDict[item][-pnts:] 

        fig = plt.figure(1)
        ax = fig.add_subplot(1,1,1)
        ax.grid(ls = ':')
        update_require = 1

        while(plt.fignum_exists(1)):

            # where = f.tell() # (option) f current position of pointer
            line = self.f.readline().strip('\n')
            if line: # if there is non-empty new line
                self.hashDict_append(line.strip('\n').split(','), self.hashDict)
                x_label = [self.hashDict['Time'][-20:][i] if i in [0,10,19] else '' for i in range(20)]
                y = self.hashDict['voltage1'][-20:]
                update_require = 1

            else: # if there is no line
                if update_require:
                    # f.seek(where) # (option) find current pointer
                    ax.clear()
                    ax.set_xticks(x, x_label)
                    ax.grid(ls = ':')
                    ax.plot(x, y, '#F37021')
                    update_require = 0
        

            plt.pause(0.01) # showing new plot
    
        plt.show()