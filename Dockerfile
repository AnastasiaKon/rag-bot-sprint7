FROM python:3.11-slim

WORKDIR /app
ENV PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/.hf \
    TOKENIZERS_PARALLELISM=false

# torch только CPU, чтобы образ был ~1 ГБ, а не 5
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Прогреваем модель эмбеддингов и собираем индекс при сборке образа
RUN python build_index.py --extra data/malicious

ENTRYPOINT ["python", "bot.py"]
