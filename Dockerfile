FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY data/ ./data/

# Create cron job
RUN echo "0 0 * * * cd /app && python src/ingestion/fetch_congress_data.py >> /var/log/cron.log 2>&1" > /etc/cron.d/capitolscope
RUN chmod 0644 /etc/cron.d/capitolscope
RUN crontab /etc/cron.d/capitolscope

# Create log file
RUN touch /var/log/cron.log

# Copy startup script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Expose port for health checks
EXPOSE 8000

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["cron", "-f"] 