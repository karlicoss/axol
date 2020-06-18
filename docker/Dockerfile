FROM python:3.8
COPY requirements.txt .
RUN pip3 install --no-cache -r requirements.txt

# TODO not sure if should mount or copy?
COPY . /app
