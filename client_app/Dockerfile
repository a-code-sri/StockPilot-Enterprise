# FreshBasket Online: customer web shop that runs on the StockPilot API.
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 SHOP_DATA_DIR=/data
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY server.py .
COPY static static
RUN useradd --create-home --uid 10001 app && mkdir -p /data && chown app /data
USER app
EXPOSE 8501
HEALTHCHECK --interval=15s --timeout=4s --start-period=10s \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8501/healthz', timeout=3).status == 200 else 1)"
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8501", "--proxy-headers"]
