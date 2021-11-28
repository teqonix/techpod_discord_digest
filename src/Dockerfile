ARG application_credentials

FROM python:3.8-slim

RUN mkdir /digest_bot
RUN mkdir /digest_bot/secret_store

COPY ./requirements.txt /digest_bot/

RUN pip install -r /digest_bot/requirements.txt

COPY ./ /digest_bot
# TODO: Update container to pull secrets from GCP Secret Store - this is terrible
COPY ./secret_store/* /digest_bot/secret_store/

ENV GOOGLE_APPLICATION_CREDENTIALS=/data/techpod_runner_sa_secret.json

CMD /digest_bot/start.sh