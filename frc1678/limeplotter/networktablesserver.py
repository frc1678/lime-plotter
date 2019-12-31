import time
import logging
import re
import sys

from networktables import NetworkTables
from logLoader import LogLoader

class NetworkTablesServer():
    def __init__(self, logfiles):
        self._logfiles = logfiles
        if type(self._logfiles) != list:
            self._logfiles = [self._logfiles]

    def inititalize(self):
        # get our log data
        log_loader = LogLoader()
        log_loader.load_file_or_directories(self._logfiles)
        self._data = log_loader.dataframes
        self._index = 0

        logging.basicConfig(level=logging.DEBUG)

        # init the net tables
        NetworkTables.initialize()

        # get tables and columns
        self._tables = {}
        for filename in self._data.keys():
            tablename = filename
            tablename = re.sub(".*/", "", tablename)
            tablename = re.sub(".csv$", "", tablename)
            print(tablename)
            for column in self._data[filename].columns:
                print("  "+column)
            self._tables[tablename] = { 'nettable': NetworkTables.getTable(tablename),
                                        'data': self._data[filename] }

    def transmit(self):
        for tablename in self._tables:
            for column in self._tables[tablename]['data'].columns:
                self._tables[tablename]['nettable'].putNumber(column, self._tables[tablename]['data'][column][self._index])
        self._index += 1
                

def main():
    source = "573/superstructure_status.csv"
    if len(sys.argv) > 1:
        source = sys.argv[1]
    nts = NetworkTablesServer(source)
    nts.inititalize()

    while True:
        nts.transmit()
        time.sleep(.01)

if __name__ == "__main__":
    main()

        
