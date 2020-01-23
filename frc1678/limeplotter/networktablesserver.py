"""A test server for re-transmitting CSV files over networktables"""

import time
import logging
import re
import sys

from networktables import NetworkTables
from frc1678.limeplotter.logloader import LogLoader

class NetworkTablesServer():
    def __init__(self, logfiles):
        self._logfiles = logfiles
        if type(self._logfiles) != list:
            self._logfiles = [self._logfiles]

    def open(self):
        # get our log data
        log_loader = LogLoader(sources=self._logfiles)
        self._log_loader = log_loader
        log_loader.open()
        self._vars = log_loader.variables_available
        self._index = 0

        logging.basicConfig(level=logging.DEBUG)

        # init the net tables
        NetworkTables.initialize()

        # get tables and columns
        self._tables = {}
        for filename in self._vars.keys():
            tablename = filename
            tablename = re.sub(".*/", "", tablename)
            tablename = re.sub(".csv", "", tablename)
            print(tablename)
            for column in self._vars[filename]:
                print("  "+column)
            self._tables[tablename] = { 'nettable': NetworkTables.getTable(tablename),
                                        'columns': self._vars[filename],
                                        'table': tablename,
                                        'index': filename,
            #                            'data': self._data[table]
            }

    def transmit(self):
        self._log_loader.gather_next_datasets()
        for tablename in self._tables:
            for column in self._tables[tablename]['columns']:
                if column == 'timestamp':
                    continue
                data = self._log_loader.gather([self._tables[tablename]['index'], 'timestamp'],
                                               [[self._tables[tablename]['index'], column]], True)
                #print(column + ": " + str(data[column][-2:-1]))
                try:
                    self._tables[tablename]['nettable'].putNumber(column, data[column][-2:-1])
                except:
                    pass

def main():
    source = "573/superstructure_status.csv"
    if len(sys.argv) > 1:
        source = sys.argv[1]
    nts = NetworkTablesServer(source)
    nts.open()

    while True:
        nts.transmit()
        time.sleep(.002)

if __name__ == "__main__":
    main()

        
