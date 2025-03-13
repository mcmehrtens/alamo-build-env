#!/usr/bin/env python3
"""Parse a YAML configuration file."""

import argparse
import itertools
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


def parse_config(config_path: Path) -> tuple[dict, ...]:
    """
    Parse the YAML configuration file.

    Parameters
    ----------
    config_path
        Path to the YAML configuration file.

    Returns
    -------
    tuple[dict]
        The dictionaries parsed from the YAML configuration file. Each
        section of the YAML file (separated by `---`) is parsed into a
        different dictionary.

    Raises
    ------
    FileNotFoundError
        If configuration file is not found.
    """
    yaml = YAML(typ="safe")
    try:
        with open(config_path) as config_file:
            return tuple(yaml.load_all(config_file))
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
    config
        The parsed configuration object.
    """
    with open(output_path, "w") as config_file:
        json.dump(config, config_file, indent=4)


def generate_configure_commands(flag_config: dict) -> list[list[str]]:
    """
    Generate all valid build flag combinations.

    Refer to the YAML file for documentation on how config parsing is
    executed.

    Parameters
    ----------
    flag_config
        The parsed configuration object.

    Returns
    -------
    list[list[str]]
        Each possible configure command, where each argument and flag
        is a different element in the internal list.
    """
    flags = flag_config["flags"]
    constraints = flag_config.get("constraints", [])

    exclusive_groups = []
    for _, group_info in flags.items():
        if group_info["type"] == "exclusive" and group_info.get(
            "required", False
        ):
            exclusive_groups.append(group_info["options"])

    base_configs = list(itertools.product(*exclusive_groups))
    all_configs: list[list[str]] = [list(config) for config in base_configs]

    for _, group_info in flags.items():
        if group_info["type"] == "multiple":
            new_configs = []
            for config in all_configs:
                opt_flags = group_info["options"]
                for r in range(len(opt_flags) + 1):
                    # Skip the "0" combination if the group is required.
                    if group_info["required"] and r == 0:
                        continue
                    for combo in itertools.combinations(opt_flags, r):
                        new_configs.append(config + list(combo))
            all_configs = new_configs

    for _, group_info in flags.items():
        if group_info["type"] == "exclusive" and not group_info.get(
            "required", False
        ):
            new_configs = []
            for config in all_configs:
                new_configs.append(config.copy())
                for option in group_info["options"]:
                    new_config = config.copy()
                    new_config.append(option)
                    new_configs.append(new_config)
            all_configs = new_configs

    valid_configs = []
    for config in all_configs:
        expanded_config = []
        for arg in config:
            if (
                " " in arg
                and not arg.startswith('"')
                and not arg.startswith("'")
            ):
                expanded_config.extend(arg.split())
            else:
                expanded_config.append(arg)
        valid = True
        command_str = " ".join(expanded_config)

        for constraint in constraints:
            if_flag = constraint["if"]
            then_flag = constraint.get("then")
            not_flag = constraint.get("not")

            if if_flag in command_str:
                if then_flag and then_flag not in command_str:
                    valid = False
                    break
                if not_flag and not_flag in command_str:
                    valid = False
                    break

        if valid:
            valid_configs.append(config)

    return valid_configs


def main() -> None:
    """Parse command-line arguments and process the YAML file."""
    args = parse_args()
    config, flag_config = parse_config(Path(args.config))
    configure_commands = generate_configure_commands(flag_config)
    config["configure_commands"] = configure_commands
    write_json_config(Path(args.output), config)


if __name__ == "__main__":
    main()
