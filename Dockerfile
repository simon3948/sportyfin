FROM python:3.8-slim-buster

WORKDIR /sportyfin

RUN pip install --no-cache-dir -r ./requirements.txt

CMD [ "python3", "-m" , "sportyfin.py", "run", "-a", "-o", "/sportyfin/output"]
