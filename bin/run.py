# functions for initializing TDF-SDK are found in the pyTDFSDK package
from pyTDFSDK.init_tdf_sdk import init_tdf_sdk_api
from pyTDFSDK.classes import TdfData
from pyTDFSDK.tims import tims_scannum_to_oneoverk0, tims_oneoverk0_to_scannum, tims_index_to_mz, tims_read_scans_v2

import os
import platform
import sqlite3
import numpy as np
import pandas as pd
import argparse


# arguments to run in the command line
def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input',
                        help='File path for Bruker .d file from MALDI AutoXecute run containing TDF file.',
                        required=True,
                        type=str)
    parser.add_argument('--outdir',
                        help='Path to folder in which to write output CSV file. Default = same as input path.',
                        default='',
                        type=str)
    parser.add_argument('--outfile',
                        help='User defined filename for output CSV file.',
                        default='',
                        type=str)
    parser.add_argument('--mz',
                        help='One or more m/z value(s) of interest. Must be equal to the num of 1/K0 values entered.',
                        required=True,
                        nargs='+',
                        type=float)
    parser.add_argument('--mz_tol',
                        help='One or more m/z tolerance(s) in Da.',
                        nargs='+',
                        default=0.05,
                        type=float)
    parser.add_argument('--ook0',
                        help='One or more 1/K0 value(s) of interest. Must be equal to the num of m/z values entered.',
                        required=True,
                        nargs='+',
                        type=float)
    parser.add_argument('--ook0_tol',
                        help='One or more 1/K0 tolerance(s).',
                        nargs='+',
                        default=0.05,
                        type=float)
    arguments = parser.parse_args()
    return vars(arguments)


def run():
    # Parse arguments
    args = get_args()

    # Set output directory to default if not specified.
    if args['outdir'] == '':
        args['outdir'] = os.path.split(args['input'])[0]

    if args['outfile'] == '':
        args['outfile'] = os.path.splitext(os.path.split(args['input'])[-1])[0] + '.csv'

    # Check to make sure number of m/z and 1/K0 values match.
    # Also make sure an equal number of m/z and 1/K0 tolerance values are present if more than one tolerance given.
    if len(args['mz_tol']) > 1 and len(args['ook0_tol']) > 1:
        if len(args['mz']) != len(args['ook0']) != len(args['mz_tol']) != len(args['ook0_tol']):
            raise Exception('Number of m/z and 1/K0 values and tolerances given in arguments is not equal.')
    elif len(args['mz_tol']) > 1 >= len(args['ook0_tol']):
        if len(args['mz']) != len(args['ook0']) != len(args['mz_tol']):
            raise Exception('Number of m/z and 1/K0 values and m/z tolerances given in arguments is not equal.')
        else:
            args['ook0_tol'] = args['ook0_tol'] * len(args['ook0'])
    elif len(args['ook0_tol']) > 1 >= len(args['mz_tol']):
        if len(args['mz']) != len(args['ook0']) != len(args['ook0_tol']):
            raise Exception('Number of m/z and 1/K0 values and 1/K0 tolerances given in arguments is not equal.')
        else:
            args['mz_tol'] = args['mz_tol'] * len(args['mz'])
    elif len(args['mz_tol']) == 1 and len(args['ook0_tol']) == 1:
        if len(args['mz']) != len(args['ook0']):
            raise Exception('Number of m/z and 1/K0 values given in arguments is not equal.')
        else:
            args['mz_tol'] = args['mz_tol'] * len(args['mz'])
            args['ook0_tol'] = args['ook0_tol'] * len(args['ook0'])

    # Load TDF data
    dll = init_tdf_sdk_api()
    tdf_data = TdfData(args['input'], dll)

    list_of_scan_dicts = []

    for mz, mz_tol, ook0, ook0_tol in zip(args['mz'], args['mz_tol'], args['ook0'], args['ook0_tol']):
        # Each frame == one spectrum from a MALDI spot
        # MaldiFrameInfo table in analysis.tdf SQL database tells which frame is associated with each spot
        for frame in range(1, tdf_data.analysis['MaldiFrameInfo'].shape[0] + 1):
            scan_dict = {}
            frames_dict = tdf_data.analysis['Frames'][tdf_data.analysis['Frames']['Id'] ==
                                                      frame].to_dict(orient='records')[0]
            maldiframeinfo_dict = tdf_data.analysis['MaldiFrameInfo'][tdf_data.analysis['MaldiFrameInfo']['Frame'] ==
                                                                      frame].to_dict(orient='records')[0]
            scan_dict['Frame'] = int(frames_dict['Id'])
            scan_dict['Spot'] = maldiframeinfo_dict['SpotName']
            scan_dict['mz'] = mz
            scan_dict['mz_tolerance'] = mz_tol
            scan_dict['ook0'] = ook0
            scan_dict['ook0_tol'] = ook0_tol
            scan_dict['intensity'] = 0

            # Get 1/K0 values from scan numbers in run
            ook0_array = tims_scannum_to_oneoverk0(dll, tdf_data.handle, frame, range(0, frames_dict['NumScans']+1))
            # Get 1/K0 values within tolerance
            ook0_within_tolerance = [i for i in ook0_array
                                     if ook0 + ook0_tol >= i >= ook0 - ook0_tol]
            # Get scan numbers for ook0 values within tolerance
            ook0_within_tolerance_scannums = tims_oneoverk0_to_scannum(dll,
                                                                       tdf_data.handle,
                                                                       frame,
                                                                       ook0_within_tolerance)
            ook0_within_tolerance_scannums = [int(i) for i in ook0_within_tolerance_scannums]

            # Read scans from current frame
            # each frame has N scans where each scan corresponds to a 1/K0 value
            list_of_scans = tims_read_scans_v2(dll,
                                               tdf_data.handle,
                                               frame,
                                               min(ook0_within_tolerance_scannums),
                                               max(ook0_within_tolerance_scannums))
            scan_begin = 0
            scan_end = max(ook0_within_tolerance_scannums) - min(ook0_within_tolerance_scannums)
            for scan_num in range(scan_begin, scan_end):
                if list_of_scans[scan_num][0].size != 0 \
                        and list_of_scans[scan_num][1].size != 0 \
                        and list_of_scans[scan_num][0].size == list_of_scans[scan_num][1].size:
                    mz_array = tims_index_to_mz(dll, tdf_data.handle, frame, list_of_scans[scan_num][0]).tolist()
                    intensity_array = list_of_scans[scan_num][1].tolist()
                    # Get indices of m/z values within tolerance
                    indices = [mz_array.index(i) for i in mz_array
                               if mz + mz_tol >= i >= mz - mz_tol]
                    # Sum intensities if m/z value was found within tolerance of feature of interest
                    # this summed intensity is the intensity of mz +/- mz_tol at ook0 +/- ook0_tol
                    scan_dict['intensity'] += sum([intensity_array[i] for i in indices])
            list_of_scan_dicts.append(scan_dict)

    results = pd.DataFrame(list_of_scan_dicts)
    results.to_csv(os.path.join(args['outdir'], args['outfile']), index=False)


if __name__ == "__main__":
    run()
