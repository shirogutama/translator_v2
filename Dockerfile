FROM --platform=linux/arm64 python:3.10-slim-bullseye

LABEL name="translator"
LABEL version="1.0"

WORKDIR /translator

COPY ./requirements.txt /translator/requirements.txt

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --upgrade -r /translator/requirements.txt

RUN python -m unidic download

COPY ./app /translator/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3097"]