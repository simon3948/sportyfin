FROM python:3.8-slim-bookworm

WORKDIR /sportyfin

# Install Chromium and chromedriver and required deps
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       chromium chromium-driver
       #fonts-liberation \
       #libnss3 libatk-bridge2.0-0 libgtk-3-0 libdrm2 libxkbcommon0 libxcb1 libxcomposite1 libxdamage1 libxfixes3 libgbm1 libasound2

# Copy requirements first (for caching)
COPY requirements.txt .

RUN pip install --no-cache-dir --requirement requirements.txt

# Now copy the rest of your code
COPY . .

# Default command
CMD [ "python3", "-m" , "sportyfin", "run", "-f1", "-o", "-v", "/sportyfin/output"]