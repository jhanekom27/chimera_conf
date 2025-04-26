import logging
from abc import ABC

from chimera_conf.chimera_form import ChimeraForm
from chimera_conf.utilities import (
    _add_config_set_files,
    _load_configs,
    _merge_all_dicts,
)
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ChimeraConf(BaseModel, ABC):
    """
    Base class for composable, layered configuration classes.

    Define your base configuration files in the `_config_files` attribute.

    Call `manifest()` to automatically load your base files along with
    the currently active ChimeraForm overlays, and construct a full
    configuration object.

    Example:
        class MyConfig(ChimeraConf):
            _config_files = ["configs/base.yml"]
            api_key: str
            timeout: int

        ChimeraForm.set_form("prod")
        config = MyConfig.load_config()
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
    def manifest(
        cls,
        chimera_form: str | None = None,
        config_files_override: list[str] | None = None,
    ):
        """
        Manifest the final configuration for this class.

        This method loads all relevant configuration files based on:
        - Base files specified in the class `_config_files` attribute
        - Overlays provided by the active ChimeraForm (current form(s))
        - Any optional overrides provided at load time

        It merges all configurations in order, with later files overriding earlier ones,
        and constructs a fully realized config object.

        Args:
            chimera_form (Optional[str]): The name of the form to load overlays for.
                Defaults to the current ChimeraForm if not specified.
            config_files_override (Optional[list[str]]): Override the base files
                instead of using the class's default `_config_files`.

        Returns:
            An instance of the configuration class populated with merged values.

        Raises:
            ValueError: If `_config_files` is improperly specified or missing.
        """
        logger.info("Loading config for %s", cls.__name__)

        if chimera_form is None:
            logger.info(
                "Using ConfigSet singleton: %s",
                ChimeraForm.chimera_form,
            )
            chimera_form = ChimeraForm.chimera_form

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

        all_config_files = _add_config_set_files(files_to_load, chimera_form)

        # Load config files into list.
        config_dicts = _load_configs(all_config_files)

        # Merge all the dictionaries.
        merged_config = _merge_all_dicts(config_dicts)

        # Create the class.
        return cls(**merged_config)
