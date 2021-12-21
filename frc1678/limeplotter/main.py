#!/usr/bin/python3

"""log-plotter.py: plot CSV and networktable data based on specified columns.

For usage information, see the webpage at: https://github.com/frc1678/lime-plotter

Author: Wes Hardaker
"""

import time
import pandas as pd
import yaml
import matplotlib
import matplotlib.pyplot as plt
import math

from matplotlib.animation import FuncAnimation
from matplotlib.path import Path

from frc1678.limeplotter.loader.log import LogLoader
from frc1678.limeplotter.loader.timermarks import TimerMarks
from frc1678.limeplotter.loader.networktables import NetworkTablesLoader
from frc1678.limeplotter.loader.svg import SVGLoader

import argparse
import sys

__debug = False

animate_plots = []
animate_data = []
animate_frames = 0
plot_pair_data = {}
plot_info = None
anim = None
default_data_source = None
data_sources = []
pause_button = None
save_button = None
saved_plots = None

def parse_args():
    parser = argparse.ArgumentParser(epilog = "Example usage: log-plotter.py -y 2021.yml -Y -a -f 50 drivetrain_status.csv")

    group = parser.add_argument_group("Data access")

    group.add_argument("-p", "--plot-pairs", type=str, nargs="*",
                       help="List of comma separated X,Y variables to use.  If a single variable is specified, it will be Y with X taken from the timestamp column.  Separating variable sets with a / will create multiple plots instead.")

    group.add_argument("-y", "--yaml-plot", default=None, type=argparse.FileType("r"),
                       help="A YAML file with plotting specifications")

    group.add_argument("-Y", "--plot-tokens", default=None, type=str, nargs="*",
                       help="A list of plot tokens to ONLY load from the yaml file")

    group.add_argument("-L", "--log-files", type=str,
                       nargs='*', help="Log files or dirs to plot")

    group.add_argument("-N", "--network-server", type=str,
                       help="NetworkTables server address to get data from")

    group.add_argument("-t", "--time-range", nargs=2, type=float,
                       help="Only plot data between two time stamps")

    group.add_argument("-X", "--default-x", default="timestamp", type=str,
                       help="Default x column when not specified")

    group.add_argument("-T", "--default-table", default=None, type=str,
                       help="Default table name when not specified")
    
    group = parser.add_argument_group("Graphics controls") 

    group.add_argument("-o","--output-file",
                       type=str, nargs='?', 
                       help="Save a PNG file instead of displaying an interactive window")

    group.add_argument("-s", "--scatter-plot", action="store_true",
                       help="Plot a scatter plot instead of a line plot")

    group.add_argument("-a", "--animate", action="store_true",
                       help="Animate the plot")

    group.add_argument("-f", "--animation-frames", default=1, type=int,
                       help="Number of frames to plot each time for speed")

    group.add_argument("-i", "--animation-interval", default=20, type=float,
                       help="Animation interval (milliseconds)")

    parser.add_argument("-n", "--no-legend", action="store_true",
                        help="Don't print a legend on the graphs")

    group = parser.add_argument_group("Debugging") 

    group.add_argument("-l", "--list-variables", action="store_true",
                       help="Just list the available variables in the passed files and exit")

    group.add_argument("-d", "--debug", action="store_true",
                       help="Turn on debugging output")

    # XXX currently broken:
    # group.add_argument("-m", "--marker-columns", type=str, nargs="*",
    #                     help="Marker columns to print")

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
    for data_source in data_sources:
        data_source.gather_next_datasets()
    for plot_entry in plot_info:
        # will return a pandas dataframe with x, y
        ds = plot_entry['data_source']
        plot_entry['data'] = ds.gather(plot_entry['xident'],
                                       plot_entry['yidents'],
                                       animate)
        if 'annotate' in plot_entry['options']:
            ds.annotate(plot_entry['axis'],
                        plot_entry['data'],
                        plot_entry['options']['annotate'])

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
    for (axis_index, subplot) in enumerate(saved_plots):
        xlims = [1e10,-1e10]
        ylims = [1e10,-1e10]
        plot_entry = None
        update_x_limits = True
        update_y_limits = True
        for entry in subplot:
            plot_entry = entry

            # skip non-data entries like images
            if 'data' not in plot_entry:
                continue

            # gather the x axis data
            if 'x' not in plot_entry or type(plot_entry['data']) == None:
                print("no x")
                print(plot_entry)
                continue
            
            xdata = plot_entry['data'][plot_entry['x']]
            if 'xoff' in plot_entry['options']:
                xdata = xdata + float(plot_entry['options']['xoff'])

            if 'last' in plot_entry['options']:
                xdata = xdata[-int(plot_entry['options']['last']):-1]

            xlims[0] = min(xdata.min(), xlims[0])
            xlims[1] = max(xdata.max(), xlims[1])

            # gather all the associated y axis data
            for y in plot_entry['y']:
                ydata = plot_entry['data'][y]
                if 'last' in plot_entry['options']:
                    ydata = ydata[-int(plot_entry['options']['last']):-1]

                if 'yoff' in plot_entry['options']:
                    ydata = ydata + float(plot_entry['options']['yoff'])

                ylims[0] = min(ydata.min(), ylims[0])
                ylims[1] = max(ydata.max(), ylims[1])

                plot_entry['plot'].set_data(xdata, ydata)
                plots_touched.append(plot_entry['plot'])

            if 'x_axis_set' in plot_entry:
                update_x_limits = False

            if 'y_axis_set' in plot_entry:
                update_y_limits = False

        if math.isnan(xlims[0]):
            continue

        # steals last plot from loop
        if update_x_limits:
            plot_entry['axis'].set_xlim(xlims)
            
        if update_y_limits:
            plot_entry['axis'].set_ylim(ylims)

        if update_x_limits or update_y_limits:
            plot_entry['axis'].relim()
            plot_entry['axis'].autoscale_view()

        #plot_entry['axis'].get_yaxis().set_ylim(ylims)

    # for ds in data_sources:
    #     ds.debug_print()

    return plots_touched

def freeze(event):
    print("freezing")
    for (axis_index, subplot) in enumerate(saved_plots):
        for entry in subplot:
            plot_entry = entry

            # skip non-data entries like images
            if 'data' not in plot_entry:
                continue

            # gather the x axis data
            xdata = plot_entry['data'][plot_entry['x']]
            if 'xoff' in plot_entry['options']:
                xdata = xdata + float(plot_entry['options']['xoff'])

            if 'last' in plot_entry['options']:
                xdata = xdata[-int(plot_entry['options']['last']):-1]

            # gather all the associated y axis data
            for y in plot_entry['y']:
                ydata = plot_entry['data'][y]
                if 'last' in plot_entry['options']:
                    ydata = ydata[-int(plot_entry['options']['last']):-1]

                if 'yoff' in plot_entry['options']:
                    ydata = ydata + float(plot_entry['options']['yoff'])

                verts = []
                codes = [Path.MOVETO]
                for x, y in zip(xdata,ydata):
                    verts.append((x,y))
                    codes.append(Path.LINETO)

                codes = codes[:-2]
                path = Path(verts)

                patch = matplotlib.patches.PathPatch(path, facecolor="orange",
                                                     color="orange", fill=False,
                                                     linestyle=":")
                axis = plot_entry['axis']
                patch.set_transform(axis.transData)
                axis.add_patch(patch)
                print("added:" + str(plot_entry['y']))



            if 'x_axis_set' in plot_entry:
                update_x_limits = False

            if 'y_axis_set' in plot_entry:
                update_y_limits = False



    for data_source in data_sources:
        data_source.clear_data()
    
    clear_data(event)

def save_data(event):
    now = str(time.time())
    print("saving...")
    for count, plot_entry in enumerate(plot_info):
        # will return a pandas dataframe with x, y
        plot_entry['data'].to_csv(now + "-" + str(count) + ".csv",
                                  index_label="index")
    

def clear_data(event):
    """Called on a button push for live animations to clear the current plots"""
    for data_source in data_sources:
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
                              default_table=None, plot_tokens=None):
    """Creates an array of subplots from a yaml specification file"""
    contents = yaml.load(yaml_file, Loader=yaml.FullLoader)

    # create an array of all the plots from the hierarchical structure
    subplots = []
    subplot_keys = {}
    for key in contents['plots']:
        if plot_tokens and key not in plot_tokens:
            continue

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

            table = default_table
            if 'table' in entry:
                table = entry['table']

            if 'y' not in entry: # e.g., svgs don't need a y
                entry['y'] = []
            elif type(entry['y']) != list:
                entry['y'] = [entry['y']]

            subplot.append({'x': x,
                            'y': entry['y'],
                            'table': table,
                            'key': key,
                            'options': entry})
            subplot_keys[key] = 1

    # check that we found all required plots
    if plot_tokens:
        if len(plot_tokens) != len(subplots):
            # look for missing names for better errors
            for token in plot_tokens:
                if token not in subplot_keys:
                    raise ValueError("CONFIGURATION ERROR: could not find plot '%s' in YAML file '%s'" % (token, yaml_file.name))
                
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
                            'y': [y],
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
    global plot_info, saved_plots, data_sources
    plot_info = []
    saved_plots = plots

    for (axis_index, subplot) in enumerate(plots):
        for entry in subplot:
            (x,ys) = (entry['x'], entry['y'])

            entry['axis'] = axes[axis_index]

            if 'data_source' in entry['options']:
                if entry['options']['data_source'] == 'svg':
                    # determine if we should scale to a size

                    config = {}
                    if 'ymax' in entry['options']:
                        (xmin, ymin) = (0,0)
                        xmax = entry['options']['xmax']
                        ymax = entry['options']['ymax']
                        if 'xmin' in entry['options']:
                            xmin = entry['options']['xmin']
                        if 'ymin' in entry['options']:
                            ymin = entry['options']['ymin']

                        config['transform_to_box'] = [xmin, ymin, xmax, ymax]

                    if 'alpha' in entry['options']:
                        config['alpha'] = entry['options']['alpha']

                    # create the drawer
                    ds = SVGLoader(entry['options']['file'], config)
                    
                    # have the class do final touches
                    ds.open()


                    entry['data_source'] = ds
                    entry['x'] = ds.get_default_time_column()
                    entry['y'] = ['svgy']
                    ys = entry['y']

                    ds.draw(entry['axis'])
                    # data_sources.append(entry['data_source'])
                    continue

                elif entry['options']['data_source'] == 'log':
                    log_source = LogLoader(sources=[str(entry['options']['file'])])
                    
                    entry['data_source'] = log_source
                    log_source.open()
                    data_sources.append(log_source)
                elif entry['options']['data_source'] == 'timer':
                    timer_source = TimerMarks(entry['options'],
                                              default_data_source)
                    entry['data_source'] = timer_source
                    timer_source.open()
                    data_sources.append(timer_source)
            else:
                # use the default data source
                entry['data_source'] = default_data_source

            source = entry['data_source']

            if type(ys) != list:
                ys = [ys]

            # find the x and y data from all the columns in all the data
            # note: we don't deal with duplicates...  we probably should
            # especially because timestamps should all come from the same file
            debug("checking data for: " + x + ", " + str(ys))

            # find the data columns we need to plot from the correct tables
            time_data = []
            yidents = []
            for y in ys:
                yident = source.find_column_identifier(y)
                yidents.append(yident)

            if x == source.get_default_time_column():
                xident = source.find_column_timestamp_identifier(ys[0])
            else:
                xident = source.find_column_identifier(x)

            # Yell if we failed to find what they asked for
            if xident is None:
                raise ValueError("CONFIGURATION ERROR: failed to find x data for variable '%s' (with y of '%s') " % (x,y))
            if len(yidents) == 0:
                raise ValueError("CONFIGURATION ERROR: failed to find y data for variable '%s'" % (y))

            debug("plotting " + x + ", " + str(ys))

            entry['xident'] = xident
            entry['yidents'] = yidents

            if 'fixedAspect' in entry['options'] and entry['options']['fixedAspect']:
                entry['axis'].set_aspect('equal')
            if 'title' in entry['options']:
                entry['axis'].set_title(entry['options']['title'])
            plot_info.append(entry)

def create_matplotlib_plots(plot_info, animate=False, scatter=False):
    """Create the actual matplotlib subplots, setting them up for animation
    if needed."""
    # actually do the plotting
    for plot_entry in plot_info:
        (x, ys) = (plot_entry['x'], plot_entry['y'])

        # These will store the x,y data for each plot
        x_data = plot_entry['data'][x]
        if 'xoff' in plot_entry['options']:
            x_data = x_data + float(plot_entry['options']['xoff'])

        # set the limits of the graph if defined by the configuration
        if 'xmin' in plot_entry['options'] and 'xmax' in plot_entry['options']:
            plot_entry['axis'].set_xlim([float(plot_entry['options']['xmin']),
                                         float(plot_entry['options']['xmax'])])
            plot_entry['x_axis_set'] = True
        elif 'xmax' in plot_entry['options']: # assume 0 for min
            plot_entry['axis'].set_xlim([0.0, float(plot_entry['options']['xmax'])])
            plot_entry['x_axis_set'] = True

        if 'ymin' in plot_entry['options'] and 'ymax' in plot_entry['options']:
            plot_entry['axis'].set_ylim([float(plot_entry['options']['ymin']),
                                         float(plot_entry['options']['ymax'])])
            plot_entry['y_axis_set'] = True
        elif 'ymax' in plot_entry['options']: # assume 0 for min
            plot_entry['axis'].set_ylim([0.0, float(plot_entry['options']['ymax'])])
            plot_entry['y_axis_set'] = True
            
        for y in ys:
            y_data = plot_entry['data'][y]
            if 'yoff' in plot_entry['options']:
                y_data = y_data + float(plot_entry['options']['yoff'])

            marker_size=5.0
            if 'marker_size' in plot_entry['options']:
                marker_size = float(plot_entry['options']['marker_size'])
                debug("marker size: ------------ " + str(marker_size))
                
            color=None
            if 'color' in plot_entry['options']:
                if plot_entry['options']['color'] != 'random':
                    color = plot_entry['options']['color']
                
            if animate:
                # Animation requires plotting no data, and doing so in the
                # update_animate routine instead.  So we store the data now
                # for later use.
                if scatter:
                    p = plot_entry['axis'].plot([], [], label=y, ls='',
                                                marker = '.', ms=marker_size,
                                                color=color)
                else:
                    p = plot_entry['axis'].plot([], [], label=y, ms=marker_size,
                                                color=color)

                plot_entry['plot'] = p[0]
                animate_plots.append(p[0])

            else:
                if scatter:
                    plot_entry['axis'].scatter(x_data, y_data, label=y,
                                               marker = '.', s=marker_size,
                                                color=color)
                else:            
                    plot_entry['axis'].plot(x_data, y_data, label=y,
                                            ms=marker_size,
                                            color=color)
    
    

def main():
    """The main routine that opens a data source, initializes it, creates
    the plots structures within matplotlib and displays/animates them."""
    global plot_pair_data
    global default_data_source
    global data_sources
    args = parse_args()

    if args.output_file:
        matplotlib.use('Agg') # avoids needing an X terminal

    # What are we plotting?  config either from command line or a yaml file
    if args.list_variables:
        plots = None
    elif args.plot_pairs:
        plots = create_subplots_from_arguments(args.plot_pairs)
    else:
        plots = create_subplots_from_yaml(args.yaml_plot, default_x=args.default_x,
                                          plot_tokens=args.plot_tokens)

    # What are we plotting?  -- open the stream

    # Create the data source object where we'll extract data from
    if args.log_files:
        default_data_source = LogLoader(animation_frames=args.animation_frames,
                                        sources=args.log_files)

    elif args.network_server:
        default_data_source = NetworkTablesLoader(args.network_server, plots)
        
    else:
        sys.stderr.write("either a log file list (-L) or a network server (-N) is needed")
        exit(1)

    # see if the data source is only animatable (ie, live data)
    if default_data_source.animate_only():
        args.animate = True
        
    # just generate a list of variables if requested
    if args.list_variables:
        # Not all data sources support this
        data = default_data_source.variables_available
        for source in data:
            print(source + ":")
            for column in data[source]:
                print("  " + column)
        exit()

    # tell the datasource to initialize.
    default_data_source.open()

    data_sources.append(default_data_source)
        
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

    create_matplotlib_plots(plot_info, args.animate, args.scatter_plot)

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
    if False: # if args.marker_columns:
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
            # ...possibly using animation
            global anim
            anim = FuncAnimation(fig, update_animate,
                                 init_func=init_animate,
#                                 frames=int(len(animate_data[0][0]) / animate_frames),
                                 interval=args.animation_interval, blit=False)

            axnext = plt.axes([0.0, 0.0, 0.05, 0.05])
            button = matplotlib.widgets.Button(axnext, 'clear')
            button.on_clicked(clear_data)

            axnext = plt.axes([0.05, 0.0, 0.05, 0.05])
            global pause_button
            pause_button = matplotlib.widgets.Button(axnext, 'pause')
            pause_button.on_clicked(pause)

            axnext = plt.axes([0.10, 0.0, 0.10, 0.05])
            global freeze_button
            freeze_button = matplotlib.widgets.Button(axnext, 'freeze track')
            freeze_button.on_clicked(freeze)

            axnext = plt.axes([0.20, 0.0, 0.10, 0.05])
            global save_button
            save_button = matplotlib.widgets.Button(axnext, 'save data')
            save_button.on_clicked(save_data)

        plt.show()

if __name__ == "__main__":
    main()

