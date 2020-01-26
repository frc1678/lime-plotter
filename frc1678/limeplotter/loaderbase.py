"""An entirely virtual LoaderBase class needed just for documentation"""

class LoaderBase():
    """An (almost) virtual class just to document the required functions
    that must be overridden by child classes to be functional.
    """

    def __init__(self):
        """Each child class will likely have their own arguments required to
        save for run-time use."""
        pass

    def animate_only(self):
        """Whether or not the data source contains full data, or must be
        animated over time."""
        return False
    
    def open(self):
        """Opens whatever resources are needed by the child classes."""
        pass

    def gather_next_datasets(self):
        """This is called once per animation loop to collect all necessary
        data from a datasource."""
        pass

    def gather(self, xident, yident, animate = False):
        """This function should return a pandas DataFrame object containing
        two columns identified by the xident and yident identifiers.
        If animate is True, it will indicate we're returning only a
        portion of the data during an animation loop.
        """
        pass

    def clear_data(self):
        """This is called to reset a graph during animations; it should clear
        out all past stored data."""
        pass

    def get_default_time_column(self):
        return 'timestamp'

    def find_column_identifier(self, column_name, table_info):
        "Finds an column name in a nested structure of table/column_names "
        for table in table_info:
            if column_name in table_info[table]:
                return [table, column_name]

    def find_column_timestamp_identifier(self, column_name, table_info,
                                         matching = 'timestamp'):
        """Same, but looks for a column 'matching' for a table identified by a
        different column_name ; useful for looking for duplicate
        'matching' named columns (eg, timestamps) that exist in every
        table.
        """
        for table in table_info:
            if column_name in table_info[table]:
                # XXX todo:: make sure matching exists before returning it
                return [table, matching]


