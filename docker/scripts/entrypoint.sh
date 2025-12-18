#!/bin/bash

set -e

if [ ! -f "/app/config.yaml" ]; then
    echo "WARNING: No config.yaml found at /app/config.yaml"
    echo "Creating default config from example..."
    cp /app/config.example.yaml /app/config.yaml
    echo "Please update /app/config.yaml with your Spotify credentials"
fi

CRON_ENABLED=$(grep -A 1 "^cron:" /app/config.yaml | grep "enabled:" | awk '{print $2}')

# Default to false if 'enabled:' field is missing
if [ -z "$CRON_ENABLED" ]; then
    CRON_ENABLED="false"
fi

if [ "$CRON_ENABLED" = "true" ]; then
    echo "Cron scheduling enabled"

    CRON_SCHEDULE=$(grep -A 2 "^cron:" /app/config.yaml | grep "schedule:" | sed 's/.*schedule: *"\(.*\)".*/\1/')

    if [ -z "$CRON_SCHEDULE" ]; then
        echo "ERROR: Could not extract cron schedule from config.yaml"
        exit 1
    fi

    echo "Cron schedule: $CRON_SCHEDULE"

    echo "$CRON_SCHEDULE /usr/local/bin/spotisync sync >> /var/log/spotisync.log 2>&1" > /etc/cron.d/spotisync
    chmod 0644 /etc/cron.d/spotisync

    crontab /etc/cron.d/spotisync

    echo "Cron job installed"
else
    echo "Cron scheduling disabled"
fi

exec "$@"
