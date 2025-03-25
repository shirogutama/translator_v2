FROM python:3.10-bullseye

LABEL name="translator"
LABEL version="1.0"

WORKDIR /translator

COPY ./requirements.txt /translator/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /translator/requirements.txt && \
    python -m unidic download

COPY ./app /translator/app

CMD ["sh", "-c", "fastapi run app/main.py --port $PORT"]