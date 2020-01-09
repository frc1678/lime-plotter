import time
import logging

from networktables import NetworkTables

import argparse
import sys
import pandas as pd

from . import loaderbase

def parse_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("-v", "--variables", default="str", type=str,
                        help="The list of table/variable names to print")

    parser.add_argument("input_file", type=argparse.FileType('r'),
                        nargs='?', default=sys.stdin,
                        help="")

    parser.add_argument("output_file", type=argparse.FileType('w'),
                        nargs='?', default=sys.stdout,
                        help="")

    args = parser.parse_args()
    return args



class NetworkTablesLoader(loaderbase.LoaderBase):
    def __init__(self, server, plots=[{'y': 'elevator_height',
                                       'table': 'superstructure_status'}]):
        self._server = server
        self._plots = plots
        self._time = 0.0
    
    def animate_only(self):
        """This loader only loads data over time, and thus must be
        animated."""
        return True
    
    def open(self):
        """Opens the networktables server connection and creates storage"""
        logging.basicConfig(level=logging.DEBUG)

        NetworkTables.initialize(server=self._server)
        
        self._nettables = {}
        self._tables = {}
        self._dfs = {}
        for plot in self._plots:
            for subplot in plot:
                table = subplot['table']

                if table not in self._nettables:
                    print("table: " + table)
                    self._nettables[table] = NetworkTables.getTable(table)
                    self._tables[table] = {}

            
                if 'x' in subplot:
                    x = subplot['x']
                else:
                    x = 'timestamp'

                y = subplot['y']

                self._tables[table][x] = []
                self._tables[table][y] = [] # overwriting is ok if done

    @property
    def variables_available(self):
        return ["not yet"]

    def gather_next_datasets(self):
        """Loops through the existing tables and columns and fetches 
           the next set of data from the nettables server.
        """
        self._time += 1.0
        for table in self._tables:
            for column in self._tables[table]:
                if column == 'localtime':
                    value = self._time
                else:
                    value = self._nettables[table].getNumber(column, 0.0) # default to 0 if no data
                self._tables[table][column].append(value)
                #print(table + "/" + column + " = " + str(value))
        #print(self._tables)

    def gather(self, xident, yident, animate):
        # animate is pretty much always useless to us since
        # we don't have a "get everything" type of source
        # thus we ignore it and return everything we have always
        return pd.DataFrame({xident[1]: self._tables[xident[0]][xident[1]],
                             yident[1]: self._tables[xident[0]][yident[1]]},
                            columns=[xident[1], yident[1]])

    def debug_print(self):
        for table in self._tables:
            for column in self._tables[table]:
                print(table + "/" + column + ": " + str(self._nettables[table].getNumber(column, 'N/A')))

    def _get_a_result(self):
        results = getattr(self, '_results', None)
        if not results:
            results = self.gather_next_datasets() # XXX: this burns a record
            setattr(self, '_results', results)
        return results

    def find_column_identifier(self, column_name):
        for plot in self._plots:
            for subplot in plot:
                if subplot['x'] == column_name:
                    return [subplot['table'], subplot['x']]
                elif subplot['y'] == column_name:
                    return [subplot['table'], subplot['y']]

    def find_column_timestamp_identifier(self, column_name, matching = 'timestamp'):
        for plot in self._plots:
            for subplot in plot:
                if subplot['y']== column_name:
                    return [subplot['table'], matching] # they better be transmitting this!

    def clear_data(self):
        for table in self._tables:
            for column in self._tables[table]:
                self._tables[table][column] = []

    def load_n_rows(self, n=100, sleep=.100):
        for num in range(n):
            if num != 0:
                time.sleep(sleep)
            self.gather_next_datasets()

    def __iter__(self):
        return self

    def __next__(self):
        return self.get_latest_values()

def main():
    ntl = NetworkTablesLoader("127.0.0.1")
    ntl.open()
    print(ntl.variables_available)
    while True:
        ntl.debug_print()

if __name__ == "__main__":
    main()

