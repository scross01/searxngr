#!/bin/sh
# Opt-in watchdog for a local stack managed by searxng.service.
# Only test the local HTTP server; never send periodic upstream searches or
# restart the stack to clear engine CAPTCHA/rate-limit cooldowns.
set -eu

healthy() {
    curl --noproxy '*' --fail --silent --show-error --max-time 5 \
        http://127.0.0.1:8080/healthz >/dev/null
}

if healthy; then
    exit 0
fi
sleep 2
if healthy; then
    exit 0
fi

echo 'SearXNG health check failed twice; restarting searxng.service.' >&2
systemctl --user restart searxng.service
# Allow the web server to become ready after the containers have started.
for attempt in 1 2 3 4 5; do
    if healthy; then
        exit 0
    fi
    sleep 2
done
echo 'SearXNG still unavailable after restart; inspect the service logs.' >&2
exit 1
