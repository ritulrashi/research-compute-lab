FROM ubuntu:26.04@sha256:f144425ff09be612d6d9ad965196e9cdc23dae1f42110a8a11a3e9a8198759f7
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends slurm-wlm munge supervisor python3 ansible-core curl ca-certificates && rm -rf /var/lib/apt/lists/*
RUN useradd --uid 2000 --create-home --shell /bin/bash researcher
COPY infra /opt/infra
COPY workload.py distributed.py exporter.py /opt/lab/
WORKDIR /opt/lab
ENTRYPOINT ["bash", "/opt/infra/entrypoint.sh"]
