ARG BASE_IMAGE=ghcr.io/nvidia/nemoclaw/hermes-sandbox-base@sha256:176ec6ec056cdf2dd45f60a0095fb6aac962eb5d7382d28d5734098a72399000
FROM ${BASE_IMAGE}

COPY config.yaml /sandbox/.hermes/config.yaml

RUN mkdir -p /sandbox/.hermes /sandbox/.hermes-data \
    && chown -R sandbox:sandbox /sandbox/.hermes /sandbox/.hermes-data \
    && chmod 755 /sandbox/.hermes /sandbox/.hermes-data

ENV HOME=/sandbox
ENV HERMES_HOME=/sandbox/.hermes

CMD ["/bin/bash"]
