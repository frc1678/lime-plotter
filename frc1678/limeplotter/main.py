#!/usr/bin/python3

"""log-plotter.py: plot CSV and networktable data based on specified columns.

For usage information, see the webpage at: https://github.com/frc1678/lime-plotter

Author: Wes Hardaker
"""

import pandas as pd
import yaml
import matplotlib
import matplotlib.pyplot as plt

from matplotlib.animation import FuncAnimation

from frc1678.limeplotter.logloader import LogLoader
from frc1678.limeplotter.networktablesloader import NetworkTablesLoader

import argparse
import sys

__debug = False

animate_plots = []
animate_data = []
animate_frames = 0
plot_pair_data = {}
plot_info = None
anim = None
data_source = None
pause_button = None

def parse_args():
    parser = argparse.ArgumentParser(epilog = "Example usage: log-plotter.py -p estimated_x_position,estimated_y_position / linear_velocity angular_velocity -a -f 50 drivetrain_status.csv")

    parser.add_argument("-p", "--plot-pairs", type=str, nargs="*",
                        help="List of comma separated X,Y variables to use.  If a single variable is specified, it will be Y with X taken from the timestamp column.  Separating variable sets with a / will create multiple plots instead.")

    parser.add_argument("-y", "--yaml-plot", default=None, type=argparse.FileType("r"),
                        help="A YAML file with plotting specifications")

    parser.add_argument("-s", "--scatter-plot", action="store_true",
                        help="Plot a scatter plot instead of a line plot")

    parser.add_argument("-a", "--animate", action="store_true",
                        help="Animate the plot")

    parser.add_argument("-f", "--animation-frames", default=1, type=int,
                        help="Number of frames to plot each time for speed")

    parser.add_argument("-i", "--animation-interval", default=20, type=float,
                        help="Animation interval (milliseconds)")

    parser.add_argument("-l", "--list-variables", action="store_true",
                        help="Just list the available variables in the passed files and exit")

    parser.add_argument("-n", "--no-legend", action="store_true",
                        help="Don't print a legend on the graphs")

    parser.add_argument("-t", "--time-range", nargs=2, type=float,
                        help="Only plot data between two time stamps")

    parser.add_argument("-m", "--marker-columns", type=str, nargs="*",
                        help="Marker columns to print")

    parser.add_argument("-o","--output-file",
                        type=str, nargs='?', 
                        help="PNG File to save")

    parser.add_argument("-L", "--log-files", type=str,
                        nargs='*', help="Log files or dirs to plot")

    parser.add_argument("-N", "--network-server", type=str,
                        help="NetworkTables server address to get data from")

    parser.add_argument("-d", "--debug", action="store_true",
                        help="Turn on debugging output")

    parser.add_argument("-X", "--default-x", default="timestamp", type=str,
                        help="Default x column when not specified")

    parser.add_argument("-T", "--default-table", default=None, type=str,
                        help="Default table name when not specified")
    
    args = parser.parse_args()

    if not args.plot_pairs and not args.list_variables and not args.yaml_plot:
        print("-y with a yaml file or -p with plot-pairs is required")
        exit(1)

    global __debug
    __debug = args.debug

    global animate_frames
    animate_frames = args.animation_frames

    return args

def debug(line):
    """Prints debug log lines when debugging is turned on"""
    if __debug:
        print(line)

def gather_new_data(plot_info, animate):
    """Gather's the next round of data to plot when animating"""
    data_source.gather_next_datasets()
    for plot_entry in plot_info:
        # will return a pandas dataframe with x, y
        plot_entry['data'] = plot_entry['data_source'].gather(plot_entry['xident'],
                                                              plot_entry['yident'],
                                                              animate)

def init_animate():
    """Initialize the plots to nothing.  this allows animation looping so
    we can reset on each loop.
    """

    # XXXX: need to reset the data_source counter for LogLoader
    for plot in animate_plots:
        plot.set_data([],[])

    return animate_plots

def update_animate(i):
    """Updates the animation data with 'animate_frames' new frames"""
    gather_new_data(plot_info, True)
    plots_touched = []
    for plot_entry in plot_info:
        xdata = plot_entry['data'][plot_entry['x']]
        ydata = plot_entry['data'][plot_entry['y']]
        if 'last' in plot_entry['options']:
            xdata = xdata[-int(plot_entry['options']['last']):-1]
            ydata = ydata[-int(plot_entry['options']['last']):-1]

        plot_entry['plot'].set_data(xdata, ydata)
        plots_touched.append(plot_entry['plot'])
    
        #print([xdata.min(), xdata.max()])
        # plot_entry['axis'].set_xlim([xdata.min(), xdata.max()])
        # plot_entry['axis'].set_ylim([ydata.min(), ydata.max()])
        # plot_entry['axis'].relim()
        # plot_entry['axis'].autoscale_view()

        #     axes[axis_index-1].set_ylim(y_lims)

    return plots_touched

def clear_data(event):
    """Called on a button push for live animations to clear the current plots"""
    data_source.clear_data()

paused = False
def pause(event):
    """Pauses the animation when someone clicks the pause button"""
    global paused
    if paused:
        anim.event_source.stop()
        pause_button.label = "Pause"
    else:
        anim.event_source.start()
        pause_button.label = "Play"

    paused = not paused

def mark_time(pair, index, marker = "x"):
    """XXX: currently broken"""
    # mark this on every sub-axis
    debug("  marking " + pair + " at " + str(plot_pair_data[pair]['x'][index]) + "," + str(plot_pair_data[pair]['y'][index]))
    plot_pair_data[pair]['axis'].scatter([plot_pair_data[pair]['x'][index]],[plot_pair_data[pair]['y'][index]], marker = marker, s=25.0, color='red')
    
def mark_xdata(x, marker = "x"):
    """XXX: currently broken"""
    debug("searching for " + str(x))
    for pair in plot_pair_data:
        index = int(len(plot_pair_data[pair]['t']) / 2)
        distance = index

        # search for the spot where index <= x < index+1
        debug("  starting at %d" % (index))
        while True:
            if plot_pair_data[pair]['t'][index] <= x and x < plot_pair_data[pair]['t'][index+1]:
                # found it
                debug("found " + pair)
                debug("  time: " + str(plot_pair_data[pair]['t'][index]))
                debug("  index:" + str(index))

                mark_time(pair, index, marker=marker)
                break

            # jump half a remaining distance
            distance = int(distance / 2)

            if distance == 0:
                distance = 1
                debug("binary search failed -- shouldn't be possible")

            if plot_pair_data[pair]['t'][index+1] <= x:
                index = index + distance
            else:
                index = index - distance

            debug("  jumping to %d" % (index))


def display_time_info(event):
    """XXX: Needs to be re-connected to a button"""
    # assume this must be timestamp data
    # XXX: shouldn't assume this
    mark_xdata(event.xdata)
    plt.show()

def create_subplots_from_yaml(yaml_file, default_x='timestamp',
                              default_table=None):
    """Creates an array of subplots from a yaml specification file"""
    contents = yaml.load(yaml_file, Loader=yaml.FullLoader)

    # create an array of all the plots from the hierarchical structure
    subplots = []
    for key in contents['plots']:
        subplot = []
        subplots.append(subplot)

        # for each subplot entry in the plots list
        # create it's information structure consisting of:
        # x: the x column name
        # y: the y column name
        # table: the table name
        # options: the rest of the options of any kind
        for entry in contents['plots'][key]:
            if 'x' not in entry:
                x = default_x
            else:
                x = entry['x']
            y = entry['y']
            table = default_table
            if 'table' in entry:
                table = entry['table']
            subplot.append({'x': x,
                            'y': y,
                            'table': table,
                            'options': entry})
    return subplots

def create_subplots_from_arguments(arguments, default_x='timestamp',
                                   default_table=None):
    """Creates an array of subplots from an argparse arguments list"""
    # process arguments into subplots
    subplot = []
    subplots = [subplot]
    for pair in arguments:
        if pair == "/":
            # start a new subplot
            subplot = []
            subplots.append(subplot)
        else:
            comma_spot = pair.find(",")
            if comma_spot != -1:
                x = pair[:pair.index(",")]
                y = pair[pair.index(",")+1:]
            else:
                x = default_x
                y = pair
            table=None
            if default_table is not None:
                table=default_table
            subplot.append({'x': x,
                            'y': y,
                            'table': table,
                            'options': {}})
    return subplots

def create_plot_info(plots, axes):
    """Creates a plot information array list that can be iterated over later.

    The data stored in 'plots' definitions represents a visualization
    structure, and is not necessarily related to the collection/tables
    that we need to loop through.  We'll use this opportunity to:
    - create an axis for each plot
    - create a storage data array to iterate over in the future
    - create a storage data dictionary entry for each table/x,y column pair
      - put the axis for it in the data entry
      - put any other needed data into the data entry as well
    """
    global plot_info
    plot_info = []

    for (axis_index, subplot) in enumerate(plots):
        for entry in subplot:
            (x,y) = (entry['x'], entry['y'])

            # find the x and y data from all the columns in all the data
            # note: we don't deal with duplicates...  we probably should
            # especially because timestamps should all come from the same file
            debug("checking data for: " + x + ", " + y)

            # find the data columns we need to plot from the correct tables
            time_data = []
            yident = data_source.find_column_identifier(y)
            if x == 'timestamp':
                xident = data_source.find_column_timestamp_identifier(y)
            else:
                xident = data_source.find_column_identifier(x)

            # Yell if we failed to find what they asked for
            if xident is None:
                raise ValueError("failed to find x data for %s (with y of %s) " % (x,y))
            if yident is None:
                raise ValueError("failed to find y data for " + y)
            debug("plotting " + x + ", " + y)

            entry['xident'] = xident
            entry['yident'] = yident
            entry['axis'] = axes[axis_index]
            entry['data_source'] = data_source # someday we may handle more than one at a time
            if 'fixedAspect' in entry['options'] and entry['options']['fixedAspect']:
                entry['axis'].set_aspect('equal')
            if 'title' in entry['options']:
                entry['axis'].set_title(entry['options']['title'])
            plot_info.append(entry)

def create_matplotlib_plots(plot_info, animate=False, scatter=False,
                            x_lims=[], y_lims=[]):
    """Create the actual matplotlib subplots, setting them up for animation
    if needed."""
    # actually do the plotting
    for plot_entry in plot_info:
        (x, y) = (plot_entry['x'], plot_entry['y'])

        # These will store the x,y data for each plot
        x_data = plot_entry['data'][x]
        y_data = plot_entry['data'][y]

        # set the limits of the graph if defined by the configuration
        if 'xmin' in plot_entry['options'] and 'xmax' in plot_entry['options']:
            plot_entry['axis'].set_xlim([float(plot_entry['options']['xmin']),
                                         float(plot_entry['options']['xmax'])])
        elif 'xmax' in plot_entry['options']: # assume 0 for min
            plot_entry['axis'].set_xlim([0.0, float(plot_entry['options']['xmax'])])

        if 'ymin' in plot_entry['options'] and 'ymax' in plot_entry['options']:
            plot_entry['axis'].set_ylim([float(plot_entry['options']['ymin']),
                                         float(plot_entry['options']['ymax'])])
        elif 'ymax' in plot_entry['options']: # assume 0 for min
            plot_entry['axis'].set_ylim([0.0, float(plot_entry['options']['ymax'])])
            

        marker_size=5.0
        if 'marker_size' in plot_entry['options']:
            marker_size = float(plot_entry['options']['marker_size'])
            print("marker size: ------------ " + str(marker_size))
            
        if animate:
            # Animation requires plotting no data, and doing so in the
            # update_animate routine instead.  So we store the data now
            # for later use.
            if scatter:
                p = plot_entry['axis'].plot([], [], label=y, ls='',
                                            marker = '.', ms=marker_size)
                plot_entry['plot'] = p[0]
                animate_plots.append(p[0])
            else:
                p = plot_entry['axis'].plot([], [], label=y, ms=marker_size)
                plot_entry['plot'] = p[0]
                animate_plots.append(p[0])

            if x_lims[0] is None:
                x_lims = [x_data.min(), x_data.max()]
                y_lims = [y_data.min(), y_data.max()]
            else:
                x_lims = [min(x_lims[0], x_data.min()),
                          max(x_lims[1], x_data.max())]
                y_lims = [min(y_lims[0], y_data.min()),
                          max(y_lims[1], y_data.max())]

        else:
            if scatter:
                plot_entry['axis'].scatter(x_data, y_data, label=y,
                                           marker = '.', s=marker_size)
            else:            
                plot_entry['axis'].plot(x_data, y_data, label=y, ms=marker_size)
    
    

def main():
    """The main routine that opens a data source, initializes it, creates
    the plots structures within matplotlib and displays/animates them."""
    global plot_pair_data
    global data_source
    args = parse_args()

    if args.output_file:
        matplotlib.use('Agg') # avoids needing an X terminal

    # What are we plotting?  config either from command line or a yaml file
    if args.list_variables:
        plots = None
    elif args.plot_pairs:
        plots = create_subplots_from_arguments(args.plot_pairs)
    else:
        plots = create_subplots_from_yaml(args.yaml_plot)

    # What are we plotting?  -- open the stream

    # Create the data source object where we'll extract data from
    if args.log_files:
        data_source = LogLoader(animation_frames=args.animation_frames,
                                sources=args.log_files)

    elif args.network_server:
        data_source = NetworkTablesLoader(args.network_server, plots)
        
    else:
        sys.stderr.write("either a log file list (-L) or a network server (-N) is needed")
        exit(1)

    # see if the data source is only animatable (ie, live data)
    if data_source.animate_only():
        args.animate = True
        
    # just generate a list of variables if requested
    if args.list_variables:
        # Not all data sources support this
        data = data_source.variables_available
        for source in data:
            print(source + ":")
            for column in data[source]:
                print("  " + column)
        exit()

    # tell the datasource to initialize.
    data_source.open()
        
    # How are we plotting them -- create the matplotlib axes 

    # create a figure and NxM plots
    fig, axes = plt.subplots(nrows=len(plots), ncols=1)
    if len(plots) == 1:
        axes = [axes]

    # the data 
    create_plot_info(plots, axes)

    # gather the data we need to plot
    # (for animation or network tables this will only gather a small sample)
    gather_new_data(plot_info, args.animate)

    y_lims = [None, None]
    x_lims = [None, None]
        
    create_matplotlib_plots(plot_info, args.animate, args.scatter_plot,
                            x_lims, y_lims)

    # marker_columns will contain a list of column names to used
    # to mark the graphs.  If it contains commas, we'll split it into
    # segments such that the specification becomes:
    #
    # column_name,rising_threshold,marker
    #
    # where:
    #   - rising_threshold defaults to .5 if not specified
    #   - marker defaults to 'x' if not specified

    # XXX: broken
    if args.marker_columns:
        for column_spec in args.marker_columns:
            parts = column_spec.split(",")
            column = parts[0]
            rising_threshold = .5
            marker = 'x'

            if len(parts) > 1:
                rising_threshold = float(parts[1])

            if len(parts) > 2:
                marker = parts[2]
                
            is_low = True
            for i in range(0, len(plot_pair_data[column]['y'])):
                if is_low and plot_pair_data[column]['y'][i] > rising_threshold:
                    mark_xdata(plot_pair_data[column]['x'][i], marker=marker)
                    is_low = False
                elif plot_pair_data[column]['y'][i] < rising_threshold:
                    is_low = True
            pass

    # add in legends if desired
    if not args.no_legend:
        for (axis_index, subplot) in enumerate(plot_info):
            subplot['axis'].legend()

    # general clean-up: tighten up the plots and
    plt.tight_layout()

    # set the limits of the graph
    # axes[-1].set_xlim(x_lims)
    # axes[-1].set_ylim(y_lims)

    # set font sizes and display size to something reasonable
    fig.set_dpi(150)
    fig.set_size_inches(11,7.5)
    matplotlib.rcParams.update({'font.size': 10})

    if args.output_file:
        # save the results to the requested output file
        plt.savefig(args.output_file)
    else:
        # display the results on the screen...
        if args.animate:
            print(animate_plots)
            # ...possibly using animation
            global anim
            anim = FuncAnimation(fig, update_animate,
                                 init_func=init_animate,
#                                 frames=int(len(animate_data[0][0]) / animate_frames),
                                 interval=args.animation_interval, blit=True)

            axnext = plt.axes([0.0, 0.0, 0.05, 0.05])
            button = matplotlib.widgets.Button(axnext, 'clear')
            button.on_clicked(clear_data)

            axnext = plt.axes([0.1, 0.0, 0.05, 0.05])
            global pause_button
            pause_button = matplotlib.widgets.Button(axnext, 'pause')
            pause_button.on_clicked(pause)
        
        plt.show()

if __name__ == "__main__":
    main()

