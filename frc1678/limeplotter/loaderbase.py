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

    def find_column_identifier(self, column_name):
        """This should return a column identifier for how to find a column in
        the loader's stored data.  This may be, for example, a double array
        indicating the table and column where the data is stored than then can
        be used as an index into a dictionary."""
        pass
    
    def find_column_timestamp_identifier(self, column_name,
                                         matching='timestamp'):
        """This should return a column identifier for how to find a column in
        the loader's stored data given a matching identifier.  The
        difference between this an the find_column_identifier()
        function is that this should return a reference to the
        matching identifier instead of the column_name itself.  This
        is necessary to be called for, typically, X data names that
        may be repeated across tables such as 'timestamp' columns.  In
        these situations, the X column MUST match the Y column so this
        function is used to find the right X matching data for a given
        Y column_name.
        """
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


