ARG application_credentials

FROM python:3.8-slim

RUN mkdir /digest_bot
RUN mkdir /digest_bot/secret_store

COPY ./requirements.txt /digest_bot/

RUN pip install -r /digest_bot/requirements.txt

COPY ./ /digest_bot

ENV GOOGLE_APPLICATION_CREDENTIALS=/data/techpod_runner_sa_secret.json

CMD python3 /digest_bot/main.py