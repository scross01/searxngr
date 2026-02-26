FROM python:3-slim-bookworm

WORKDIR /app

RUN pip install uv

RUN apt-get update && apt-get install -y --no-install-recommends vim-tiny && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
RUN uv sync --no-install-project

COPY searxngr/ searxngr/
COPY README.md ./
RUN uv pip install --system -e .

CMD ["searxngr"]
