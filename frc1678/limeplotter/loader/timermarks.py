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
        self._data = {config['x']: [],
                      config['y'][0]: [],}
        self._next_mark = 0
        self._delta = 120

    def open(self):
        self._xident = self._data_source.find_column_identifier(self._config['x'])
        self._yident = self._data_source.find_column_identifier(self._config['y'][0])
        print(self._xident)
        print(self._yident)

    @property
    def dataframes(self):
        return self._dataframes

    def gather_next_datasets(self):
        pass
        
    def gather(self, xident, yidents, animate = False):
        now = time.time()
        if now > self._next_mark:
            self._next_mark = self._next_mark + self._delta
            dfs = self._data_source.gather(self._xident, [self._yident], animate)
            self._data[self._config['x']].append(float(dfs[self._config['x']][-1:]))
            self._data[self._config['y'][0]].append(float(dfs[self._config['y'][0]][-1:]))

        print("returning:" + str(self._data))
        return pd.DataFrame(self._data,
                            columns=[self._config['x'], self._config['y'][0]])

    def load_file(self, filename, directory = None):
        if directory:
            path = directory + "/" + filename
        else:
            path = filename

        df = pd.read_csv(path)
        #df = df.loc[(df != 0).all(axis=1), :]

        self._csvs.append(path)
        self._dataframes[path] = df

        return df

    def clear(self):
        self._csvs = []
        self._dataframes = {}

    def load_directory(self, directory = None, clear_old = True):
        if not directory:
            directory = self._directory

        # Find all csvs in dir
        files = (os.listdir(directory))

        # clear old
        if clear_old:
            self.clear()
    
        # load each file in the directory
        for filename in files:
            if not filename.endswith(".csv"):
                continue

            self.load_file(filename, directory)

        return self._dataframes

    def load_file_or_directory(self, thing):
        if os.path.isdir(thing):
            return self.load_directory(thing)
        else:
            self.load_file(thing)

    def load_file_or_directories(self, things):
        for thing in things:
            self.load_file_or_directory(thing)

    def find_column_identifier(self, column_name):
        # ask the source for their ident
        return self._data_source.find_column_identifier(column_name)

    def find_column_timestamp_identifier(self, column_name, matching = 'timestamp'):
        # ask the source for their ident
        return self._data_source.find_column_timestamp_identifier(column_name, matching)

    def clear_data(self):
        # we just restart the starting time notion 
        self._data = {}

if __name__ == "__main__":
    print("DNE")
