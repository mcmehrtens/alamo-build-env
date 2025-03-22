#!/usr/bin/env python3
"""Parse a YAML configuration file."""

import argparse
import json
import logging
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
    parser.add_argument("amrex_version", help="The AMReX version to compile")
    parser.add_argument(
        "dimension",
        type=int,
        choices=[2, 3],
        help="The dimension configure flag",
    )
    parser.add_argument("compiler", help="The compiler to use")
    parser.add_argument(
        "debug", type=int, help="Whether to set the debug flag"
    )
    parser.add_argument(
        "profile", type=int, help="Whether to set the profile flag"
    )
    parser.add_argument(
        "coverage", type=int, help="Whether to set the coverage flag"
    )
    parser.add_argument(
        "memcheck",
        choices=["0", "msan", "asan"],
        help="The type of memcheck to use (if any)",
    )
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
    Write the JSON configuration file.

    Parameters
    ----------
    output_path
        Path to the output config file.
    config
        Parsed configuration object.
    """
    logger.info("Writing output config: %s", output_path)
    logger.debug("Output config:\n%s", json.dumps(config, indent=4))
    with open(output_path, "w") as config_file:
        json.dump(config, config_file, indent=4)


def generate_configure_command(
    base_configure_cmd: str,
    amrex_version: str,
    dimension: int,
    compiler: str,
    debug: int,
    profile: int,
    coverage: int,
    memcheck: str,
) -> list[str]:
    """
    Generate an Alamo configure command.

    Parameters
    ----------
    base_configure_cmd
        Base Alamo configure command (usually ./configure).
    amrex_version
        AMReX version (git tag) to build.
    dimension
        Spatial dimension to configure.
    compiler
        Compiler to use.
    debug
        Whether to use the --debug flag.
    profile
        Whether to use the --profile flag.
    coverage
        Whether to use the --coverage flag.
    memcheck
        Whether to use the --memcheck flag and which memcheck tool to
        use.

    Returns
    -------
    list[str]
        Configure command split by white spaces.
    """
    logger.info("Generating configure command...")

    configure_cmd = (
        f"{base_configure_cmd} "
        f"--build-amrex-tag {amrex_version} "
        f"--dim {dimension} "
        f"--comp {compiler}"
    )
    configure_cmd += " --debug " if debug else ""
    configure_cmd += " --profile " if profile else ""
    configure_cmd += " --coverage " if coverage else ""

    if memcheck != "0":
        configure_cmd += f" --memcheck --memcheck-tool {memcheck}"

    logger.info("Generated configure command: %s", configure_cmd)
    return configure_cmd.replace("  ", " ").strip().split(" ")


def generate_make_target(
    amrex_dir: str,
    amrex_version: str,
    dimension: int,
    compiler: str,
    debug: int,
    profile: int,
    coverage: int,
    memcheck: str,
) -> str:
    """
    Generate the make target based on the configure flags.

    Parameters
    ----------
    amrex_dir
        AMReX checkout location relative to Alamo root.
    amrex_version
        AMReX version (git tag) to build.
    dimension
        Spatial dimension to configure.
    compiler
        Compiler to use.
    debug
        Whether to use the --debug flag.
    profile
        Whether to use the --profile flag.
    coverage
        Whether to use the --coverage flag.
    memcheck
        Whether to use the --memcheck flag and which memcheck tool to
        use.

    Returns
    -------
    str
        Make target for the given configure command.
    """
    logger.info("Generate make target...")

    target = f"{amrex_dir}/{dimension}d"
    target += "-debug" if debug else ""
    target += "-asan" if memcheck == "asan" else ""
    target += "-msan" if memcheck == "msan" else ""
    target += "-profile" if profile else ""
    target += "-coverage" if coverage else ""
    target += f"-{compiler}-{amrex_version}"

    logger.info("Generated make target: %s", target)
    return target


def main() -> None:
    """Parse command-line arguments and process the YAML file."""
    args = parse_args()
    configure_logging(args.log_level)
    logger.debug("Parsed args:\n%s", args)

    logger.info("Parsing config: %s", args.config)
    (output_config,) = parse_config(Path(args.config))

    output_config["configure_cmd"] = generate_configure_command(
        output_config["base_configure_cmd"],
        args.amrex_version,
        args.dimension,
        args.compiler,
        args.debug,
        args.profile,
        args.coverage,
        args.memcheck,
    )

    output_config["make_target"] = generate_make_target(
        str(Path(output_config["amrex_dir"])),
        args.amrex_version,
        args.dimension,
        args.compiler,
        args.debug,
        args.profile,
        args.coverage,
        args.memcheck,
    )

    write_json_config(Path(args.output), output_config)


if __name__ == "__main__":
    main()
