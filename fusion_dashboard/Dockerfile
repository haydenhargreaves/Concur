
FROM public.ecr.aws/docker/library/python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY fusion_dashboard/requirements.txt fusion_dashboard/requirements.txt
RUN pip install --no-cache-dir -r fusion_dashboard/requirements.txt

# node_b_bridge.py imports classifier.py from here so the two states stay in sync.
COPY node_b_sensors/python/classifier.py node_b_sensors/python/classifier.py
COPY fusion_dashboard fusion_dashboard

WORKDIR /app/fusion_dashboard

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
