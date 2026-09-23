# Running SearXNG and searxngr in docker

Build the searxngr container

```shell
docker build . -t searxngr
```

Run the container against a local SearXNG instance. Set `--dns` to a DNS
server that can resolve your instance's hostname, and substitute your own
instance URL and credentials:

```shell
podman run --dns <dns-ip> -it --rm searxngr searxngr "test" \
  --searxng-url https://searxng.example.com --no-verify-ssl --url-handler echo
```

Run SearXNG and searxng in docker.

```shell
docker compose up -d
docker exec -it searxngr
```

## Integration tests

The repo ships a live integration suite (`tests/integration/`) that runs the
real CLI against the SearXNG instance defined in `docker-compose.yml`. The
tests are skipped automatically unless `SEARXNG_URL` is set, so a plain
`pytest` run (and CI) never requires a server.

Build the image (it includes the tests) and start the SearXNG server:

```shell
docker compose --profile integration build
docker compose --profile integration up -d searxng
```

Run the suite (the `integration` service waits for SearXNG to answer before
asserting):

```shell
docker compose --profile integration run --rm integration
```

Every check asserts against the real server: query encoding (`&`, `+`, `#`,
Unicode), JSON purity on stdout with diagnostics on stderr, non-interactive
behavior (piped stdout must not hang or prompt), nonzero exit on failure,
retry flag validation, `--version`, and the removal of the
`--fallback-engines` flag.

Tear down:

```shell
docker compose --profile integration down
```

You can also run the suite from the repo root against any reachable SearXNG
instance with JSON enabled:

```shell
SEARXNG_URL=http://127.0.0.1:8080 uv run pytest tests/integration -v
```
