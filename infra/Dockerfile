FROM python:3.12-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends openjdk-17-jre-headless \
    && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 \
    PYSPARK_PYTHON=python \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/work/src \
    DBT_SEND_ANONYMOUS_USAGE_STATS=false \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /opt/build
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir ".[dev]"

WORKDIR /work
ENTRYPOINT ["python"]
