#!/bin/sh
set -eu
service=trash-panda-observer.service
data=/home/pi/trash-panda-observer-data
systemctl is-enabled "$service"
systemctl is-active "$service"
systemctl show "$service" -p MainPID -p NRestarts -p ActiveEnterTimestamp
df -h /
du -sh "$data/captures"
printf 'complete_events='
find "$data/captures" -name event.json -exec grep -l '"status": "complete"' {} + |
  wc -l
printf 'temporary_files='
find "$data/captures" -name '.*.tmp' | wc -l
tail -n 10 "$data/logs/observer.log"
