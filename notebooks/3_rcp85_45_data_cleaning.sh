#!/bin/bash -l
#SBATCH --job-name=3_rcp85_45_data_cleaning
#SBATCH --output=3_rcp85_45_data_cleaning.log
#SBATCH --partition=seseml
#SBATCH --ntasks=1                 # Dask Scheduler is a single task
#SBATCH --cpus-per-task=1          # Scheduler does not need many CPUs
#SBATCH --mem=220GB                 # Memory for the scheduler
#SBATCH --time=23:00:00            # Total runtime

# Load Conda
echo "Sourcing Conda"
source /data/keeling/a/ctavila2/mambaforge/etc/profile.d/conda.sh || { echo "Failed to source conda.sh"; exit 1; }
echo "Activating WFPIenv"
conda activate FWI || { echo "Failed to activate FWI env"; exit 1; }

# Launch Dask Scheduler
echo "Starting Dask Scheduler"
dask-scheduler --host 0.0.0.0 &  # Starts the scheduler on this node
sleep 5  # Give it time to start

# Launch Dask Workers
echo "Launching Dask Workers"
for i in {1..10}; do
    srun --exclusive --ntasks=1 --cpus-per-task=1 --mem=20GB dask-worker tcp://127.0.0.1:8786 --nthreads=1 --memory-limit=20GB &
done

# Run the Python script
echo "Running Python script"
python 3_rcp85_45_data_cleaning.py || { echo "Python script execution failed"; exit 1; }

# Wait for workers to finish
wait

echo "Job completed"
