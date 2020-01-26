"""An entirely virtual LoaderBase class needed just for documentation"""

import pandas as pd
from xml.dom import minidom
import svgpath2mpl
import matplotlib as mpl

class SVGLoader():
    """An (almost) virtual class just to document the required functions
    that must be overridden by child classes to be functional.
    """

    def __init__(self, filename):
        """save the svg information"""
        self._filename = filename

    def animate_only(self):
        """Whether or not the data source contains full data, or must be
        animated over time."""
        return False
    
    def open(self):
        # read the sveg file
        doc = minidom.parse(self._filename)
        path_strings = [path.getAttribute('d') for path
                        in doc.getElementsByTagName('path')]
        print(path_strings)
        doc.unlink()

        # the path_strings will now be an array of strings containing coords
        self._paths = []
        for entry in path_strings:
            path = svgpath2mpl.parse_path(entry)
            print(type(path))
            self._paths.append(path)
            # this only handles one now...  need multiple names
            
    def draw(self, axis):
        for path in self._paths:
            patch = mpl.patches.PathPatch(path, facecolor=None)
            patch.set_transform(axis.transData)
            axis.add_patch(patch)

    def find_column_identifier(self, column_name):
        """not needed"""
        return ['bogus']
    
    def find_column_timestamp_identifier(self, column_name,
                                         matching='timestamp'):
        """not needed
        """
        return ['bogus']

    def gather_next_datasets(self):
        """We don't animate svgs"""
        pass

    def gather(self, xident, yident, animate = False):
        """read the paths out of the file"""
        return pd.DataFrame({'svgx': [0, 1], 'svgy': [0,3]})

    def get_default_time_column(self):
        return 'svgx'
