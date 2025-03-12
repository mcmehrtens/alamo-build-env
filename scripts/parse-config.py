#!/usr/bin/env python3
"""Parse a YAML configuration file."""

import argparse
import json
from pathlib import Path

from ruamel.yaml import YAML


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns
    -------
    argparse.Namespace
        Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Extract package lists from a YAML configuration file for use "
            "with apt-get"
        )
    )
    parser.add_argument(
        "config",
        help="Path to the YAML configuration file",
    )
    parser.add_argument("output", help="Path to the output JSON file")
    return parser.parse_args()


def parse_config(config_path: Path) -> dict:
    """
    Parse the YAML configuration file.

    Parameters
    ----------
    config_path
        Path to the YAML configuration file.

    Returns
    -------
    dict
        The parsed configuration file.

    Raises
    ------
    FileNotFoundError
        If configuration file is not found.
    """
    yaml = YAML(typ="safe")
    try:
        with open(config_path) as config_file:
            return yaml.load(config_file)
    except FileNotFoundError as err:
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}"
        ) from err
    except Exception as err:
        raise RuntimeError("Error parsing YAML:") from err


def write_json_config(output_path: Path, config: dict):
    """
    Write environment variables to the environment file.

    Parameters
    ----------
    output_path
        Path to the output config file.
    """
    with open(output_path, "w") as config_file:
        json.dump(config, config_file, indent=4)


def main() -> None:
    """Parse command-line arguments and process the YAML file."""
    args = parse_args()
    config = parse_config(Path(args.config))
    write_json_config(Path(args.output), config)


if __name__ == "__main__":
    main()
