FROM python:3.11

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt
# RUN apt-get update && apt-get install -y ffmpeg

COPY ./src ./src
COPY ./db ./db
COPY ./assets ./assets
RUN mkdir ./logs

# ENVIRONMENT VARIABLES
ENV TOKEN_PROD=$TOKEN_PROD
ENV DOURADINHOS=$DOURADINHOS
ENV CURRENCY_API_KEY=$CURRENCY_API_KEY
ENV CLOUDFLARE_WORKER=$CLOUDFLARE_WORKER

CMD [ "python", "./src/bot.py" ]

