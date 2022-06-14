FROM python:3.10-alpine3.15

ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_NO_INTERACTION=1

RUN apk add --no-cache --virtual .python_deps build-base python3-dev libffi-dev bash && \
    pip3 install poetry && \
    apk del .python_deps && \
    mkdir -p /app/src /app && \
    poetry config virtualenvs.create false

ADD src /app/src
ADD pyproject.toml /app/pyproject.toml

WORKDIR /app
ENV PYTHONPATH=${PYTHONPATH}:/app

RUN apk add --no-cache --virtual .build_deps gcc g++ && \
      poetry install --no-dev && \
      apk del .build_deps

CMD ["kopf", "run", "--liveness=http://0.0.0.0:8080/health", "/app/src/tailscale_svc_lb_controller/main.py"]
