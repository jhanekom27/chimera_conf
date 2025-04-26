# Lib functions to support config management.

# Import packages.
import importlib.resources
import logging
import os
from abc import ABC
from functools import reduce
from typing import Any

import yaml
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ConfigSet:
    config_set: str = "local"

    @classmethod
    def set_config_set(cls, config_set: str) -> None:
        logger.info("Setting config set to %s", config_set)
        cls.config_set = config_set


def merge_dicts(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = base.copy()  # Start with a copy of the base dictionary

    for overlay_key, overlay_value in overlay.items():
        if overlay_key in merged:
            if isinstance(overlay_value, dict) and isinstance(
                merged[overlay_key], dict
            ):
                # Recursively merge dictionaries
                merged[overlay_key] = merge_dicts(merged[overlay_key], overlay_value)
            else:
                merged[overlay_key] = overlay_value
        else:
            merged[overlay_key] = overlay_value

    return merged


# Define functions.
def split_package_file_path(file_path: str) -> tuple[str, str]:
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


def load_yaml(package_path: str, file_name: str) -> dict[str, Any]:
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


def update_config_tactics(config_dict: dict[str, Any]) -> dict[str, Any]:
    """
    Function to update the tactic profiles
    overwriting the default.

    Args:
        config_dict (dict[str, Any]): loaded profiles.

    Returns:
        dict[str, Any]: updated profiles.
    """

    list_variant = []
    if config_dict["tactic_variant"] is not None:
        list_variant = config_dict["tactic_variant"].keys()

    if len(list_variant) > 0:
        for variant in list_variant:
            dict_profile = config_dict["tactic_variant"][variant]

            for k, v in config_dict["tactic_default"].items():
                if k not in dict_profile.keys():
                    dict_profile[k] = v

            config_dict["tactic_variant"][variant] = dict_profile

    return config_dict


def load_configs(config_files: list[str]) -> list[dict[str, Any]]:
    """
    Load configuration dictionaries.

    Args:
        config_files (list[str]): list of config files.

    Returns:
        list[dict[str, Any]]: list of loaded config files.
    """

    config_dicts = []

    for file_path in config_files:
        package_path, file_name = split_package_file_path(file_path)
        config_dict = load_yaml(package_path, file_name)

        if config_dict is not None:
            config_dicts.append(config_dict)

    return config_dicts


def merge_all_dicts(dicts: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Coalesce config dictionaries.

    Args:
        dicts (list[dict[str, Any]]): list of config files.

    Returns:
        dict[str, Any]: coalesced configs in single dictionary.
    """

    return reduce(merge_dicts, dicts, {})


def add_config_set_files(config_files: list[str], config_set: str) -> list[str]:
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


class ConfigBuilder(BaseModel, ABC):
    """
    Abstract class to build a config class.
    """

    # Specify the path in fpo to the config file with slashes.
    _config_files: list[str]

    class Config:
        extra = "forbid"

    @classmethod
    def config_files(cls) -> list[str]:
        """
        Add some assertions around retrieving _config_files
        and ensures it is specified.
        """

        if not hasattr(cls, "_config_files"):
            raise NotImplementedError(
                "You must define _config_files on your concrete class"
            )

        # .default is how to access the default value for a pydantic
        # class on static properties.
        config_files = cls._config_files.default  # type: ignore

        if not isinstance(config_files, list):
            raise ValueError(
                (
                    "_config_files must be a list of strings, where "
                    "each string is a import path to a config file."
                )
            )

        if len(config_files) == 0:
            raise ValueError("You must specify at least 1 file in _config_files")

        return config_files

    @classmethod
    def load_config(
        cls,
        config_set: str | None = None,
        config_files_override: list[str] | None = None,
    ):
        logger.info("Loading config for %s", cls.__name__)

        if config_set is None:
            logger.info(
                "Using ConfigSet singleton: %s",
                ConfigSet.config_set,
            )
            config_set = ConfigSet.config_set

        if config_files_override is not None:
            files_to_load = config_files_override
            logger.info("Using overridden config files: %s", files_to_load)
        else:
            try:
                files_to_load = cls.config_files()  # Get defaults from class variable
                logger.info(
                    "Using default config files defined in class: %s", files_to_load
                )
            except (AttributeError, NotImplementedError, ValueError) as e:
                raise ValueError(
                    f"Config files must be provided via 'config_files_override' argument "
                    f"as '{cls.__name__}' does not define a valid default '_config_files'. Original error: {e}"
                )

        all_config_files = add_config_set_files(files_to_load, config_set)

        # Load config files into list.
        config_dicts = load_configs(all_config_files)

        # Merge all the dictionaries.
        merged_config = merge_all_dicts(config_dicts)

        # Create the class.
        return cls(**merged_config)
