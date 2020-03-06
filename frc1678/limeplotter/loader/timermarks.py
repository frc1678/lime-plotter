import sys
import pandas as pd
import os
import os.path
import time

from frc1678.limeplotter.loader import LoaderBase

class TimerMarks(LoaderBase):
    def __init__(self, config, data_source):
        self._config = config
        self._data_source = data_source
        self._dataframes = None
        self._x = config['x']
        self._y = config['y'][0] # we only support a single y point
        self._data = {self._x: [],
                      self._y: [],}
        self._next_mark = 0
        self._delta = 60
        self._last_annonate = 0
        if 'delta' in config:
            self._delta = config['delta']

    def open(self):
        self._xident = self._data_source.find_column_identifier(self._x)
        self._yident = self._data_source.find_column_identifier(self._y)

    @property
    def dataframes(self):
        return self._dataframes

    def gather_next_datasets(self):
        pass
        
    def gather(self, xident, yidents, animate = False):
        now = time.time()
        if now > self._next_mark:
            self._next_mark = now + self._delta
            dfs = self._data_source.gather(self._xident, [self._yident], animate)
            # make sure we have some data
            if len(dfs[self._x]) == 0 or len(dfs[self._y]) == 0:
                return

            x = float(dfs[self._x][-1:])
            y = float(dfs[self._y][-1:])

            # if we're on the 0 line, the robot is off
            if x != 0.0 or y != 0.0:
                self._data[self._x].append(x)
                self._data[self._y].append(y)
            else:
                # if off, reset the expected next mark
                self._next_mark = 0


        return pd.DataFrame(self._data,
                            columns=[self._x, self._y])

    def clear(self):
        self._csvs = []
        for col in self._data:
            self._data[col] = []

    def find_column_identifier(self, column_name):
        # ask the source for their ident
        return self._data_source.find_column_identifier(column_name)

    def find_column_timestamp_identifier(self, column_name, matching = 'timestamp'):
        # ask the source for their ident
        return self._data_source.find_column_timestamp_identifier(column_name, matching)

    def clear_data(self):
        # we just restart the starting time notion 
        for col in self._data:
            self._data[col] = []

    def annotate(self, axis, data, annotate_config):
        count = len(data[self._x].index)
        if count > self._last_annonate:
            self._last_annonate = count
            lastx = data[self._x].iloc[-1]
            lasty = data[self._y].iloc[-1]
            if 'xoff' in self._config:
                lastx = lastx + self._config['xoff']
            if 'yoff' in self._config:
                lasty = lasty + self._config['yoff']

            axis.annotate(str(count), xy=(lastx, lasty),
                          xytext=(lastx, lasty),
                          ha='center', va='center')
            

if __name__ == "__main__":
    print("DNE")
