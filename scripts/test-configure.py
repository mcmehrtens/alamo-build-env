#!/usr/bin/env python3
"""Test configure commands from a JSON file."""

import argparse
import datetime
import json
import os
import subprocess
import sys
import time


def parse_args() -> argparse.Namespace:
    """
    Parse command line arguments using argparse.

    Returns
    -------
    Namespace
        The parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Run configure commands from a JSON file and log results",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "input_file",
        help="JSON file containing configure commands to run",
    )
    parser.add_argument(
        "output_file",
        help="JSON file to write results to",
    )
    parser.add_argument(
        "--configure-path",
        default="./configure",
        help="Path to the configure script",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue running commands even if some fail",
    )

    return parser.parse_args()


def run_configure_command(
    command_args: list[str],
    configure_path="./configure",
) -> dict:
    """
    Run a single configure command and capture its output and status.

    Parameters
    ----------
    command_args
        List of arguments to pass to ./configure

    Returns
    -------
    dict
        Command metadata and result.
    """
    full_command = [configure_path, *list(command_args)]
    command_str = " ".join(full_command)

    result = {
        "command": command_str,
        "timestamp": datetime.datetime.now().isoformat(),
        "success": False,
        "stdout": "",
        "stderr": "",
        "exit_code": None,
        "duration_seconds": 0,
    }

    print(f"Running: {command_str}")
    start_time = time.time()

    try:
        process = subprocess.run(
            full_command,
            capture_output=True,
            text=True,
            check=False,
        )

        result["stdout"] = process.stdout
        result["stderr"] = process.stderr
        result["exit_code"] = process.returncode
        result["success"] = process.returncode == 0

    except Exception as e:
        result["stderr"] = str(e)
        result["success"] = False

    end_time = time.time()
    result["duration_seconds"] = round(end_time - start_time, 2)

    status = "SUCCESS" if result["success"] else "FAILURE"
    print(
        f"  → {status} (Exit code: {result['exit_code']}, "
        f"Time: {result['duration_seconds']}s)"
    )

    return result


def main():
    """Run configure commands and record the result."""
    args = parse_args()
    input_file = args.input_file
    output_file = args.output_file
    configure_path = args.configure_path

    # Check if configure exists
    if not os.path.isfile(configure_path) or not os.access(
        configure_path, os.X_OK
    ):
        print(f"Error: '{configure_path}' not found or not executable")
        sys.exit(1)

    # Load input JSON
    try:
        with open(input_file) as f:
            config_data = json.load(f)
    except Exception as e:
        print(f"Error loading input file: {e}")
        sys.exit(1)

    if "configure_commands" not in config_data:
        print("Error: Input JSON must contain a 'configure_commands' array")
        sys.exit(1)

    results = {
        "run_timestamp": datetime.datetime.now().isoformat(),
        "total_commands": len(config_data["configure_commands"]),
        "successful_commands": 0,
        "failed_commands": 0,
        "command_results": [],
    }

    for i, command_args in enumerate(config_data["configure_commands"]):
        print(f"\nCommand {i + 1}/{results['total_commands']}:")

        expanded_args = []
        for arg in command_args:
            if (
                " " in arg
                and not arg.startswith('"')
                and not arg.startswith("'")
            ):
                expanded_args.extend(arg.split())
            else:
                expanded_args.append(arg)

        result = run_configure_command(
            expanded_args, configure_path=configure_path
        )
        results["command_results"].append(result)

        if result["success"]:
            results["successful_commands"] += 1
        else:
            results["failed_commands"] += 1

    results["success_rate"] = (
        round(
            (results["successful_commands"] / results["total_commands"]) * 100,
            2,
        )
        if results["total_commands"] > 0
        else 0
    )

    try:
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {output_file}")
    except Exception as e:
        print(f"Error saving output file: {e}")
        sys.exit(1)

    print("\nSummary:")
    print(f"  Total commands: {results['total_commands']}")
    print(f"  Successful: {results['successful_commands']}")
    print(f"  Failed: {results['failed_commands']}")
    print(f"  Success rate: {results['success_rate']}%")

    if results["failed_commands"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
