FROM python:3.11-slim

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Static ffmpeg/ffprobe (multi-arch image; buildx selects the right arch)
# instead of the Debian ffmpeg package, which drags in a large GUI/codec
# dependency tree (SDL2, mesa, pango, pocketsphinx, ...).
COPY --from=mwader/static-ffmpeg:7.1 /ffmpeg /ffprobe /usr/local/bin/

# ca-certificates for outbound HTTPS (the slim base omits them; aiohttp uses
# the system trust store). Retries guard against transient mirror hiccups.
RUN echo 'Acquire::Retries "5";' > /etc/apt/apt.conf.d/80-retries \
    && apt-get update && apt-get install -y --no-install-recommends ca-certificates \
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

