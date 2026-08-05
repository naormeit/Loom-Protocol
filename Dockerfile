FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
COPY run.py ./
COPY core ./core
COPY sdk ./sdk

RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -e .

EXPOSE 8080

CMD ["loom-api"]
