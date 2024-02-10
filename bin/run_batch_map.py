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
import seaborn as sns
import matplotlib.pyplot as plt

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
    parser.add_argument('--feature_list',
                        help='CSV file w/ columns for "mz", "mz_tol", "ook0", and "ook0_tol" to define features.',
                        required=True,
                        type=str)
    parser.add_argument('--numerator_ook0',
                        help='User defined ook0 value to be used as the numerator in ratio calculation.',
                        required=True,
                        type=float)
    parser.add_argument('--denominator_ook0',
                        help='User defined ook0 value to be used as the denominator in ratio calculation.',
                        required=True,
                        type=float)
    parser.add_argument('--IS_mz',
                        help='User defined m/z value for the feature to be used as the internal standard for intensity normalization.',
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

    feature_df = pd.read_csv(args['feature_list'])

    # Load TDF data
    dll = init_tdf_sdk_api()
    tdf_data = TdfData(args['input'], dll)

    list_of_scan_dicts = []

    for index, row in feature_df.iterrows():
        mz = row['mz']
        mz_tol = row['mz_tol']
        ook0 = row['ook0']
        ook0_tol = row['ook0_tol']

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
                    mz_array = tims_index_to_mz(dll, tdf_data.handle, frame, list_of_scans[scan_num][0])
                    intensity_array = list_of_scans[scan_num][1]

                    for mz_value, intensity in zip(mz_array, intensity_array):
                        if mz + mz_tol >= mz_value >= mz - mz_tol:
                            scan_dict['intensity'] += intensity

            list_of_scan_dicts.append(scan_dict)

    intensity_df = pd.DataFrame(list_of_scan_dicts)

    if args['IS_mz']:
        IS_intensity = intensity_df.loc[intensity_df['mz'] == args['IS_mz'], 'intensity'].mean()
        intensity_df['normalized_intensity'] = intensity_df['intensity'] / IS_intensity
    else:
        intensity_df['normalized_intensity'] = intensity_df['intensity']

    # Apply logarithmic transformation to normalized intensity values
    intensity_df['log_normalized_intensity'] = np.log1p(intensity_df['normalized_intensity'])

    # Calculate ratio using the provided numerator and denominator ook0 values
    intensity_df['ratio'] = intensity_df['ook0'].apply(lambda x: args['numerator_ook0'] / x) \
                            * intensity_df['normalized_intensity']

    # Write the DataFrame to a CSV file
    output_path = os.path.join(args['outdir'], args['outfile'])
    intensity_df.to_csv(output_path, index=False)

    # Plotting
    sns.scatterplot(data=intensity_df, x='ook0', y='ratio', hue='Spot', palette='tab10')
    plt.title('Ratio vs. ook0')
    plt.xlabel('ook0')
    plt.ylabel('Ratio')
    plt.show()


if __name__ == '__main__':
    run()


