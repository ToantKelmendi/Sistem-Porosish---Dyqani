# Imazh i vogël dhe i riprodhueshëm: version i pinuar i Python-it, varësitë
# instalohen para kopjimit të kodit që të ripërdoret cache-i i shtresave.
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
