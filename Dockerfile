FROM python:3.8-slim

RUN mkdir /usr/local/digest_bot
RUN mkdir /usr/local/digest_bot/secret_store

COPY ./requirements.txt /usr/local/digest_bot/

RUN pip install -r /usr/local/digest_bot/requirements.txt

COPY ./ /usr/local/digest_bot/
# TODO: Update container to pull secrets from GCP Secret Store - this is terrible
COPY ./secret_store/* /usr/local/digest_bot/secret_store/

CMD python3 /usr/local/digest_bot/main.py