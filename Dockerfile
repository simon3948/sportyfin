FROM python:3.8-slim-buster

WORKDIR /sportyfin
# Copy requirements first (for caching)
COPY requirements.txt .

RUN pip install --no-cache-dir --requirement requirements.txt

# Now copy the rest of your code
COPY . .

CMD [ "python3", "-m" , "sportyfin.py", "run", "-a", "-o", "/sportyfin/output"]
