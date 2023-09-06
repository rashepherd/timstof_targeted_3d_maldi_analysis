# functions for initializing TDF-SDK are found in the pyTDFSDK package
from pyTDFSDK.init_tdf_sdk import init_tdf_sdk_api
from pyTDFSDK.constants import *
from pyTDFSDK.methods import *
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
                        help='Path to folder in whch to write output CSV file. Default = same as input path.',
                        default='',
                        type=str)
    parser.add_argument('--outfile',
                        help='User defined filename for output CSV file.',
                        default='',
                        type=str)
    parser.add_argument('--mz',
                        help='m/z value of interest',
                        required=True,
                        type=float)
    parser.add_argument('--mz_tol',
                        help='m/z tolerance in Da',
                        default=0.05,
                        type=float)
    parser.add_argument('--ook0',
                        help='1/K0 value of interest',
                        required=True,
                        type=float)
    parser.add_argument('--ook0_tol',
                        help='1/K0 tolerance',
                        default=0.05,
                        type=float)
    arguments = parser.parse_args()
    return vars(arguments)


# error handler copied from TDF-SDK
def throw_last_timsdata_error(tdf_sdk):
    length = tdf_sdk.tims_get_last_error_string(None, 0)
    buf = ctypes.create_string_buffer(length)
    tdf_sdk.tims_get_last_error_string(buf, length)
    raise RuntimeError(buf.value)


# class to read in metadata from analysis.tdf file
# modified from tdf_data class in TIMSCONVERT to only include relevant information
# class methods were removed; methods for parsing raw Bruker data are now found in pyTDFSDK along with API files
class MaldiTdfData(object):
    def __init__(self, bruker_d_folder_name: str, tdf_sdk_dll, use_recalibrated_state=True):
        self.dll = tdf_sdk_dll
        self.handle = tims_open(self.dll, bruker_d_folder_name, use_recalibrated_state)
        if self.handle == 0:
            throw_last_timsdata_error(self.dll)
        self.conn = sqlite3.connect(os.path.join(bruker_d_folder_name, 'analysis.tdf'))
        self.initial_frame_buffer_size = 128

        self.meta_data = None
        self.frames = None
        self.maldiframeinfo = None
        self.framemsmsinfo = None
        self.source_file = bruker_d_folder_name

        self.get_global_metadata()
        self.get_frames_table()
        self.get_maldiframeinfo_table()
        self.get_framemsmsinfo_table()

    # Gets global metadata table as a dictionary.
    def get_global_metadata(self):
        metadata_query = 'SELECT * FROM GlobalMetadata'
        metadata_df = pd.read_sql_query(metadata_query, self.conn)
        metadata_dict = {}
        for index, row in metadata_df.iterrows():
            metadata_dict[row['Key']] = row['Value']
        self.meta_data = metadata_dict

    # Get Frames table from analysis.tdf SQL database.
    def get_frames_table(self):
        frames_query = 'SELECT * FROM Frames'
        self.frames = pd.read_sql_query(frames_query, self.conn)

    # Get MaldiFramesInfo table from analysis.tdf SQL database.
    def get_maldiframeinfo_table(self):
        maldiframeinfo_query = 'SELECT * FROM MaldiFrameInfo'
        self.maldiframeinfo = pd.read_sql_query(maldiframeinfo_query, self.conn)

    # Get FrameMsMsInfo table from analysis.tdf SQL database.
    def get_framemsmsinfo_table(self):
        framemsmsinfo_query = 'SELECT * FROM FrameMsMsInfo'
        self.framemsmsinfo = pd.read_sql_query(framemsmsinfo_query, self.conn)


def run():
    # Parse arguments
    args = get_args()

    # Set output directory to default if not specified.
    if args['outdir'] == '':
        args['outdir'] = os.path.split(args['input'])[0]

    if args['outfile'] == '':
        args['outfile'] = os.path.splitext(os.path.split(args['input'])[-1])[0] + '.csv'

    # Load TDF data
    # Get relative TDF-SDK .dll/.so path
    if platform.system() == 'Windows':
        dll_path = os.path.join(os.path.dirname(__file__), 'lib', 'timsdata.dll')
    elif platform.system() == 'Linux':
        dll_path = os.path.join(os.path.dirname(__file__), 'lib', 'timsdata.dll')
    dll = init_tdf_sdk_api(dll_path)
    tdf_data = MaldiTdfData(args['input'], dll)

    list_of_scan_dicts = []

    # Each frame == one spectrum from a MALDI spot
    # MaldiFrameInfo table in analysis.tdf SQL database tells which frame is associated with each spot
    for frame in range(1, tdf_data.maldiframeinfo.shape[0] + 1):
        scan_dict = {}
        frames_dict = tdf_data.frames[tdf_data.frames['Id'] == frame].to_dict(orient='records')[0]
        maldiframeinfo_dict = tdf_data.maldiframeinfo[tdf_data.maldiframeinfo['Frame'] == frame].to_dict(orient='records')[0]
        scan_dict['Frame'] = int(frames_dict['Id'])
        scan_dict['Spot'] = maldiframeinfo_dict['SpotName']
        scan_dict['mz'] = args['mz']
        scan_dict['mz_tolerance'] = args['mz_tol']
        scan_dict['ook0'] = args['ook0']
        scan_dict['ook0_tol'] = args['ook0_tol']
        scan_dict['intensity'] = 0

        # Get 1/K0 values from scan numbers in run
        ook0_array = tims_scannum_to_oneoverk0(dll, tdf_data.handle, frame, range(0, frames_dict['NumScans']+1))
        # Get 1/K0 values within tolerance
        ook0_within_tolerance = [i for i in ook0_array
                                 if args['ook0'] + args['ook0_tol'] >= i >= args['ook0'] - args['ook0_tol']]
        # Get scan numbers for ook0 values within tolerance
        ook0_within_tolerance_scannums = tims_oneoverk0_to_scannum(dll, tdf_data.handle, frame, ook0_within_tolerance)
        ook0_within_tolerance_scannums = [int(i) for i in ook0_within_tolerance_scannums]

        # Read scans from current frame
        # each frame has N scans where each scan corresponds to a 1/K0 value
        list_of_scans = tims_read_scans_v2(dll,
                                           tdf_data.handle,
                                           frame,
                                           min(ook0_within_tolerance_scannums),
                                           max(ook0_within_tolerance_scannums)+1)
        scan_begin = 0
        scan_end = max(ook0_within_tolerance_scannums) + 1 - min(ook0_within_tolerance_scannums)
        for scan_num in range(scan_begin, scan_end):
            if list_of_scans[scan_num][0].size != 0 \
                    and list_of_scans[scan_num][1].size != 0 \
                    and list_of_scans[scan_num][0].size == list_of_scans[scan_num][1].size:
                mz_array = tims_index_to_mz(dll, tdf_data.handle, frame, list_of_scans[scan_num][0]).tolist()
                intensity_array = list_of_scans[scan_num][1].tolist()
                # Get indices of m/z values within tolerance
                indices = [mz_array.index(i) for i in mz_array
                           if args['mz'] + args['mz_tol'] >= i >= args['mz'] - args['mz_tol']]
                # Sum intensities if m/z value was found within tolerance of feature of interest
                # this summed intensity is the intensity of mz +/- mz_tol at ook0 +/- ook0_tol
                scan_dict['intensity'] += sum([intensity_array[i] for i in indices])
        list_of_scan_dicts.append(scan_dict)

    results = pd.DataFrame(list_of_scan_dicts)
    results.to_csv(os.path.join(args['outdir'], args['outfile']), index=False)


if __name__ == "__main__":
    run()
