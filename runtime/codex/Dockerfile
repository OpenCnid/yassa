FROM node:24.19.0-bookworm-slim@sha256:a9f5f7c91a432850b2a8a7797adf5eadb6c733ceed61167806cee7ea7fbc29df

ARG CODEX_VERSION=0.153.4
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-yaml git ripgrep curl ca-certificates bubblewrap \
    && rm -rf /var/lib/apt/lists/* \
    && npm install --global @openai/codex@${CODEX_VERSION} \
    && npm cache clean --force

RUN mkdir -p /work /home/subject /home/runtime/codex \
    && chown -R node:node /work /home/subject /home/runtime
ENV HOME=/home/subject CODEX_HOME=/home/runtime/codex
USER node
WORKDIR /work
CMD ["sleep", "infinity"]
