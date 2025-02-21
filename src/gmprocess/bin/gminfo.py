#!/usr/bin/env python

# stdlib imports
from pathlib import Path
import argparse
from collections import OrderedDict
import sys
import warnings
import textwrap
import logging

from gmprocess.subcommands.lazy_loader import LazyLoader
from gmprocess.io.utils import _walk

# third party imports
pd = LazyLoader("pd", globals(), "pandas")

# local imports
readmod = LazyLoader("readmod", globals(), "gmprocess.io.read")
argmod = LazyLoader("argmod", globals(), "gmprocess.utils.args")
stationtrace = LazyLoader("stationtrace", globals(), "gmprocess.core.stationtrace")
confmod = LazyLoader("confmod", globals(), "gmprocess.utils.config")


COLUMNS = [
    "Filename",
    "Format",
    "Process Level",
    "Start Time",
    "End Time",
    "Duration (s)",
    "Network",
    "Station",
    "Channel",
    "Sampling Rate (Hz)",
    "Latitude",
    "Longitude",
]

REV_PROCESS_LEVELS = {
    "raw counts": "V0",
    "uncorrected physical units": "V1",
    "corrected physical units": "V2",
    "derived time series": "V3",
}



class App:
    """App for getting info about ground motion data."""

    @staticmethod
    def main(dir, concise=False, outfile=None, quiet_errors=False):
        """Driver method for gminfo.
        
        Args:
            dir (str):
                Directory to inspect.
            concise (bool):
                Concise format?
            outfile (str):
                File to save result.
            quiet_errors:
                Print error log containing files that could not be parsed.
        """


        logger = logging.getLogger()
        logger.setLevel(logging.CRITICAL)
        warnings.filterwarnings("ignore")
        pd.set_option("display.max_columns", 10000)
        pd.set_option("display.max_colwidth", 10000)
        pd.set_option("display.expand_frame_repr", False)

        do_save = outfile is not None

        # Does the directory exist?
        if not Path(dir).is_dir():
            raise OSError(f"Directory '{dir}' does not exist.")
        
        df, errors = render_dir(dir, concise=concise, save=do_save)
        if outfile is not None and concise:
            save_path = Path(outfile)
            fbase = save_path.parent / save_path.stem
            fext = save_path.suffix
            errfile = str(fbase) + "_errors" + fext
            print(f"Catalog written to {outfile}.")
            print(f"Errors written to {errfile}.")
            if fext == ".xlsx":
                df.to_excel(outfile, index=False)
                errors.to_excel(errfile, index=False)
            else:
                df.to_csv(outfile, index=False)
                errors.to_csv(errfile, index=False)
        if not outfile and not quiet_errors:
            print(errors.to_string(index=False))


def get_dataframe(filename, stream):
    rows = []
    for trace in stream:
        row = {}
        row["Filename"] = filename
        row["Format"] = trace.stats["standard"]["source_format"]
        plevel = trace.stats["standard"]["process_level"]
        row["Process Level"] = REV_PROCESS_LEVELS[plevel]
        row["Start Time"] = trace.stats.starttime
        row["End Time"] = trace.stats.endtime
        dt = trace.stats.endtime - trace.stats.starttime
        row["Duration (s)"] = dt
        row["Network"] = trace.stats.network
        row["Station"] = trace.stats.station
        row["Channel"] = trace.stats.channel
        row["Sampling Rate (Hz)"] = trace.stats.sampling_rate
        row["Latitude"] = trace.stats.coordinates["latitude"]
        row["Longitude"] = trace.stats.coordinates["longitude"]
        rows.append(row.copy())
    df = pd.DataFrame(rows)
    return df


def render_concise(files, save=False):
    df = pd.DataFrame(columns=COLUMNS, index=None)
    folders = []
    error_rows = []
    for path in files:
        fpath = path.parent
        if fpath not in folders:
            sys.stderr.write(f"Parsing files from subfolder {fpath}...\n")
            folders.append(fpath)
        try:
            streams = readmod.read_data(str(path))
            for stream in streams:
                tdf = get_dataframe(path, stream)
                df = pd.concat([df, tdf], axis=0)
        except BaseException as e:
            row = {}
            row["Filename"] = str(path)
            row["Error"] = str(e)
            error_rows.append(row)
            continue
    errors = pd.DataFrame(error_rows)

    # organize dataframe by network, station, and channel
    df = df.sort_values(["Network", "Station", "Channel"])
    if not save:
        print(df.to_string(index=False))

    return (df, errors)


def render_dir(rootdir, concise=True, save=False):
    rootdir = Path(rootdir)
    datafiles = list(_walk(rootdir))

    if concise:
        df, errors = render_concise(datafiles, save=save)
    else:
        errors = render_verbose(datafiles)
        df = None

    return (df, errors)


def render_verbose(files):
    config = confmod.get_config()
    error_rows = []
    for fname in files:
        try:
            fmt = readmod._get_format(fname, config)
            stream = readmod.read_data(fname, config)[0]
            stats = stream[0].stats
            tpl = (
                stats["coordinates"]["latitude"],
                stats["coordinates"]["longitude"],
                stats["coordinates"]["elevation"],
            )
            locstr = "Lat: %.4f Lon: %.4f Elev: %.1f" % tpl
            mydict = OrderedDict(
                [
                    ("Filename", fname),
                    ("Format", fmt),
                    ("Station", stats["station"]),
                    ("Network", stats["network"]),
                    ("Source", stats["standard"]["source"]),
                    ("Location", stats["location"]),
                    ("Coordinates", locstr),
                ]
            )
            print()

            print(pd.Series(mydict).to_string())
            for trace in stream:
                channel = OrderedDict()
                stats = trace.stats
                channel["Channel"] = stats["channel"]
                channel["Start Time"] = stats["starttime"]
                channel["End Time"] = stats["endtime"]
                channel["Number of Points"] = stats["npts"]
                channel["Units"] = stats["standard"]["units"]
                channel["Peak Value"] = trace.max()
                print()
                chstr = pd.Series(channel).to_string()
                parts = ["\t" + line for line in chstr.split("\n")]
                chstr = "\n".join(parts)
                print(chstr)
        except BaseException as e:
            row = {}
            row["Filename"] = str(fname)
            row["Error"] = str(e)
            error_rows.append(row)
            continue
    errors = pd.DataFrame(error_rows)
    return errors


def cli():
    """Command line interface for gminfo"""

    description = """Display summary information about a file, multiple files,
    or directories of files containing strong motion data in the supported
    formats.
    Use the -p option to print errors for files that could not be read.
    Use the -s option to save summary data AND errors to Excel/CSV format."""

    parser = argparse.ArgumentParser(description=description)

    parser.add_argument("dir", help="Directory to inspect.", type=str)

    chelp = """Print out results in concise CSV form. Columns are:
    Filename
    Format
    Process Level
    Start Time
    End Time
    # of Traces
    Duration
    Network
    Station
    Channels
    Sampling rate
    Latitude
    Longitude
    """
    parser.add_argument("-c", "--concise", action="store_true", help=chelp)

    shelp = """Save concise results to CSV/Excel file
    (format determined by extension (.xlsx for Excel, anything else for CSV.))
    """
    parser.add_argument("-s", "--save", metavar="OUTFILE", help=shelp)

    phelp = "Print error log containing files that could not be parsed."
    parser.add_argument("--quiet-errors", action="store_true", help=phelp)

    # Shared arguments
    parser = argmod.add_shared_args(parser)

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    pargs = parser.parse_args()

    if not pargs.concise and pargs.save:
        msg = """
        ****************************************************************
        Saving verbose output is not supported. Use -c and -s
        options together to save tabular summary/error information about
        the data.
        ****************************************************************
        """
        print(textwrap.dedent(msg))
        parser.print_help()
        sys.exit(1)


    app = App()

    app.main(pargs.dir, pargs.concise, pargs.save, pargs.quiet_errors)


if __name__ == "__main__":
    cli()
