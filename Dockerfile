FROM rasa/rasa-sdk:2.4.0

COPY actions /app/actions
COPY data /app/data

USER root
RUN pip3 install --upgrade pip
RUN pip3 install --no-cache-dir -r /app/actions/requirements.txt

RUN useradd -ms /bin/bash admin
RUN chown -R admin:admin /app
RUN chmod 755 /app
USER admin
CMD ["start", "--actions", "actions"]