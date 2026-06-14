# realtime-kafka-connect image

Baked `lensesio/fast-data-dev:3.9.0` broker with the analytics-platform Kafka Connect plugins
pre-installed, so Connect (`connect-distributed`, port `:8083`) has every plugin at startup.

Bundled plugins (under `/connectors`):
- `snowflake-kafka-connector` 3.1.0 — Snowflake sink
- `debezium-connector-postgres` 2.5.2.Final — Postgres CDC source
- `kafka-connect-mqtt` (Lenses Stream-Reactor) 8.1.29 — MQTT source

## Build & push (amd64 — cluster is AMD64)
```bash
VER=1.0.0
docker build --platform linux/amd64 -t healthidpuaeacr.azurecr.io/realtime-kafka-connect:$VER .
az acr login -n healthidpuaeacr
docker push healthidpuaeacr.azurecr.io/realtime-kafka-connect:$VER
docker inspect --format='{{index .RepoDigests 0}}' healthidpuaeacr.azurecr.io/realtime-kafka-connect:$VER  # pin this digest
```
Pin the digest as the `demo-kafka` broker image in
`factory/substrate/crossplane/realtime-platform-claim-composition.yaml` (HARD-3: no `:latest`).

## Fallback (no image build): init-container download
If you cannot build/push the image, add an init-container to the `demo-kafka` Deployment that
downloads the same jars into a shared `emptyDir` mounted at `/connectors` (the broker container
mounts the same volume). This is the documented fallback only — the baked image is the default
(deterministic, air-gap-safe, no runtime `wget`/`supervisorctl restart`).

```yaml
initContainers:
- name: fetch-connect-plugins
  image: curlimages/curl:8.5.0
  command: ["sh","-c"]
  args:
    - |
      cd /connectors
      curl -fsSL -o snowflake-kafka-connector-3.1.0.jar https://repo1.maven.org/maven2/com/snowflake/snowflake-kafka-connector/3.1.0/snowflake-kafka-connector-3.1.0.jar
      curl -fsSL https://repo1.maven.org/maven2/io/debezium/debezium-connector-postgres/2.5.2.Final/debezium-connector-postgres-2.5.2.Final-plugin.tar.gz | tar -xz
      curl -fsSL -o /tmp/mqtt.zip https://github.com/lensesio/stream-reactor/releases/download/8.1.29/kafka-connect-mqtt-8.1.29.zip && cd /tmp && unzip -j mqtt.zip '*.jar' -d /connectors/
  volumeMounts: [{ name: connect-plugins, mountPath: /connectors }]
# broker container also mounts `connect-plugins` at /connectors; volume: emptyDir {}
```

## Notes
- Snowflake key-pair auth: the 3.1.0 fat jar carries its crypto deps. If a future Snowflake version
  needs `bc-fips`/`bcpkix-fips`, add them under `/connectors/snowflake-kafka-connector/`.
- Versions are `ARG`s in the Dockerfile — bump there.
