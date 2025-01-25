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

from dask_jobqueue import SLURMCluster

cluster = SLURMCluster(cores=1,
                       processes=1,
                       memory="200GB",
                       walltime="23:00:00",
                      )

cluster.scale(1)

from dask.distributed import Client

client = Client(cluster)

models = ["BNU-ESM", "CNRM-CM5", "CSIRO-Mk3-6-0", "CanESM2", "GFDL-ESM2G", "GFDL-ESM2M", "HadGEM2-CC365", "HadGEM2-ES365", "IPSL-CM5A-LR",
         "IPSL-CM5A-MR", "IPSL-CM5B-LR", "MIROC-ESM-CHEM", "MIROC-ESM", "MIROC5", "bcc-csm1-1-m", "MRI-CGCM3", "bcc-csm1-1", "inmcm4"]
    

def coarsened_all(model, start_day, end_day, lon_max, lon_min, lat_max, lat_min):
    base_path_H = "/data/keeling/a/davidcl2/d/MACA/FWI_RHmin/historical/out/comp/macav2metdata_fwi_" + model + "_r1i1p1_historical_"
    base_path_85 = "/data/keeling/a/davidcl2/d/MACA/FWI_RHmin/rcp85/out/macav2metdata_fwi_" + model + "_r1i1p1_rcp85_"
    
    # Initialize an empty list to store the datasets
    datasets = []
    
    for year in range(1975, 2004, 5):
        # Construct the file path for the current 5-year range
        file_path = f"{base_path_H}{year}_{year + 4}_CONUS_daily.nc"
        
        # Open the dataset and append it to the list
        ds = xr.open_dataset(file_path)
        ds_1979_2010 = ds.sel(time=slice('1979-01-01', '2022-10-31'))

        # Use .groupby() to group the data by year
        grouped_ds = ds_1979_2010.groupby('time.year')
        
        # Use .where() to mask the days outside the desired range for each year
        selected_ds = grouped_ds.apply(lambda x: x.where((x['time.dayofyear'] >= start_day) & (x['time.dayofyear'] <= end_day)))
        
        # Drop any NaN values created by the mask
        selected_ds = selected_ds.dropna(dim='time', how='all')
        #annual_mean = selected_ds.groupby('time.year').mean(dim='time')
        selected_ds["lon"] = np.where(selected_ds["lon"] > 180, selected_ds["lon"] - 360, selected_ds["lon"])
        selected_ds = selected_ds.sortby("lon")
        
        annual_mean_boundaries = (
            selected_ds.where((selected_ds.lon >= lon_min) & (selected_ds.lon <= lon_max) & (selected_ds.lat >= lat_min) &
                              (selected_ds.lat <= lat_max), drop=True)
        )
        
        datasets.append(annual_mean_boundaries)

        
    filein2005 = (
        "/data/keeling/a/davidcl2/d/MACA/FWI_RHmin/historical/out/comp/macav2metdata_fwi_" + model + "_r1i1p1_historical_2005_2005_CONUS_daily.nc"
    )
    
    ds = xr.open_dataset(filein2005)
    ds_1979_2010 = ds.sel(time=slice('1979-01-01', '2022-10-31'))

    # Use .groupby() to group the data by year
    grouped_ds = ds_1979_2010.groupby('time.year')
    
    # Use .where() to mask the days outside the desired range for each year
    selected_ds = grouped_ds.apply(lambda x: x.where((x['time.dayofyear'] >= start_day) & (x['time.dayofyear'] <= end_day)))
    
    # Drop any NaN values created by the mask
    selected_ds = selected_ds.dropna(dim='time', how='all')
    #annual_mean = selected_ds.groupby('time.year').mean(dim='time')
    selected_ds["lon"] = np.where(selected_ds["lon"] > 180, selected_ds["lon"] - 360, selected_ds["lon"])
    selected_ds = selected_ds.sortby("lon")
    
    annual_mean_boundaries = (
        selected_ds.where((selected_ds.lon >= lon_min) & (selected_ds.lon <= lon_max) & (selected_ds.lat >= lat_min) &
                          (selected_ds.lat <= lat_max), drop=True)
    )
    
    datasets.append(annual_mean_boundaries)

    for year in range(2006, 2025, 5):
        
        file_path = f"{base_path_85}{year}_{year + 4}_CONUS_daily.nc"
        
        # Open the dataset and append it to the list
        ds = xr.open_dataset(file_path)
        ds_1979_2010 = ds.sel(time=slice('1979-01-01', '2022-10-31'))

        # Use .groupby() to group the data by year
        grouped_ds = ds_1979_2010.groupby('time.year')
        
        # Use .where() to mask the days outside the desired range for each year
        selected_ds = grouped_ds.apply(lambda x: x.where((x['time.dayofyear'] >= start_day) & (x['time.dayofyear'] <= end_day)))
        
        # Drop any NaN values created by the mask
        selected_ds = selected_ds.dropna(dim='time', how='all')
        #annual_mean = selected_ds.groupby('time.year').mean(dim='time')
        selected_ds["lon"] = np.where(selected_ds["lon"] > 180, selected_ds["lon"] - 360, selected_ds["lon"])
        selected_ds = selected_ds.sortby("lon")
        
        annual_mean_boundaries = (
            selected_ds.where((selected_ds.lon >= lon_min) & (selected_ds.lon <= lon_max) & (selected_ds.lat >= lat_min) &
                              (selected_ds.lat <= lat_max), drop=True)
        )
        
        datasets.append(annual_mean_boundaries)

    concatenated_ds = xr.concat(datasets, dim='time')

    output_path = (
        "/data/rsriver/a/ctavila2/FWI_cleaned/macav2metdata_fwi_" + model + "_r1i1p1_rcp8.5_tmaxrhmin_1979_2022_CONUS_daily_DASK_oregon.nc"
    )

    # Save the dataset to a .nc file
    concatenated_ds.to_netcdf(output_path)


lon_max = -114.016667
lon_min = -124.766667
lat_min = 32.025
lat_max = 50

delayed = []
for model in models: # only do for 5 models
    out = dask.delayed(coarsened_all)(model=model, start_day=152, end_day=304, 
                                      lon_max=-114.016667, lon_min=-124.766667, lat_max = 50, lat_min = 32.025)
    delayed.append(out)

results = dask.compute(*delayed)  # Specify distributed scheduler

