#!/bin/sh
set -eu
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
model=$(tr -d '\000' </proc/device-tree/model 2>/dev/null || true)
case "$model" in *"Raspberry Pi 5"*) ;; *) echo "Warning: expected Raspberry Pi 5, found: $model" >&2;; esac
. /etc/os-release
case "${ID:-}" in debian|raspbian) ;; *) echo "Unsupported OS: ${PRETTY_NAME:-unknown}" >&2; exit 1;; esac
python3 -c 'import picamera2, libcamera' || {
  echo "Install Raspberry Pi OS Picamera2/libcamera packages first." >&2
  exit 1
}
python3 -m venv --system-site-packages "$project_dir/.venv"
"$project_dir/.venv/bin/pip" install --no-deps -e "$project_dir"
if [ ! -f "$project_dir/config/observer.yaml" ]; then
  cp "$project_dir/config/observer.example.yaml" "$project_dir/config/observer.yaml"
fi
chmod 0640 "$project_dir/config/observer.yaml"
install -d -o pi -g pi -m 0750 \
  /home/pi/trash-panda-observer-data \
  /home/pi/trash-panda-observer-data/captures \
  /home/pi/trash-panda-observer-data/logs \
  /home/pi/trash-panda-observer-data/state
"$project_dir/.venv/bin/python" -m pytest -q "$project_dir/tests"
echo "Installation prepared. Service installation is a separate step."
