FROM socrates12345/rasa-base:3.7.10

WORKDIR /app

# Install additional requirements
RUN pip install --no-cache-dir certifi>=2023.11.17 httpx>=0.24.0

# Copy necessary files for training and running Rasa
COPY config.yml domain.yml credentials.yml endpoints.yml /app/

# Copy your custom action code
COPY actions /app/actions

# Set environment variable to disable SSL verification warnings
ENV PYTHONWARNINGS="ignore:Unverified HTTPS request"

RUN chown -R 1001:1001 /app
USER 1001

ENTRYPOINT ["rasa"]
CMD ["run", "actions"]