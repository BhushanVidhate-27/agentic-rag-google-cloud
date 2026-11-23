FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir . && useradd --uid 10001 --create-home appuser
USER appuser
EXPOSE 8080
CMD ["uvicorn", "agentic_rag.api:app", "--host", "0.0.0.0", "--port", "8080"]
