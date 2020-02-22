import time
import logging

from networktables import NetworkTables

import argparse
import sys
import pandas as pd

from frc1678.limeplotter.loader import LoaderBase

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

DEFAULT_TIMESTAMP='localtime'

class NetworkTablesLoader(LoaderBase):
    def __init__(self, server, plots=[{}], ignore_zeros=False):
        self._server = server
        self._plots = plots
        self._time = 0.0
        self._network_table_list = None
        self._ignore_zeros = ignore_zeros
    
    def animate_only(self):
        """This loader only loads data over time, and thus must be
        animated."""
        return True
    
    def open_networktables(self):
        """Opens the networktables server connection"""
        logging.basicConfig(level=logging.DEBUG)

        NetworkTables.initialize(server=self._server)
        

    def open(self):
        """Opens the networktables server connection and creates storage"""
        
        self._nettables = {}
        self._tables = None
        self._dfs = {}

        self.open_networktables()

    def setup_table_entry(self, x, yident):
        table = yident[0]

        if table not in self._nettables:
            self._nettables[table] = NetworkTables.getTable(table)
            self._tables[table] = {}
        
        y = yident[1]

        self._tables[table][x] = []
        self._tables[table][y] = [] # overwriting is ok if done

    def setup_table_storage(self):
        if self._tables:
            return
    
        self._tables = {}
        for plot in self._plots:
            for subplot in plot:
                if subplot['data_source'] != self:
                    continue # not it!

                if 'x' in subplot:
                    x = subplot['x']
                else:
                    x = DEFAULT_TIMESTAMP

                for yident in subplot['yidents']:
                    self.setup_table_entry(x, yident)

    @property
    def variables_available(self):
        if self._network_table_list:
            return self._network_table_list

        # open the connection to the server and wait
        self.open_networktables()
        while not NetworkTables.isConnected():
            time.sleep(.1)

        # collect all the tables and all the rows in each table
        results = {}
        tables = NetworkTables.getGlobalTable().getSubTables()
        for table in tables:
            net_table = NetworkTables.getTable(table)
            results[table] = {}
            keys = net_table.getKeys()
            for key in keys:
                results[table][key] = key
                
        self._network_table_list = results
        return results

    def gather_next_datasets(self):
        """Loops through the existing tables and columns and fetches 
           the next set of data from the nettables server.
        """
        self.setup_table_storage()
        self._time += 1.0
        for table in self._tables:
            for column in self._tables[table]:
                if column == DEFAULT_TIMESTAMP:
                    value = self._time
                else:
                    value = self._nettables[table].getNumber(column, 0.0) # default to 0 if no data
                self._tables[table][column].append(value)
                #print(table + "/" + column + " = " + str(value))
        #print(self._tables)

    def gather(self, xident, yidents, animate):
        # animate is pretty much always useless to us since
        # we don't have a "get everything" type of source
        # thus we ignore it and return everything we have always
        datastruct = {}
        if xident:
            datastruct[xident[1]] = self._tables[xident[0]][xident[1]]
        for yident in yidents:
            datastruct[yident[1]] = self._tables[yident[0]][yident[1]]
        df = pd.DataFrame(datastruct,
                          columns=list(datastruct.keys()))
        if self._ignore_zeros:
            df = df.loc[(df != 0).all(axis=1), :]
            #df[df != 0.].dropna(axis=1)
        return df

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
        results = super().find_column_identifier(column_name, self.variables_available)
        if results:
            return results

        # hope we already have plot info then
        for plot in self._plots:
            for subplot in plot:
                if subplot['x'] == column_name:
                    return [subplot['table'], subplot['x']]
                elif subplot['y'] == column_name:
                    return [subplot['table'], subplot['y']]

    def find_column_timestamp_identifier(self, column_name,
                                         matching = DEFAULT_TIMESTAMP):
        results = super().find_column_timestamp_identifier(column_name,
                                                           self.variables_available,
                                                           matching)
        if results:
            return results

        # hope we already have plot info then
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

    def get_default_time_column(self):
        return DEFAULT_TIMESTAMP

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

