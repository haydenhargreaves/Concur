# IEEE-CS-CC-Project-2026

## Deploying the web application

The landing page and Fusion Dashboard are published together as one image:

```bash
docker compose pull
docker compose up -d
```

This serves the dashboard at `/` and the landing page at `/landing/`. The
published image is `ghcr.io/haydenhargreaves/concur-fusion-dashboard:master`;
it is rebuilt and pushed by GitHub Actions on changes to either web application.

For a local image build instead:

```bash
docker build -t concur-web:local .
docker run --rm -p 80:80 concur-web:local
```
