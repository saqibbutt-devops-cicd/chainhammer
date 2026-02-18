FROM python:3.7-bullseye

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /opt/chainhammer

# System deps + REAL solc (NOT solcjs)
RUN apt-get update && apt-get install -y --no-install-recommends \
      bash ca-certificates curl git jq \
      build-essential gcc \
      libffi-dev libssl-dev \
      expect \
    && curl -fL -o /usr/local/bin/solc \
      https://github.com/ethereum/solidity/releases/download/v0.4.21/solc-static-linux \
    && chmod +x /usr/local/bin/solc \
    && solc --version \
    && rm -rf /var/lib/apt/lists/*

# Copy app
COPY chainhammer/ /opt/chainhammer/
COPY chainhammer/run.sh /opt/chainhammer/run.sh
COPY docker-entrypoint.sh /opt/chainhammer/entry.sh

RUN chmod +x /opt/chainhammer/run.sh /opt/chainhammer/entry.sh

# Python deps (runtime only)
RUN pip install --upgrade "pip<24" "setuptools<69" wheel \
 && pip install --retries 5 -r /opt/chainhammer/requirements.min.txt \
 && pip install --retries 5 py-solc==3.2.0 eth-testrpc==1.3.5

ENTRYPOINT ["/opt/chainhammer/entry.sh"]