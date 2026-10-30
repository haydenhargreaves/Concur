FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl nginx supervisor \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY fusion_dashboard/requirements.txt fusion_dashboard/requirements.txt
RUN pip install --no-cache-dir -r fusion_dashboard/requirements.txt

# node_b_bridge.py imports this classifier so both components use the same states.
COPY node_b_sensors/python/classifier.py node_b_sensors/python/classifier.py
COPY fusion_dashboard fusion_dashboard

COPY landing/index.html /usr/share/nginx/html/landing/index.html
COPY landing/assets /usr/share/nginx/html/landing/assets
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY docker/supervisord.conf /etc/supervisor/conf.d/concur.conf

RUN rm -f /etc/nginx/sites-enabled/default

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl --fail http://localhost/_stcore/health || exit 1

CMD ["/usr/bin/supervisord", "-n"]
