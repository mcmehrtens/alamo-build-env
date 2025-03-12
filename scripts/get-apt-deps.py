#!/usr/bin/env python3
"""Parse apt packages from a YAML configuration file."""

import argparse
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
        "-c",
        "--config",
        required=True,
        help="Path to the YAML configuration file",
    )
    return parser.parse_args()


def parse_packages(config_path: Path) -> list[str]:
    """
    Parse package list from a YAML configuration file.

    Parameters
    ----------
    config_path
        Path to configuration file.

    Returns
    -------
    list[str, ...]
        List of packages as strings.
    """
    yaml = YAML(typ="safe")

    try:
        with open(config_path) as config_file:
            config = yaml.load(config_file)
        if "packages" not in config:
            raise KeyError(
                "The 'packages' key was not found in the configuration file."
            )
        if not isinstance(config["packages"], list):
            raise ValueError(
                "The 'packages' key must contain a list of package names."
            )
        return config["packages"]
    except FileNotFoundError as err:
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}"
        ) from err
    except Exception as err:
        raise RuntimeError("Error parsing YAML:") from err


def main() -> None:
    """Parse command-line arguments and process the YAML file."""
    args = parse_args()
    package_list = parse_packages(Path(args.config))
    print(" ".join(package_list))


if __name__ == "__main__":
    main()
