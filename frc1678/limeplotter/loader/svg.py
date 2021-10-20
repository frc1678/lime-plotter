"""An entirely virtual LoaderBase class needed just for documentation"""

import os
import pandas as pd
from xml.dom import minidom
import svgpath2mpl
import matplotlib as mpl
import matplotlib.transforms
import pkgutil

class SVGLoader():
    """An (almost) virtual class just to document the required functions
    that must be overridden by child classes to be functional.
    """

    def __init__(self, filename, config = {}):
        """Sets the SVG filename and optional transformation box"""
        self._filename = filename

        if 'transform_to_box' in config:
            b = config['transform_to_box']
            self._bbox = matplotlib.transforms.Bbox.from_bounds(b[0],b[1],b[2],b[3])

        self._config = config
        if 'alpha' in config:
            self._alpha = float(config['alpha'])
        else:
            self._alpha = 0.2

    def animate_only(self):
        """Whether or not the data source contains full data, or must be
        animated over time."""
        return False
    
    def open(self):
        # read the svg file

        if os.path.exists(self._filename):
            doc = minidom.parse(self._filename)
        else:
            # see if we can find a built in version
            local_content = pkgutil.get_data('frc1678.limeplotter.loader', 'svgs/' + self._filename)
            doc = minidom.parseString(local_content)

        path_strings = [path.getAttribute('d') for path
                        in doc.getElementsByTagName('path')]
        doc.unlink()

        # the path_strings will now be an array of strings containing coords
        self._paths = []
        for entry in path_strings:
            path = svgpath2mpl.parse_path(entry)
            self._paths.append(path)
            # this only handles one now...  need multiple names
            
    def draw(self, axis):
        if self._bbox:
            # calculate the maximum extents
            xmin = 1e10
            xmax = -1e10
            ymin = 1e10
            ymax = -1e10

            for path in self._paths:
                extents = path.get_extents()
                xmin = min(xmin, extents.x0)
                xmax = max(xmax, extents.x1)
                
                ymin = min(ymin, extents.y0)
                ymax = max(ymax, extents.y1)

            current_bbox = matplotlib.transforms.Bbox.from_bounds(xmin, ymin, xmax,ymax)
            xformtounit = matplotlib.transforms.BboxTransformFrom(current_bbox)
            xformfromunit = matplotlib.transforms.BboxTransformTo(self._bbox)

            both_transforms = xformtounit + xformfromunit

        for path in self._paths:
            if self._bbox:
                scaled_path = path.transformed(both_transforms)
            else:
                scaled_path = path

            patch = mpl.patches.PathPatch(scaled_path, facecolor=None, alpha=self._alpha,
                                          color=None, fill=False)
            patch.set_transform(axis.transData)
            axis.add_patch(patch)

    def find_column_identifier(self, column_name):
        """not needed"""
        return ['bogus']
    
    def gather_next_datasets(self):
        """We don't animate svgs -- this is a noop function"""
        pass

    def find_column_timestamp_identifier(self, column_name,
                                         matching='timestamp'):
        """also not needed"""
        return ['bogus']

    def gather(self, xident, yident, animate = False):
        """read the paths out of the file"""
        return pd.DataFrame({'svgx': [0, 1], 'svgy': [0,3]})

    def get_default_time_column(self):
        return 'svgx'
