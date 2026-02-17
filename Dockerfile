# Chainhammer Docker image (minimal, load-testing focused)
FROM python:3.7-slim-bullseye

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=120

# OS deps:
# - expect: provides `unbuffer` used by chainhammer's tps.py streaming
# - build-essential/gcc + ssl/ffi: needed for some pip packages (e.g., pycryptodome)
RUN apt-get update && apt-get install -y --no-install-recommends \
      bash ca-certificates curl git jq \
      build-essential gcc \
      libffi-dev libssl-dev \
      expect \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/chainhammer

# Copy repo (your folder layout: ./chainhammer/*)
COPY chainhammer/ /opt/chainhammer/

# Copy patched run.sh from project root (same folder as Dockerfile)
COPY chainhammer/run.sh /opt/chainhammer/run.sh
RUN chmod +x /opt/chainhammer/run.sh

# Install MIN requirements (fast + enough for deploy/send/tps load runs)
# NOTE: requirements.min.txt must exist inside /opt/chainhammer (your repo has it)
RUN pip install --upgrade pip setuptools wheel \
 && pip install --retries 5 -r /opt/chainhammer/requirements.min.txt

# Create expected dirs so logging never breaks
RUN mkdir -p /opt/chainhammer/logs /opt/chainhammer/hammer

# Entry command wrapper
COPY docker-entrypoint.sh /usr/local/bin/chainhammer
RUN chmod +x /usr/local/bin/chainhammer

ENTRYPOINT ["/usr/local/bin/chainhammer"]
CMD ["help"]