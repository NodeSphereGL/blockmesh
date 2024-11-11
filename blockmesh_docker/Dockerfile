# Use the base image from Ubuntu
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    vim\
    net-tools \
    wget \
    curl \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

ENV TZ=UTC
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone


COPY ./bin/blockmesh-cli /usr/local/bin/blockmesh-cli
RUN chmod +x /usr/local/bin/blockmesh-cli

# Copy the entrypoint script
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Use the entrypoint script to run the prover with the provided ENDPOINT_URL
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
