FROM python:3.10-slim

LABEL name="translator"
LABEL version="1.0"

WORKDIR /translator

COPY ./requirements.txt /translator/requirements.txt

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        g++ \
        python3-dev \
        && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir wheel \
    && pip install --no-cache-dir -r /translator/requirements.txt \
    && python -m unidic download

COPY ./app /translator/app

ENV PORT=3097
ENV PYTHONPATH=/translator
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3097"]