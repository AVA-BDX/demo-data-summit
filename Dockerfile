FROM rasa/rasa-sdk:2.8.1

COPY actions /app/actions
COPY data /app/data

USER root
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r /app/actions/requirements.txt
RUN python -m spacy download fr_core_news_sm
RUN pip install psycopg2-binary

RUN useradd -ms /bin/bash admin
RUN chown -R admin:admin /app
RUN chmod 755 /app
USER admin
CMD ["start", "--actions", "actions"]