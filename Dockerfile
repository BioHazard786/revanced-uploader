FROM python:3.13-alpine

WORKDIR /app

# tgcrypto and uvloop need a C compiler on Alpine
RUN apk add --no-cache --virtual .build-deps \
        gcc \
        musl-dev

# Copy project files and install
COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir . \
    && apk del .build-deps

# Non-root user
RUN adduser -D -u 1000 bot \
    && mkdir -p /app/data \
    && chown -R bot:bot /app/data

USER bot

CMD ["python", "-m", "revanced_bot"]
