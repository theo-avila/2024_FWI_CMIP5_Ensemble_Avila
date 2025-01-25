#!/bin/bash -l
#SBATCH --job-name=0cmip5cleaning
#SBATCH --output=0cmip5cleaning_output.log
#SBATCH --partition=seseml
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=220GB
#SBATCH --time=23:00:00

# Load Conda
echo "Sourcing Conda"
source /data/keeling/a/ctavila2/mambaforge/etc/profile.d/conda.sh || { echo "Failed to source conda.sh"; exit 1; }
echo "Activating WFPIenv"
conda activate FWI || { echo "Failed to activate FWI env"; exit 1; }

# Run the Python script
echo "Running Python script"
python 0_CMIP5_datacleaning.py || { echo "Python script execution failed"; exit 1; }

echo "Job completed"