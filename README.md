# timstof_targeted_3d_maldi_analysis

This Python script allows for users to extract the summed intensity for a given feature (where a feature is an m/z-1/K0 
pair) from MALDI-TIMS-MS data acquired on the timsTOF fleX using timsControl in AutoXecute mode. It is intended for 
non-imaging automated runs for high throughput screening purposes. The output is a CSV table where each row is the 
summed intensity of the feature +/- tolerance for each spot from an MTP plate.

#### macOS IS NOT SUPPORTED!

Bruker's TDF-SDK is currently only compatible with Windows and Linux.

## Installation

This script has been tested using a conda virtual environment. While other virtual environments or setups may function, 
there is no guarantee that the script will be compatible with other environments. Instructions to reproduce the 
environment used during development are below.

1. If not installed, install Anaconda from [here](https://www.anaconda.com/download).

2. Open `Anaconda Prompt`.

3. Create a new conda virtual environment:
```
conda create -n timstof_targeted_3d_maldi_analysis python=3.11
```

4. Activate the venv:
```
conda activate timstof_targeted_3d_maldi_analysis
```

5. Install this package:
```
pip install git+https://github.com/gtluubruker/timstof_targeted_3d_maldi_analysis
```

## Usage

The `run.py` script can be run in `Anaconda Prompt` when the `timstof_targeted_3d_maldi_analysis` venv created during 
installation is activated.

For help, use: `python run.py --help`. Parameters are also described below.

#### Parameters

`get_feature_intensities`: used for features entered from the command line<br>
`--input`: File path for Bruker .d file from MALDI AutoXecute run containing TDF file.<br>
`--outdir`: Path to folder in whch to write output CSV file. Default = same as input path.<br>
`--outfile`: User defined filename for output CSV file. Will use the ".d" directory name if none is specified.<br>
`--mz`: One or more m/z value(s) of interest. Must be equal to the num of 1/K0 values entered.<br>
`--mz_tol`: One or more m/z tolerance(s) in Da. Default = 0.05 Da<br>
`--ook0`: One or more 1/K0 value(s) of interest. Must be equal to the num of m/z values entered.<br>
`--ook0_tol`: One or more 1/K0 tolerance(s). Default = 0.05<br>

`get_batch_feature_intensities`: used for features from a CSV file<br>
`--input`: File path for Bruker .d file from MALDI AutoXecute run containing TDF file.<br>
`--outdir`: Path to folder in which to write output CSV file. Default = same as input path.<br>
`--outfile`: User defined filename for output CSV file. Will use the ".d" directory name if none is specified.<br>
`--feature_list`: CSV file w/ columns for "mz", "mz_tol", "ook0", and "ook0_tol" to define features.<br>

`get_feature_map`: used for features from a CSV file<br>
`--input`: File path for Bruker .d file from MALDI AutoXecute run containing TDF file.<br>
`--outdir`: Path to folder in whch to write output CSV file. Default = same as input path.<br>
`--outfile`: User defined filename for output CSV file. Will use the ".d" directory name if none is specified.<br>
`--feature_list`: CSV file w/ columns for "mz", "mz_tol", "ook0", and "ook0_tol" to define features.<br>
`--numerator_ook0`: User-defined 1/K0 value for the desired feature to be used as the numerator in intensity ratio calculation.<br>
`--denominator_ook0`: User-defined 1/K0 value for the desired feature to be used as the denominator in intensity ratio calculation.<br>

### Examples

Example input data can be found in [data/maldi_ms1_tims_autox.zip](https://github.com/gtluubruker/timstof_targeted_3d_maldi_analysis/blob/main/data/maldi_ms1_tims_autox.zip) (unzip to find a .d file).<br>
Example feature list can be found in [data/maldi_ms1_tims_autox_features.csv](https://github.com/gtluubruker/timstof_targeted_3d_maldi_analysis/blob/main/data/maldi_ms1_tims_autox_features.csv)

#### Get Feature Intensities for a Single Feature
```
get_feature_intensities --input [path to]/maldi_ms1_tims_autox/maldi_ms1_tims_autox.d --mz 622.0250 --mz_tol 0.05 --ook0 0.982 --ook0_tol 0.05
```

Example output data can be found in [data/maldi_ms1_tims_autox_single.csv](https://github.com/gtluubruker/timstof_targeted_3d_maldi_analysis/blob/main/data/maldi_ms1_tims_autox_single.csv)

#### Get Feature Intensities for Multiple Features
```
get_feature_intensities --input [path to]/maldi_ms1_tims_autox/maldi_ms1_tims_autox.d --mz 622.0250 922.0140 --mz_tol 0.05 --ook0 0.982 1.190 --ook0_tol 0.05
```

Alternatively, unique tolerances can be used for each feature.

```
get_feature_intensities --input [path to]/maldi_ms1_tims_autox/maldi_ms1_tims_autox.d --mz 622.0250 922.0140 --mz_tol 0.05 0.10 --ook0 0.982 1.190 --ook0_tol 0.05 0.10
```

Example output data can be found in [data/maldi_ms1_tims_autox_multiple.csv](https://github.com/gtluubruker/timstof_targeted_3d_maldi_analysis/blob/main/data/maldi_ms1_tims_autox_multiple.csv)

#### Get Feature Intensities for Multiple Features Listed in a CSV File (Batch Processing)
```
get_batch_feature_intensities --input [path to]/maldi_ms1_tims_autox/maldi_ms1_tims_autox.d --feature_list [path to]/maldi_ms1_tims_autox_features.csv
```

Example output data can be found in [data/maldi_ms1_tims_autox_batch.csv](https://github.com/gtluubruker/timstof_targeted_3d_maldi_analysis/blob/main/data/maldi_ms1_tims_autox_batch.csv)

#### Calculate and Visualize Ratios Between Features Listed in a CSV File (Batch Processing + Visualization)
```
get_feature_map --input [path to]/maldi_ms1_tims_autox/maldi_ms1_tims_autox.d --feature_list [path to]/maldi_ms1_tims_autox_features.csv --numerator_ook0 0.683 --denominator_ook0 0.703
```
