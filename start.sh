#!/bin/bash

# Create data directories if they don't exist
mkdir -p /app/data/grades
mkdir -p /app/data/submissions  
mkdir -p /app/data/final_pdfs
mkdir -p /app/data/merged_pdfs
mkdir -p /app/data/debug_outputs

# Set proper permissions
chmod -R 755 /app/data

# Start webhook server in background
python webhook_server.py &
WEBHOOK_PID=$!

# Start the Streamlit app
streamlit run app/streamlit_app.py --server.port=8080 --server.address=0.0.0.0 --server.headless=true &
STREAMLIT_PID=$!

# Wait for either process to exit
wait $STREAMLIT_PID $WEBHOOK_PID
