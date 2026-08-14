FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && python -c "import nltk; nltk.download('vader_lexicon')"

# ML modules live in /ml at the repo root (mounted via docker-compose)
ENV PYTHONPATH=/ml:/app
ENV HF_HOME=/ml/hf-cache

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
