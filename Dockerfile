FROM python:3.11

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt
RUN echo 'Acquire::Retries "5";' > /etc/apt/apt.conf.d/80-retries \
    && apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY ./src ./src
COPY ./db ./db
COPY ./assets ./assets
COPY ./fonts ./fonts
RUN mkdir ./logs

# Config and secrets are injected at runtime via docker-compose `env_file`
# (see .env / .env.example). The image is intentionally config-free so it can
# be reused across environments and never bakes secrets into its layers.

CMD [ "python", "./src/bot.py" ]

