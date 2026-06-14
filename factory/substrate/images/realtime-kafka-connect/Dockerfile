# realtime-kafka-connect — fast-data-dev broker + baked Kafka Connect plugins.
#
# Layers the Snowflake sink, Debezium Postgres source, and Lenses Stream-Reactor
# MQTT source onto the Lenses all-in-one image, so Connect has every plugin at
# startup — NO runtime wget / supervisorctl restart (replaces the old
# kafka-config-job jar install). Deterministic + air-gap-safe.
#
# Build (MUST be amd64 — the cluster is AMD64, Mac M-series defaults arm64):
#   docker build --platform linux/amd64 \
#     -t healthidpuaeacr.azurecr.io/realtime-kafka-connect:1.0.0 .
#   az acr login -n healthidpuaeacr && docker push healthidpuaeacr.azurecr.io/realtime-kafka-connect:1.0.0
#
# Pin the digest in realtime-platform-claim-composition.yaml (demo-kafka image).
# Fallback without an image build: see README.md (init-container download variant).
ARG BASE=lensesio/fast-data-dev:3.9.0
ARG SNOWFLAKE_VER=3.1.0
ARG DEBEZIUM_PG_VER=2.5.2.Final
ARG MQTT_STREAMREACTOR_VER=8.1.29

FROM ${BASE}

ARG SNOWFLAKE_VER
ARG DEBEZIUM_PG_VER
ARG MQTT_STREAMREACTOR_VER

# fast-data-dev scans /connectors (+ /usr/share/java/kafka-connect-*) for plugins.
# Give each connector its own plugin dir.
USER root
RUN set -eux; \
    apt-get update && apt-get install -y --no-install-recommends wget ca-certificates unzip tar; \
    mkdir -p /connectors/snowflake-kafka-connector \
             /connectors/debezium-connector-postgres \
             /connectors/kafka-connect-mqtt; \
    # --- Snowflake sink (single fat jar from Maven Central) ---
    wget -q -O /connectors/snowflake-kafka-connector/snowflake-kafka-connector-${SNOWFLAKE_VER}.jar \
      https://repo1.maven.org/maven2/com/snowflake/snowflake-kafka-connector/${SNOWFLAKE_VER}/snowflake-kafka-connector-${SNOWFLAKE_VER}.jar; \
    # --- Debezium Postgres source (plugin tarball → extract jars) ---
    wget -q -O /tmp/debezium-pg.tar.gz \
      https://repo1.maven.org/maven2/io/debezium/debezium-connector-postgres/${DEBEZIUM_PG_VER}/debezium-connector-postgres-${DEBEZIUM_PG_VER}-plugin.tar.gz; \
    tar -xzf /tmp/debezium-pg.tar.gz -C /connectors/; \
    rm -f /tmp/debezium-pg.tar.gz; \
    # --- Lenses Stream-Reactor MQTT source (zip → assembly jar) ---
    wget -q -O /tmp/mqtt.zip \
      https://github.com/lensesio/stream-reactor/releases/download/${MQTT_STREAMREACTOR_VER}/kafka-connect-mqtt-${MQTT_STREAMREACTOR_VER}.zip; \
    unzip -j -o /tmp/mqtt.zip "*.jar" -d /connectors/kafka-connect-mqtt/; \
    rm -f /tmp/mqtt.zip; \
    apt-get purge -y wget unzip && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*; \
    echo "Baked plugins:" && ls -R /connectors | head -40
