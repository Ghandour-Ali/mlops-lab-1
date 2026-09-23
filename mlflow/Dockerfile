FROM python:3.11.13-slim-bookworm
RUN pip install --no-cache-dir mlflow==3.16.0
RUN useradd --create-home --uid 10001 appuser && mkdir /mlflow-data && chown appuser /mlflow-data
USER appuser
EXPOSE 5000
CMD ["mlflow", "server", "--host", "0.0.0.0", "--port", "5000", "--workers", "1", "--backend-store-uri", "sqlite:////mlflow-data/mlflow.db", "--serve-artifacts", "--artifacts-destination", "/mlflow-data/mlartifacts", "--default-artifact-root", "mlflow-artifacts:/", "--allowed-hosts", "mlflow:5000,localhost:*,127.0.0.1:*"]
