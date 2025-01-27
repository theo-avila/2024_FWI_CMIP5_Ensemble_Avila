import matplotlib.pyplot as plt
import numpy as np
from numpy import ma
import xarray as xr
import geopandas as gpd
import pandas as pd
import dask

# requires cartopy to be installed
import cartopy.feature as cfeature
import cartopy.io.shapereader as shpreader

import cartopy.crs as ccrs # for projection
import cartopy.feature as cfeature # for map features
from cartopy.util import add_cyclic_point
from matplotlib.axes import Axes
from cartopy.mpl.geoaxes import GeoAxes
#from matplotlib.colors import TwoSlopeNorm
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
from collections import Counter
import sys
import os
import time
from dask.distributed import Client, progress
import dask
import xarray as xr
import numpy as np

# Define functions for processing (unchanged from your script)
def process_dataset(file_path, start_day, end_day, lon_max, lon_min, lat_max, lat_min):
    # Open the dataset
    ds = xr.open_dataset(file_path)
    
    # Filter the dataset by time
    ds_filtered = ds.sel(time=slice('1979-01-01', '2090-10-31'))
    
    # Adjust longitude range from [0, 360] to [-180, 180]
    ds_filtered["lon"] = np.where(ds_filtered["lon"] > 180, ds_filtered["lon"] - 360, ds_filtered["lon"])
    ds_filtered = ds_filtered.sortby("lon")
    
    # Spatially subset the dataset
    bounded_ds = ds_filtered.where(
        (ds_filtered.lon >= lon_min) & (ds_filtered.lon <= lon_max) &
        (ds_filtered.lat >= lat_min) & (ds_filtered.lat <= lat_max),
        drop=True
    )
    
    filtered_ds = bounded_ds.groupby('time.year').apply(
            lambda x: x.where((x['time.dayofyear'] >= start_day) & (x['time.dayofyear'] <= end_day))
        )
    yearly_mean = filtered_ds.groupby("time.year").mean("time")
    
    annual_mean = yearly_mean.mean(['lon']).mean(['lat'])

    return annual_mean



def process_model(model, start_day, end_day, lon_max, lon_min, lat_max, lat_min, region):
    base_path_H = f"/data/keeling/a/davidcl2/d/MACA/FWI_RHmin/historical/out/comp/macav2metdata_fwi_{model}_r1i1p1_historical_"
    base_path_85 = f"/data/keeling/a/davidcl2/d/MACA/FWI_RHmin/rcp45/out/macav2metdata_fwi_{model}_r1i1p1_rcp45_"
    
    datasets = []

    # Process historical files
    for year in range(1975, 2004, 5):
        file_path = f"{base_path_H}{year}_{year + 4}_CONUS_daily.nc"
        datasets.append(dask.delayed(process_dataset)(file_path, start_day, end_day, lon_max, lon_min, lat_max, lat_min))

    # Process 2005 separately
    file_path_2005 = f"{base_path_H}2005_2005_CONUS_daily.nc"
    datasets.append(dask.delayed(process_dataset)(file_path_2005, start_day, end_day, lon_max, lon_min, lat_max, lat_min))

    # Process RCP 8.5 files
    for year in range(2006, 2090, 5):
        file_path = f"{base_path_85}{year}_{year + 4}_CONUS_daily.nc"
        datasets.append(dask.delayed(process_dataset)(file_path, start_day, end_day, lon_max, lon_min, lat_max, lat_min))

    # Concatenate datasets and compute the time series mean
    concatenated_ds = dask.delayed(xr.concat)(datasets, dim='time')
    time_series = dask.delayed(lambda ds: ds.mean(dim='time'))(concatenated_ds)

    output_path = f"/data/rsriver/a/ctavila2/FWI_cleaned/time_series/{region}_macav2metdata_fwi_{model}_r1i1p1_rcp4.5_tmaxrhmin_1979_2090_timeseries.nc"
    return dask.delayed(lambda ds: ds.to_netcdf(output_path))(time_series)

def coarsened_all(models, start_day, end_day, lon_max, lon_min, lat_max, lat_min, region):
    tasks = [process_model(model, start_day, end_day, lon_max, lon_min, lat_max, lat_min, region) for model in models]
    dask.compute(*tasks)

# Define regions
regions = {
    'SoCal': {'lon_max': -116.5, 'lon_min': -118.5, 'lat_min': 34, 'lat_max': 36},
    'NorCal': {'lon_max': -121, 'lon_min': -123, 'lat_min': 38.5, 'lat_max': 40.5},
}

start_day = 152
end_day = 304
models = [
    "BNU-ESM", "CNRM-CM5", "CSIRO-Mk3-6-0", "CanESM2", "GFDL-ESM2G", "GFDL-ESM2M", "HadGEM2-CC365", "HadGEM2-ES365",
    "IPSL-CM5A-LR", "IPSL-CM5A-MR", "IPSL-CM5B-LR", "MIROC-ESM-CHEM", "MIROC-ESM", "MIROC5", "bcc-csm1-1-m",
    "MRI-CGCM3", "bcc-csm1-1", "inmcm4"
]

# Start Dask Client
if __name__ == "__main__":
    client = Client("tcp://127.0.0.1:8786")  # Connect to Dask scheduler
    for region, bounds in regions.items():
        coarsened_all(models, start_day=start_day, end_day=end_day, region=region, **bounds)
