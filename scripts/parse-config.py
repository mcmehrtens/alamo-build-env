#!/usr/bin/env python3
"""Parse a YAML configuration file."""

import argparse
import itertools
import json
import logging
import re
from pathlib import Path

from ruamel.yaml import YAML

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns
    -------
    argparse.Namespace
        Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=(
            "Extract package lists from a YAML configuration file for use "
            "with apt-get"
        ),
    )
    parser.add_argument(
        "config",
        help="Path to the YAML configuration file",
    )
    parser.add_argument("output", help="Path to the output JSON file")
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level",
    )
    return parser.parse_args()


def configure_logging(logging_level: str):
    """
    Configure the root logger.

    Parameters
    ----------
    logging_level
        The root logging level.
    """
    level = getattr(logging, logging_level.upper(), None)
    if not isinstance(level, int):
        raise ValueError(f"Invalid log level: {logging_level}")

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


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
        logger.debug("Attempting to open: %s", config_path)
        with open(config_path) as config_file:
            logger.debug("Successfully opened.")
            configs = tuple(yaml.load_all(config_file))
            logger.debug("Config parsed:")
            for config in configs:
                logger.debug("\n%s", json.dumps(config, indent=4))
            return configs
    except FileNotFoundError:
        logger.exception("Configuration file not found: %s", config_path)
        raise
    except Exception:
        logger.exception("Error parsing YAML")
        raise


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
    logger.info("Writing output config: %s", output_path)
    with open(output_path, "w") as config_file:
        json.dump(config, config_file, indent=4)


def generate_configure_commands(config: dict) -> list[list[str]]:
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
    logger.info("Generating configure commands...")

    flag_groups = config["flags"]
    logger.debug("flags:\n%s", json.dumps(flag_groups, indent=4))

    constraints = config.get("constraints", [])
    logger.debug("constraints:\n%s", json.dumps(constraints, indent=4))

    logger.debug("Parsing exclusive, required flags...")
    exclusive_groups = []
    for flag_group in flag_groups.values():
        if flag_group["type"] == "exclusive" and flag_group.get(
            "required", False
        ):
            exclusive_groups.append(flag_group["options"])
    logger.debug(
        "exlcusive_groups:\n%s", json.dumps(exclusive_groups, indent=4)
    )

    logger.debug(
        "Generating all possible configure commands from the exclusive, "
        "required flag groups..."
    )
    base_commands = list(itertools.product(*exclusive_groups))
    all_commands: list[list[str]] = [list(config) for config in base_commands]
    logger.debug("configure_commands:\n%s", json.dumps(all_commands, indent=4))

    logger.debug(
        "Generating all possible configure commands from the non-exclusive "
        "flag groups..."
    )
    for flag_group in flag_groups.values():
        if flag_group["type"] == "multiple":
            new_commands = []
            for command in all_commands:
                opt_flags = flag_group["options"]
                for r in range(len(opt_flags) + 1):
                    # Skip the "0" combination if the group is required.
                    if flag_group["required"] and r == 0:
                        continue
                    for combo in itertools.combinations(opt_flags, r):
                        new_commands.append(command + list(combo))
            all_commands = new_commands
    logger.debug("configure_commands:\n%s", json.dumps(all_commands, indent=4))

    logger.debug("Processing, exclusive, non-required flag groups...")
    for flag_group in flag_groups.values():
        if flag_group["type"] == "exclusive" and not flag_group.get(
            "required", False
        ):
            new_commands = []
            for command in all_commands:
                new_commands.append(command.copy())
                for option in flag_group["options"]:
                    new_command = command.copy()
                    new_command.append(option)
                    new_commands.append(new_command)
            all_commands = new_commands
    logger.debug("configure_commands:\n%s", json.dumps(all_commands, indent=4))

    logger.debug("Processing constraints...")
    valid_commands = []
    for command in all_commands:
        expanded_config = []
        for arg in command:
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
            valid_commands.append(command)
    logger.debug(
        "configure_commands:\n%s", json.dumps(valid_commands, indent=4)
    )
    logger.info(
        "%d configure commands successfully generated.", len(valid_commands)
    )

    return valid_commands


def generate_make_targets(
    amrex_dir: str, configure_commands: list[list[str]]
) -> list[str]:
    """
    Generate the make target based on the configure flags.

    This target will not include the AMReX version which must be added
    at build time.

    Parameters
    ----------
    amrex_dir
        AMReX checkout location relative to Alamo root.
    configure_commands
        List of valid configure commands.

    Returns
    -------
    list[str]
        Ordered list with the make targets corresponding to the
        configure commands.
    """
    logger.info(
        "Generating make targets that correspond to the configure commands..."
    )
    targets = []
    for conf_cmd in configure_commands:
        cmd = " ".join(conf_cmd)

        # get the dimension
        match = re.search(r"--dim\s+(\d+)", cmd)
        if match:
            dim = match.group(1)
        else:
            error_msg = f"Configure flags don't specify dimension: {cmd}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg)

        # get the compiler
        match = re.search(r"--comp\s+(\S+)", cmd)
        if match:
            comp = match.group(1)
        else:
            error_msg = f"Configure flags don't specify compiler: {cmd}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg)

        target = amrex_dir + "/"
        target += f"{dim}d"
        target += "-debug" if "--debug" in cmd else ""
        target += "-asan" if "--memcheck-tool asan" in cmd else ""
        target += "-msan" if "--memcheck-tool msan" in cmd else ""
        target += "-profile" if "--profile" in cmd else ""
        target += "-coverage" if "--coverage" in cmd else ""
        target += f"-{comp}"
        targets.append(target)

    logger.debug("targets:\n%s", json.dumps(targets, indent=4))
    return targets


def main() -> None:
    """Parse command-line arguments and process the YAML file."""
    args = parse_args()
    configure_logging(args.log_level)

    logger.info("Parsing config: %s", args.config)
    output_config, flag_config = parse_config(Path(args.config))

    configure_commands = generate_configure_commands(flag_config)

    targets = generate_make_targets(
        str(Path(output_config["amrex_build_config"]["amrex_dir"])),
        configure_commands,
    )

    logger.info(
        "Adding configure commands and their targets to the output config..."
    )
    output_config["configure_commands"] = [
        {"target": target, "configure_cmd": cmd}
        for target, cmd in zip(targets, configure_commands, strict=True)
    ]

    write_json_config(Path(args.output), output_config)


if __name__ == "__main__":
    main()
