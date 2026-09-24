# Running the local SearXNG test container

This directory runs a local SearXNG instance in Docker for testing `searxngr`
against a real server. The instance listens on `http://127.0.0.1:8080` on the
host and `http://searxng:8080` inside the compose network.

## Start the test server

```shell
docker compose -f docker/docker-compose.yml up -d --wait searxng
```

The server is then reachable at `http://127.0.0.1:8080` (JSON format is
enabled in `docker/config/searxng/settings.yml`).

## Search against it from the host

```shell
uv run searxngr --searxng-url http://127.0.0.1:8080 --url-handler echo "test"
```

## Run the integration suite

The `integration` compose profile builds the `searxngr` image (with tests)
and runs `tests/integration/` against the containerized SearXNG:

```shell
make test-integration
```

Or step by step:

```shell
docker compose --profile integration -f docker/docker-compose.yml build
docker compose --profile integration -f docker/docker-compose.yml run --rm integration
```

The suite is skipped automatically unless `SEARXNG_URL` is set, so a plain
`pytest` run (and CI) never requires a server. To run it from the host
against any reachable instance with JSON enabled:

```shell
SEARXNG_URL=http://127.0.0.1:8080 make test-live
```

## Tear down

```shell
make integration-down
```

or

```shell
docker compose --profile integration -f docker/docker-compose.yml down
```
