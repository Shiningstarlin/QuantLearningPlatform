FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DEFAULT_TIMEOUT=120
ENV PIP_RETRIES=10

WORKDIR /app

ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn

COPY requirements.txt .
RUN python -m pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --timeout 120 --retries 10 \
        -i ${PIP_INDEX_URL} --trusted-host ${PIP_TRUSTED_HOST} \
        -r requirements.txt

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
