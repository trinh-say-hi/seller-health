# Dung toan bo kho va DSS ngay luc build, nen chay container la mo app ngay.
FROM python:3.13-slim

ENV PYTHONUTF8=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    OLIST_DB=/app/db/olist.duckdb \
    OLIST_HOME=/app/db

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Kiem tra hash CSV, nap 26 dot, chay DSS, sinh catalog, chay 126 test. Test hong thi build dung.
RUN mkdir -p /app/db && python run_all.py

EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"
CMD ["python", "-m", "streamlit", "run", "src/app/app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
