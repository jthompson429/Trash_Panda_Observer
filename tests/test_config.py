from pathlib import Path

import pytest
import yaml

from trash_panda_observer.config import load_config


EXAMPLE = Path("config/observer.example.yaml")


def write_config(tmp_path, mutate):
    value = yaml.safe_load(EXAMPLE.read_text())
    mutate(value)
    path = tmp_path / "observer.yaml"
    path.write_text(yaml.safe_dump(value))
    return path


def test_example_configuration_is_valid():
    assert load_config(EXAMPLE)["camera"]["analysis_fps"] == 12


def test_missing_section_fails(tmp_path):
    path = write_config(tmp_path, lambda value: value.pop("storage"))
    with pytest.raises(ValueError, match="storage"):
        load_config(path)


def test_invalid_autofocus_fails(tmp_path):
    path = write_config(
        tmp_path, lambda value: value["camera"].update(autofocus_mode="magic")
    )
    with pytest.raises(ValueError, match="autofocus"):
        load_config(path)


def test_invalid_roi_fails(tmp_path):
    path = write_config(
        tmp_path,
        lambda value: value["motion"].update(region_of_interest=[0.8, 0, 0.5, 1]),
    )
    with pytest.raises(ValueError, match="region_of_interest"):
        load_config(path)


def test_manual_focus_requires_position(tmp_path):
    path = write_config(
        tmp_path, lambda value: value["camera"].update(
            autofocus_mode="manual", manual_lens_position=None))
    with pytest.raises(ValueError, match="manual_lens_position"):
        load_config(path)
