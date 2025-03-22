#!/usr/bin/env python3
"""
Generate a Docker image name based on build configuration parameters.

This script takes build configuration parameters and generates a standardized
Docker image name that can be used with a specific AMReX version tag.
"""
import argparse


def generate_docker_image_name(
    dimension: int,
    compiler: str,
    debug: int,
    profile: int,
    coverage: int,
    memcheck: str,
    os: str,
) -> str:
    """
    Generate a Docker image name based on build configuration.

    Parameters
    ----------
    dimension
        Spatial dimension (2 or 3).
    compiler
        Compiler used (e.g., g++, clang++).
    debug
        Whether debug mode is enabled (1) or not (0).
    profile
        Whether profiling is enabled (1) or not (0).
    coverage 
        Whether coverage is enabled (1) or not (0).
    memcheck
        Memory checking tool to use (e.g., 'asan', 'msan', or 'none').
    os
        Operating system (e.g., 'ubuntu2404').

    Returns
    -------
    str
        Generated Docker image name.
    """
    image_name = f"{dimension}d"

    if debug:
        image_name = f"{image_name}-debug"

    if memcheck == "asan":
        image_name = f"{image_name}-asan"

    if memcheck == "msan":
        image_name = f"{image_name}-msan"

    if profile:
        image_name = f"{image_name}-profile"

    if coverage:
        image_name = f"{image_name}-coverage"

    image_name = f"{image_name}-{compiler}-{os}"

    return image_name


def main() -> None:
    """Parse command line arguments and print the generated image name."""
    parser = argparse.ArgumentParser(
        description="Generate a Docker image name based on build parameters."
    )
    parser.add_argument(
        "dimension", 
        type=int, 
        help="Spatial dimension (2 or 3)"
    )
    parser.add_argument(
        "compiler", 
        help="Compiler (e.g., g++, clang++)"
    )
    parser.add_argument(
        "debug",
        type=int,
        choices=[0, 1],
        help="Enable debug mode (0 or 1)",
    )
    parser.add_argument(
        "profile",
        type=int,
        choices=[0, 1],
        help="Enable profiling (0 or 1)",
    )
    parser.add_argument(
        "coverage",
        type=int,
        choices=[0, 1],
        help="Enable coverage (0 or 1)",
    )
    parser.add_argument(
        "memcheck",
        choices=["0", "asan", "msan"],
        help="Memory checker to use",
    )
    parser.add_argument(
        "os",
        help="Operating system (e.g., ubuntu2404)",
    )

    args = parser.parse_args()

    image_name = generate_docker_image_name(
        args.dimension,
        args.compiler,
        args.debug,
        args.profile,
        args.coverage,
        args.memcheck,
        args.os,
    )

    print(image_name)


if __name__ == "__main__":
    main()
