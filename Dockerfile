FROM python:3.8.0-alpine
ADD . /code
WORKDIR code
RUN pip install -r requirements.txt