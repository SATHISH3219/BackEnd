#!/bin/bash
echo "Installing dependencies..."
python3 -m pip install --upgrade pip
pip install -r requirements.txt
echo "Dependencies installed."