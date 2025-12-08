FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .


RUN pip install --no-cache-dir -r requirements.txt


COPY src/ src/

RUN mkdir -p data/raw models


ENV PREFECT_API_URL="http://host.docker.internal:4200/api"


CMD ["python", "src/main_flow.py"]