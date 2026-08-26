FROM python:3.11

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update && apt-get install -y ffmpeg

COPY ./src ./src
COPY ./db ./db
COPY ./assets ./assets
COPY ./fonts ./fonts
RUN mkdir ./logs

# Config and secrets are injected at runtime via docker-compose `env_file`
# (see .env / .env.example). The image is intentionally config-free so it can
# be reused across environments and never bakes secrets into its layers.

CMD [ "python", "./src/bot.py" ]

