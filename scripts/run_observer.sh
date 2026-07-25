#!/bin/sh
set -eu
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
config_path="$project_dir/config/observer.yaml"
[ -f "$config_path" ] || {
  echo "Missing $config_path; copy observer.example.yaml and review it." >&2
  exit 2
}
exec "$project_dir/.venv/bin/python" -m trash_panda_observer \
  --config "$config_path" "$@"
