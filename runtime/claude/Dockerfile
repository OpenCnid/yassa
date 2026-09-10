FROM node:24.19.0-bookworm-slim@sha256:a9f5f7c91a432850b2a8a7797adf5eadb6c733ceed61167806cee7ea7fbc29df

ARG CLAUDE_VERSION=2.1.267
RUN npm install --global @anthropic-ai/claude-code@${CLAUDE_VERSION} \
    && npm cache clean --force \
    && mkdir -p /work /home/claude/.claude /home/runtime \
    && chown -R node:node /work /home/claude /home/runtime
ENV HOME=/home/claude CLAUDE_CONFIG_DIR=/home/claude/.claude
USER node
WORKDIR /work
CMD ["sleep", "infinity"]
