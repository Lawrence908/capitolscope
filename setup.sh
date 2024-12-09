# Update python
sudo apt-get update

# Install libpq-dev package 
sudo apt-get install libpq-dev

# Install python3-pip package
sudo apt-get install python3-pip

# Install venv package
sudo apt-get install python3-venv

# Create a virtual environment
python3 -m venv .venv

# Activate the virtual environment
source .venv/bin/activate

# Install the required packages
pip install -r requirements.txt