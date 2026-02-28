FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1
ENV UV_ENV_WORKDIR=/app/recruitment_assistant

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --upgrade pip uv

COPY requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

COPY recruitment_assistant $UV_ENV_WORKDIR
WORKDIR $UV_ENV_WORKDIR

EXPOSE 8000 8501

CMD ["uv", "run", "uvicorn", "recruitment_assistant.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
