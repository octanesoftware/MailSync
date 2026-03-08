FROM gilleslamiral/imapsync:latest

# Install Python and Flask for the API server
RUN apk add --no-cache python3 py3-pip && \
    pip3 install --no-cache-dir flask apscheduler

# Create app directory
WORKDIR /app

# Copy application files
COPY api_server.py /app/
COPY config.json /app/

# Expose API port
EXPOSE 5000

# Run the API server
CMD ["python3", "/app/api_server.py"]
