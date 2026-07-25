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

## Night setup

Compare porch-light-only, porch-light-plus-IR, and IR-only captures. If the
sliding glass produces haze or hotspots, offset and angle the 940 nm illuminator
away from the strongest reflection and place matte black fabric against the
inside of the glass. Keep the illuminator board outside the camera frame.

## Uninstall

Stop and disable the service, remove
`/etc/systemd/system/trash-panda-observer.service`, and reload systemd. Removing
the repository does not remove captured data. Delete captured data only after
making any required backup.
