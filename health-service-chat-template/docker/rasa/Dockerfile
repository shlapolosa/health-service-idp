FROM socrates12345/rasa-base:3.7.10

# Force cache busting
ARG CACHEBUST=1
WORKDIR /app

# Copy necessary files for training and running Rasa
COPY config.yml domain.yml credentials.yml endpoints.yml ./
COPY data /app/data

# Ensure proper permissions
RUN mkdir -p /app/models && chown -R 1001:1001 /app

# Train the model and generate visualizations
RUN python -m rasa train --num-threads 1 --fixed-model-name model --quiet

USER 1001
ENTRYPOINT ["rasa"]
CMD ["run", "--enable-api", "--cors", "*", "--port", "5005"]