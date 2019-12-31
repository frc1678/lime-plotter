import sys
import pandas as pd
import os
import os.path

from . import loaderbase

class LogLoader(loaderbase.LoaderBase):
    def __init__(self, directory = None, animation_frames=1,
                 sources=None):
        self._directory = directory
        self._sources = sources
        self.clear()
        self._slice_count = 0
        self._slice_increment = animation_frames
        self._slice_start = 0
        pass

    @property
    def dataframes(self):
        return self._dataframes

    @property
    def variables_available(self):
        """Returns a list of tables/columns we found in the data source(s)."""
        outlist = {}
        for filename in self._dataframes:
            outlist[filename] = {}
            for column in self._dataframes[filename].columns:
                outlist[filename][column] = 1
        return outlist

    @property
    def csvs(self):
        return self._csvs

    def open(self):
        self.load_file_or_directories(self._sources)

    def gather_next_datasets(self):
        self._slice_count += self._slice_increment
        
    def gather(self, xident, yident, just_a_bit = False):
        if just_a_bit:
            return self._dataframes[xident[0]][[xident[1], yident[1]]][self._slice_start:self._slice_count]
            
        # selects the table (xident[0]) with x and y columns (the 1s)
        return self._dataframes[xident[0]][[xident[1], yident[1]]]

    def load_file(self, filename, directory = None):
        if directory:
            path = directory + "/" + filename
        else:
            path = filename

        df = pd.read_csv(path)

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

    def find_column_dataframe(self, column_name):
        for filename in self._dataframes:
            if column_name in self._dataframes[filename]:
                return self._dataframes[filename][column_name]

    def find_column_identifier(self, column_name):
        for filename in self._dataframes:
            if column_name in self._dataframes[filename]:
                return [filename, column_name]

    def find_column_timestamp_identifier(self, column_name, matching = 'timestamp'):
        for filename in self._dataframes:
            if column_name in self._dataframes[filename]:
                return [filename, matching]

    def find_columns_timestamp_dataframe(self, column_name,
                                         matching = 'timestamp'):
        # timestamp is a duplicated column and we need the matching one
        for filename in self._dataframes:
            if column_name in self._dataframes[filename]:
                return self._dataframes[filename][matching]
        

    def clear_data(self):
        # we just restart the starting time notion 
        self._slice_start = self._slice_count

if __name__ == "__main__":
    thing = "../792"
    if len(sys.argv) >= 2:
        thing = sys.argv[1]

    ll = LogLoader()
    ll.load_file_or_directory(thing)
    dfs = ll.dataframes
    print(dfs)
    print("---")
    print(ll.find_column_dataframe('profiled_y_goal'))
    print("timestamp " + str(ll.find_column_dataframe('timestamp')[5]))
    print("--- dne:")
    print(ll.find_column_dataframe('aoeaoeuaeouaoeu'))
