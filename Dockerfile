# TODO: Update tag (supports Qurrent OS version and dev-specific tags)
FROM us-central1-docker.pkg.dev/qurrent-prod-02192025/qurrent-prod-02192025-docker-images/qurrent-os:0.9

WORKDIR /app

EXPOSE 8000

ARG GOOGLE_CLOUD_PROJECT
ARG GCP_REGION=us-central1

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .

# Make changes to the startup script as needed
COPY startup.sh /usr/local/bin/startup.sh
RUN chmod +x /usr/local/bin/startup.sh

ENTRYPOINT ["/usr/local/bin/startup.sh"]
