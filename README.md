# chimera_conf

`chimera_conf` is a Python utility for managing composable, layered configurations. It allows you to define base configuration files and easily overlay environment-specific settings (called "forms") like development, production, or local overrides.

## Core Concepts

- **`ChimeraConf`**: The base class for your configuration models. You define your configuration schema (using Pydantic) and specify the default base configuration files here.
- **`ChimeraForm`**: A simple class that holds the currently active "form" (e.g., "prod", "dev", "local"). This determines which overlay files are applied.
- **Layered Loading**: When you `manifest()` a `ChimeraConf` class, it:
  1. Reads the base configuration files defined in `_config_files`.
  2. Reads overlay files corresponding to the currently active `ChimeraForm`. Overlay files should be placed in a subdirectory named after the form (e.g., `configs/prod/` for the "prod" form).
  3. Merges all loaded configurations, with later files (overlays) overriding earlier ones (base files).
  4. Validates the final configuration against your Pydantic model schema.

## Installation

```bash
# Recommended to install within a virtual environment
pip install chimera_conf
# Or if installing directly from source
# pip install .
```

_(Note: You'll need to package this properly for pip install to work, or adjust the command if installing locally)_

## Usage

1.  **Define your Configuration Class:**
    Inherit from `ChimeraConf`, define your fields using Pydantic type hints, and specify your base configuration files in `_config_files`.

    ```python
    # src/my_app/config.py
    from chimera_conf import ChimeraConf

    class AppConfig(ChimeraConf):
        # Base configuration file(s)
        _config_files = ["configs/base.yaml"]

        # Configuration fields
        database_url: str
        api_key: str
        timeout: int = 60 # Default value
        feature_flags: dict[str, bool] = {}

        class Config:
            extra = "forbid" # Forbid extra fields not defined in the model
    ```

2.  **Create Configuration Files:**
    Create your base configuration file(s) and any overlay files. File paths in `_config_files` and for overlays are relative to your project root or should be importable paths if using a different structure. Supported formats currently include YAML and JSON (you might need to adjust `_load_configs` in `utilities.py` if you only support one).

    - `configs/base.yaml`:

      ```yaml
      database_url: "postgresql://user:pass@localhost/default_db"
      api_key: "base_key_123"
      ```

    - `configs/prod/base.yaml`: (Overlay for the 'prod' form)
      ```yaml
      database_url: "postgresql://prod_user:prod_pass@prod_host/prod_db"
      api_key: "prod_secret_key_xyz"
      timeout: 120
      feature_flags:
        new_dashboard: true
      ```
    - `configs/dev/base.yaml`: (Overlay for the 'dev' form)
      ```yaml
      database_url: "postgresql://dev_user:dev_pass@dev_host/dev_db"
      api_key: "dev_key_456"
      feature_flags:
        new_dashboard: false
        beta_feature: true
      ```

3.  **Set the Form and Load:**
    Use `ChimeraForm.set_form()` to specify the active environment, then call `manifest()` on your configuration class.

    ```python
    # src/my_app/main.py
    import os
    from chimera_conf import ChimeraForm
    from .config import AppConfig

    # Set the form (e.g., from an environment variable)
    env_form = os.getenv("APP_ENV", "local") # Default to 'local' if not set
    ChimeraForm.set_form(env_form)

    # Manifest the configuration
    try:
        config = AppConfig.manifest()

        # Now use the loaded configuration
        print(f"Database URL: {config.database_url}")
        print(f"API Key: {config.api_key}")
        print(f"Timeout: {config.timeout}")
        print(f"Feature Flags: {config.feature_flags}")

    except (ValueError, FileNotFoundError) as e:
        print(f"Error loading configuration: {e}")
        # Handle configuration loading errors appropriately
    ```

## How Overlays Work

When `ChimeraForm` is set to `"prod"`, `chimera_conf` will look for files within a directory structure mirroring your base files, but inside a `prod` subdirectory.

For example, if `_config_files = ["configs/base.yaml", "configs/features.yaml"]` and the form is `"prod"`, it will load:

1.  `configs/base.yaml`
2.  `configs/features.yaml`
3.  `configs/prod/base.yaml` (if it exists)
4.  `configs/prod/features.yaml` (if it exists)

Values in later files overwrite values from earlier files during the merge process.

## Default Form

If `ChimeraForm.set_form()` is never called, the default form is `"local"`. You can create `configs/local/` overlays for local development overrides that shouldn't be committed.
