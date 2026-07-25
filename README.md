# Trash Panda Observer

A headless Raspberry Pi 5 wildlife observation and dataset collection system.
It detects conventional image motion and stores high-resolution JPEG bursts for
later manual review. It does not classify animals or actuate hardware.

## Pi installation

```sh
git clone https://github.com/jthompson429/Trash_Panda_Observer.git
cd Trash_Panda_Observer
./scripts/install.sh
```

Review the ignored `config/observer.yaml`, verify the camera, then test:

```sh
./scripts/run_observer.sh --dry-run --motion-debug --max-runtime-minutes 2
./scripts/run_observer.sh --capture-test
```

Captured data is stored outside Git at
`/home/pi/trash-panda-observer-data/captures`. Preserve that directory before
reformatting or replacing storage. Automatic retention is not enabled.

## Service operation

```sh
sudo systemctl status trash-panda-observer
sudo systemctl start trash-panda-observer
sudo systemctl stop trash-panda-observer
sudo systemctl restart trash-panda-observer
sudo systemctl enable trash-panda-observer
sudo systemctl disable trash-panda-observer
journalctl -u trash-panda-observer -f
```

Application logs rotate under `/home/pi/trash-panda-observer-data/logs`.

## Configuration

The installer creates the ignored `config/observer.yaml` once and never
overwrites it. Begin with automatic exposure and continuous autofocus. Settings
most likely to need field tuning are motion thresholds, background learning
rate, ROI, autofocus behavior, burst interval/count, cooldown, and lighting
placement.

An ROI is `[x, y, width, height]` using normalized values from 0 through 1. It
only limits motion analysis; saved images remain full-frame. Run dry mode while
walking through the scene and compare animal motion against idle values before
raising thresholds. Avoid tuning so conservatively that small or distant cats
are missed.

Manual focus is available for stable feeder distances:

```yaml
camera:
  autofocus_mode: manual
  manual_lens_position: 3.5
```

Test lens positions rather than copying this example blindly. Fixed exposure,
gain, and frame-duration controls are also optional; leave them `null` until
night testing shows automatic exposure is unsuitable.

## Reviewing and copying data

Each event contains `frame_000.jpg` through `frame_011.jpg` and a versioned
`event.json`. The application never assigns species labels.

```sh
find /home/pi/trash-panda-observer-data/captures -name event.json | tail
du -sh /home/pi/trash-panda-observer-data/captures
df -h /
rsync -av pi@tpb9000-2.local:/home/pi/trash-panda-observer-data/captures/ \
  ./trash-panda-captures/
```

Stop the service or take a consistent filesystem copy before reformatting the
SD card. Verify the copied files before deleting anything. Retention is
disabled by default and the observer will not delete captures automatically.

## Night setup

Compare porch-light-only, porch-light-plus-IR, and IR-only captures. If the
sliding glass produces haze or hotspots, offset and angle the 940 nm illuminator
away from the strongest reflection and place matte black fabric against the
inside of the glass. Keep the illuminator board outside the camera frame.

Recommended field sequence:

1. Verify a sharp daytime frame and the feeder/approach framing.
2. Compare porch light only, porch light plus IR, and IR only.
3. Run motion debug and observe cats moving naturally.
4. Run a forced burst and inspect all JPEGs plus `event.json`.
5. Run manually for at least 30 minutes and test Ctrl+C.
6. Enable the service, reboot, and confirm automatic recovery.

Review nighttime samples for glare, haze, clipped highlights, motion blur,
metal-bowl hotspots, and glass reflections.

## Troubleshooting

- **Camera busy:** stop the service before running verification manually:
  `sudo systemctl stop trash-panda-observer`.
- **Picamera2 missing in the venv:** recreate it with
  `python3 -m venv --system-site-packages .venv`; do not install libcamera
  from pip.
- **Autofocus hunting:** compare continuous autofocus with tested manual lens
  positions, especially under IR-only illumination.
- **Night motion blur:** inspect event exposure metadata before considering a
  fixed exposure or gain.
- **False triggers:** use motion-debug logs, then adjust ROI, thresholds, or
  background learning gradually.
- **Restart loop:** inspect
  `journalctl -u trash-panda-observer -n 100 --no-pager`, validate the YAML,
  check disk space, and confirm no other process owns the camera.
- **Low storage:** copy captures elsewhere and verify the backup. Captures are
  suppressed while space is below the configured minimum; they are not deleted.

## Uninstall

```sh
sudo systemctl disable --now trash-panda-observer
sudo rm /etc/systemd/system/trash-panda-observer.service
sudo systemctl daemon-reload
```

Removing `/home/pi/Trash_Panda_Observer` does not remove captured data. Preserve
and verify `/home/pi/trash-panda-observer-data` before deleting it.
