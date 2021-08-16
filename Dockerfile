FROM python:3.7-slim as python_builder
RUN apt-get update -qq && \
  apt-get install -y --no-install-recommends \
  build-essential \
  curl

# install poetry
# keep this in sync with the version in pyproject.toml and Dockerfile
ENV POETRY_VERSION 1.1.4
RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python
ENV PATH "/root/.poetry/bin:/opt/venv/bin:${PATH}"

# install dependencies
COPY . /app/
RUN python -m venv /opt/venv && \
  . /opt/venv/bin/activate && \
  pip install --no-cache-dir -U pip && \
  cd /app && \
  poetry install --no-dev --no-interaction

# start a new build stage
FROM python:3.7-slim

# copy everything from /opt
COPY --from=python_builder /opt/venv /opt/venv
COPY --from=python_builder /app /app
ENV PATH="/opt/venv/bin:$PATH"

COPY actions /app/actions
COPY data /app/data

USER root
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r /app/actions/requirements.txt
RUN python -m spacy download fr_core_news_sm

RUN useradd -ms /bin/bash admin
RUN chown -R admin:admin /app
RUN chmod 755 /app
USER admin
CMD ["start", "--actions", "actions"]