# Dependencies

Camera-integrated and native libraries come from Raspberry Pi OS apt packages:

- `python3-picamera2` — Picamera2 and libcamera Python integration
- `python3-opencv` — conventional motion image processing
- `python3-numpy` — analysis arrays
- `python3-yaml` — configuration loading
- `python3-pytest` — hardware-independent tests
- `python3-venv` — project virtual environment

The project venv is created with `--system-site-packages` so it can use the
Raspberry Pi camera stack. Do not install or replace libcamera from pip.

The project itself is installed editable into `.venv` with `--no-deps`.
`pyproject.toml` contains package metadata and the CLI entry point; OS package
selection remains explicit in `scripts/install.sh`.
