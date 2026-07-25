#!/bin/sh
set -eu
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
install_service=false
[ "${1:-}" = "--install-service" ] && install_service=true
model=$(tr -d '\000' </proc/device-tree/model 2>/dev/null || true)
case "$model" in *"Raspberry Pi 5"*) ;; *) echo "Warning: expected Raspberry Pi 5, found: $model" >&2;; esac
. /etc/os-release
case "${ID:-}" in debian|raspbian) ;; *) echo "Unsupported OS: ${PRETTY_NAME:-unknown}" >&2; exit 1;; esac
required_packages="python3-picamera2 python3-opencv python3-yaml python3-pytest python3-venv"
missing_packages=""
for package in $required_packages; do
  dpkg-query -W -f='${Status}' "$package" 2>/dev/null |
    grep -q "install ok installed" || missing_packages="$missing_packages $package"
done
if [ -n "$missing_packages" ]; then
  echo "Installing required Raspberry Pi OS packages:$missing_packages"
  echo "This will refresh apt package metadata."
  sudo apt-get update
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y $missing_packages
fi
python3 -c 'import picamera2, libcamera, cv2, yaml'
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
if $install_service; then
  sudo install -o root -g root -m 0644 \
    "$project_dir/systemd/trash-panda-observer.service" \
    /etc/systemd/system/trash-panda-observer.service
  sudo systemctl daemon-reload
  echo "Service installed or updated; it was not automatically started."
else
  echo "Installation prepared. Use --install-service to install the unit."
fi
