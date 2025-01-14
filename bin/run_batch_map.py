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
                        required=True,
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

    # Display the resulting DataFrame with the modified columns
    print(results)
    
    # Split the 'Spot' column into two new columns 'index' and 'integer'
    results[['index', 'integer']] = results['Spot'].str.extract('([A-Za-z]+)(\d+)', expand=True)

    # Group by 'Frame', 'Spot', 'index' and 'integer', and calculate sum of intensities for numerator, denominator, and internal standard if provided 
    group_columns = ['Frame', 'Spot', 'index', 'integer']
    results['numerator_intensity'] = results[results['ook0'] == args['numerator_ook0']].groupby(group_columns, as_index=False)['intensity'].transform('sum')
    results['denominator_intensity'] = results[results['ook0'] == args['denominator_ook0']].groupby(group_columns, as_index=False)['intensity'].transform('sum')
    results['IS_intensity'] = results[results['mz'] == args['IS_mz']].groupby(group_columns, as_index=False)['intensity'].transform('sum')
    
    #Group by 'Frame', 'Spot', 'index' and 'integer'
    grouped_results = results.groupby(group_columns, as_index=False)[['numerator_intensity', 'denominator_intensity','IS_intensity']].sum()
    grouped_results.to_csv(os.path.join(args['outdir'], 'modified_outfile.csv'), index=False)

    # Calculate the ratio based on 'numerator_intensity' and 'denominator_intensity'
    grouped_results['ratio'] = grouped_results['numerator_intensity'] / grouped_results['denominator_intensity']

    #normalize to internal standard
    grouped_results['n_ratio'] = (grouped_results['ratio'] / grouped_results['IS_intensity'])

    # Save the result to a new CSV file
    grouped_results.to_csv(os.path.join(args['outdir'], 'modified_outfile.csv'), index=False)

    # Display the resulting DataFrame with the modified columns
    print(grouped_results)

    # Group by 'index' and 'integer', then aggregate using the mean of 'ratio'
    heatmap_data = grouped_results[grouped_results['n_ratio'] != '-'].groupby(['index', 'integer'])['n_ratio'].mean().unstack()

    # Convert the data type of 'ratio' to float
    heatmap_data = heatmap_data.astype(float)

    # Save the result to a new CSV file
    heatmap_data.to_csv(os.path.join(args['outdir'], 'heatmap_data.csv'), index=False)

    # Create a heatmap of the calculated ratios using seaborn
    plt.figure(figsize=(10, 8))
    sns.heatmap(heatmap_data, annot=False, cmap='viridis', fmt=".2f", cbar_kws={'label': 'Normalized Ratio'})
    plt.title('Heatmap of Mean Ratio Values')
    plt.xlabel('Integer')
    plt.ylabel('Index')
    plt.show()

if __name__ == "__main__":
    run()




