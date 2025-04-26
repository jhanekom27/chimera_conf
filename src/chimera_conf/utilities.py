from functools import reduce
import os
from typing import Any

import yaml
import importlib.resources

from chimera_conf.chimera_conf import logger


def _merge_dicts(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = base.copy()  # Start with a copy of the base dictionary

    for overlay_key, overlay_value in overlay.items():
        if overlay_key in merged:
            if isinstance(overlay_value, dict) and isinstance(
                merged[overlay_key], dict
            ):
                # Recursively merge dictionaries
                merged[overlay_key] = _merge_dicts(merged[overlay_key], overlay_value)
            else:
                merged[overlay_key] = overlay_value
        else:
            merged[overlay_key] = overlay_value

    return merged


# Define functions.
def _split_package_file_path(file_path: str) -> tuple[str, str]:
    """
    Split package path and file name from a file path.

    Args:
        file_path (str): file path.

    Returns:
        tuple[str, str]: package path and file name.
    """

    full_path, file_name = os.path.split(file_path)
    package_path = full_path.replace(file_name, "").replace("/", ".")

    return package_path, file_name


def _load_yaml(package_path: str, file_name: str) -> dict[str, Any]:
    """
    Load a .yaml configuration file given its path
    and name.

    Args:
        package_path (str): package path.
        file_name (str): file name.

    Returns:
        dict[str, Any]: loaded yaml file as dict.
    """

    try:
        with (
            importlib.resources.files(package_path)
            .joinpath(file_name)
            .open("r") as yaml_file
        ):
            logger.info("Loading %s.%s", package_path, file_name)
            return yaml.safe_load(yaml_file)

    except FileNotFoundError:
        logger.info("File not found %s.%s", package_path, file_name)
        return {}

    except Exception as e:
        raise e


def _load_configs(config_files: list[str]) -> list[dict[str, Any]]:
    """
    Load configuration dictionaries.

    Args:
        config_files (list[str]): list of config files.

    Returns:
        list[dict[str, Any]]: list of loaded config files.
    """

    config_dicts = []

    for file_path in config_files:
        package_path, file_name = _split_package_file_path(file_path)
        config_dict = _load_yaml(package_path, file_name)

        if config_dict is not None:
            config_dicts.append(config_dict)

    return config_dicts


def _merge_all_dicts(dicts: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Coalesce config dictionaries.

    Args:
        dicts (list[dict[str, Any]]): list of config files.

    Returns:
        dict[str, Any]: coalesced configs in single dictionary.
    """

    return reduce(_merge_dicts, dicts, {})


def _add_config_set_files(config_files: list[str], config_set: str) -> list[str]:
    environment_config_files = []

    for config_file in config_files:
        file_parts = config_file.split(".")
        file_extension = file_parts[-1]
        remainder_of_file_path = file_parts[:-1]

        all_path_parts = remainder_of_file_path + [config_set] + [file_extension]
        new_file_path = ".".join(all_path_parts)

        environment_config_files.append(new_file_path)

    # Important that environment files go last so they overwrite the configs
    return config_files + environment_config_files
