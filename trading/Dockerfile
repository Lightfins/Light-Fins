FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY trading/requirements.txt /app/trading/requirements.txt
RUN pip install --no-cache-dir -r /app/trading/requirements.txt

# Copy trading code
COPY trading/ /app/trading/

# Create workspace directories
RUN mkdir -p /app/trading/workspace/strategies \
    /app/trading/workspace/pinescript \
    /app/trading/data \
    /app/trading/logs

# Streamlit config
RUN mkdir -p /root/.streamlit
RUN echo '[server]\nheadless = true\nport = 8501\nenableCORS = false\nenableXsrfProtection = false\n' > /root/.streamlit/config.toml

EXPOSE 8501

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

CMD ["streamlit", "run", "trading/dashboard/app.py", "--server.address", "0.0.0.0"]
