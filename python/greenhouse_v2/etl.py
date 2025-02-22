import sys
import glob
import os
sys.path.append("./")

import xarray as xr
import numpy as np
import zipfile


def unzip_files_and_rename(directory: str):
  """Unzip the files and rename them to the original filename."""
  zip_files = glob.glob(f"{directory}/*.zip")
  print(f"Found {len(zip_files)} zip files")

  for file in zip_files:
    print("PROCESSING:", file)

    # Unzip the file:
    with zipfile.ZipFile(file, 'r') as zip_ref:
      zip_ref.extractall(directory)

    # All files uzip to data_0.nc, so we need to rename it to the original filename.
    filename = f"{directory}/data_0.nc"

    # Rename to match the original filename
    new_filename = f"{directory}/{file.split('/')[-1]}".replace(".zip", ".nc")
    os.rename(filename, new_filename)
    print(f"Renamed {filename} to {new_filename}")


def rename_nc_files_month_year(directory: str):
  """Rename the nc files to the month and year they contain."""
  for file in glob.glob(f"{directory}/*.nc"):
    print(file)

    ds = xr.open_dataset(file)
    month: int = ds.valid_time.dt.month.values[0]
    year: int = ds.valid_time.dt.year.values[0]
    print(f"This file is for {month}/{year}")

    # Rename to to the month and year
    new_filename = f"{directory}/{year}_{month:02d}.nc"

    # If the file already exists, skip it
    if os.path.exists(new_filename):
      print(f"File {new_filename} already exists, skipping")
      continue

    # Move the file to the new filename
    os.rename(file, new_filename)
    print(f"Renamed {file} to {new_filename}")


def calculate_monthly_hourly_means(filename: str, output_filename: str):
  """Compress the data into a smaller file by calculating the mean of the data for each month and hour."""
  ds = xr.open_dataset(
    filename,
    # chunks={'valid_time': -1, 'latitude': 100, 'longitude': 100}
  )
  print("Opened dataset")

  # Get the month that this data represents
  month = ds.valid_time.dt.month.values[0]
  year = ds.valid_time.dt.year.values[0]

  # Create new coordinate arrays with round numbers
  new_lats = np.arange(-90, 90, 0.5)  # 0.5° grid from -90 to 90
  new_lons = np.arange(0, 360, 0.5)   # 0.5° grid from 0 to 359.5

  # Interpolate to the new grid (this preserves data better than simple slicing)
  downsampled = ds.interp(latitude=new_lats, longitude=new_lons)

  downsampled = downsampled.assign_coords(
    month=downsampled.valid_time.dt.month,
    hour=downsampled.valid_time.dt.hour
  )

  print("Assigned coords")

  # Group by month and hour and compute the mean
  # This will handle both t2m and ssrd variables
  monthly_hourly_means = downsampled.groupby(['month', 'hour']).mean()
  # print(monthly_hourly_means)

  # Change all data variables to float32
  monthly_hourly_means = monthly_hourly_means.astype({
    var: 'float32' for var in monthly_hourly_means.data_vars
  })

  print("Grouped by month and hour")

  # Save the results to a new, much smaller NetCDF file
  monthly_hourly_means.to_netcdf(output_filename)

  print("Saved results")

  # Close the dataset
  ds.close()


def merge_monthly_hourly_files(merge_files: list[str]):
  """Merge the monthly hourly files into a single file."""
  if len(merge_files) != 12:
    raise ValueError(f"Expected 12 files, got {len(merge_files)}")

  # Concatenate the files:
  datasets = []

  # Open each file and add to list
  for file in merge_files:
    ds = xr.open_dataset(file)
    datasets.append(ds)
      
  # Concatenate along the 'month' dimension
  # Note: Make sure each file has a 'month' coordinate that's unique
  return xr.concat(datasets, dim='month')


if __name__ == "__main__":
  ### TEMPERATURE AND SOLAR RADIATION ###
  # Unzip all files in the directory
  # unzip_files_and_rename("./data/era5/zips")
  # rename_nc_files_month_year("./data/era5/zips")

  ### HUMIDITY ###
  # rename_nc_files_month_year("./data/era5/d2m")

  # Calculate the monthly hourly means
  # d2m_files = glob.glob("./data/era5/d2m/*.nc")
  # for input_filename in d2m_files:
  #   output_filename = input_filename.replace(".nc", "_hourly_means.nc")
  #   calculate_monthly_hourly_means(input_filename, output_filename)

  ### MERGE MONTHLY HOURLY FILES ###
  merge_files = glob.glob("./data/era5/d2m/*_hourly_means.nc")
  print(f"Found {len(merge_files)} files to merge")
  merged_data = merge_monthly_hourly_files(merge_files)
  merged_data.to_netcdf("./data/era5/d2m/complete_month_hour_data_2023.nc")
  print("DONE")
