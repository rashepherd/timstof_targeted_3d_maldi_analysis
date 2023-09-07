# timstof_targeted_3d_maldi_analysis

This Python script allows for users to extract the summed intensity for a given feature (where a feature is an m/z-1/K0 pair) from MALDI-TIMS-MS data acquired on the timsTOF fleX using timsControl in AutoXecute mode. It is intended for non-imaging automated runs for high throughput screening purposes. The output is a CSV table with the frame where each row is the summed intensity of the feature +/- tolerance for each spot from an MTP plate.

## Installation

This script has been tested using a conda virtual environment. While other virtual environments or setups may function, there is no guarantee that the script will be compatible with other environments. Instructions to reproduce the environment used during development are below.

1. If not installed, install Anaconda from [here](https://www.anaconda.com/download).
2. If not installed, install Git from [here](https://git-scm.com/downloads).
3. Open `Anaconda Prompt`.
4. Navigate to the directory where you want to store this project.
5. Example:
```cd C:\Users\[username]\Desktop```
6. In `Anaconda Prompt`, clone this repo from Github using the following command:
```git clone https://github.com/gtluubruker/timstof_targeted_3d_maldi_analysis```
7. Navigate to the clone repo.
8. Example:
```cd C:\Users\[username]\Desktop\timstof_targeted_3d_maldi_analysis```
9. Create a new conda virtual environment:
```conda create -n timstof_targeted_3d_maldi_analysis python=3.11```
10. Activate the venv:
```conda activate timstof_targeted_3d_maldi_analysis```
11. Install Python dependencies:
```pip install -r requirements.txt```
12. You will also need to install the [pyTDFSDK](https://github.com/gtluu/pyTDFSDK) package directly from Github:
```pip install git+https://github.com/gtluu/pyTDFSDK```

## Usage

The `run.py` script can be run in `Anaconda Prompt` when the `timstof_targeted_3d_maldi_analysis` venv created during installation is activated.

For help, use: `python run.py --help`. Parameters are also described below.

#### Parameters

`--input`: File path for Bruker .d file from MALDI AutoXecute run containing TDF file.<br>
`--outdir`: Path to folder in whch to write output CSV file. Default = same as input path.<br>
`--outfile`: User defined filename for output CSV file. Will use the ".d" directory name if none is specified.<br>
`--mz`: m/z value of interest<br>
`--mz_tol`: m/z tolerance in Da. Default = 0.05 Da<br>
`--ook0`: 1/K0 value of interest<br>
`--ook0_tol`: 1/K0 tolerance. Default = 0.05<br>

#### Example Usage

`python run.py --input maldi_ms1_tims_autox/maldi_ms1_tims_autox.d --mz 622.0250 --mz_tol 0.05 --ook0 0.982 --ook0_tol 0.05`

#### Example Data

Example input data can be found in [data/maldi_ms1_tims_autox.zip](https://github.com/gtluubruker/timstof_targeted_3d_maldi_analysis/blob/main/data/maldi_ms1_tims_autox.zip).<br>
Example output data can be found in [data/maldi_ms1_tims_autox.zip](https://github.com/gtluubruker/timstof_targeted_3d_maldi_analysis/blob/main/data/maldi_ms1_tims_autox.csv)
