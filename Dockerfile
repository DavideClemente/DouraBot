FROM python:3.11

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update && apt-get install -y ffmpeg

COPY ./src ./src
COPY ./db ./db
COPY ./assets ./assets
COPY ./fonts ./fonts
RUN mkdir ./logs

# ENVIRONMENT VARIABLES

ARG TOKEN_PROD
ARG DOURADINHOS
ARG CURRENCY_API_KEY
ARG CLOUDFLARE_WORKER
ARG SPOTIFY_CLIENT_ID
ARG SPOTIFY_CLIENT_SECRET

ENV TOKEN_PROD=$TOKEN_PROD
ENV DOURADINHOS=$DOURADINHOS
ENV CURRENCY_API_KEY=$CURRENCY_API_KEY
ENV CLOUDFLARE_WORKER=$CLOUDFLARE_WORKER
ENV SPOTIFY_CLIENT_ID=$SPOTIFY_CLIENT_ID
ENV SPOTIFY_CLIENT_SECRET=$SPOTIFY_CLIENT_SECRET

CMD [ "python", "./src/bot.py" ]

