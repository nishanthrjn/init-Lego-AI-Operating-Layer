# /// script
# dependencies = ["pyperclip"]
# ///
import os
import subprocess
import sys
import tempfile
import uuid

import pyperclip


def main():
    # Generate the unique dynamic temp paths
    base_temp = os.path.join(tempfile.gettempdir(), f"legoai-m7-{uuid.uuid4().hex}")

    commands = [
        ["uv", "sync", "--locked", "--group", "dev", "--no-install-project"],
        ["uv", "sync", "--locked", "--group", "dev", "--no-build-isolation"],
        # M7 contracts, architecture and governed integration
        [
            "uv",
            "run",
            "--locked",
            "--no-sync",
            "python",
            "-m",
            "pytest",
            "--basetemp",
            f"{base_temp}-agent",
            "-q",
            "tests/unit/execution/test_agent.py",
            "tests/architecture/test_agent.py",
            "tests/integration/composition/test_agent.py",
        ],
        # M6.5 and existing Model regressions
        [
            "uv",
            "run",
            "--locked",
            "--no-sync",
            "python",
            "-m",
            "pytest",
            "--basetemp",
            f"{base_temp}-model",
            "-q",
            "tests/unit/reference/test_model_routing.py",
            "tests/architecture/test_model_routing.py",
            "tests/unit/intelligence/test_model_values.py",
            "tests/unit/reference/test_model.py",
            "tests/integration/composition/test_model_governed.py",
        ],
        # Full Core, including build and fresh-install coverage
        [
            "uv",
            "run",
            "--locked",
            "--no-sync",
            "python",
            "-m",
            "pytest",
            "--basetemp",
            f"{base_temp}-core",
        ],
        [
            "uv",
            "run",
            "--locked",
            "--no-sync",
            "python",
            "-m",
            "mypy",
            "src",
            "tests",
            "examples/agent.py",
        ],
        ["uv", "run", "--locked", "--no-sync", "ruff", "check", "."],
        ["uv", "run", "--locked", "--no-sync", "ruff", "format", "--check", "."],
        ["uv", "build", "--no-build-isolation"],
        ["uv", "run", "--locked", "--no-sync", "python", "examples/agent.py"],
        ["git", "diff", "--check"],
    ]

    full_output = []
    has_error = False

    for cmd in commands:
        cmd_str = " ".join(cmd)
        header = f"\n{'-' * 60}\n>>> RUNNING: {cmd_str}\n{'-' * 60}\n"

        print(header, end="")
        full_output.append(header)

        # Run process, streaming stdout and stderr to the console and capturing it
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )

        for line in process.stdout:
            print(line, end="")
            full_output.append(line)

        process.wait()

        if process.returncode != 0:
            err_msg = f"\n[!] Command failed with exit code {process.returncode}. Stopping execution.\n"
            print(err_msg)
            full_output.append(err_msg)
            has_error = True
            break  # Stop executing further commands on failure

    # Compile the final string and copy to clipboard
    final_log = "".join(full_output)
    try:
        pyperclip.copy(final_log)
        print("\n[+] Success! The complete output has been copied to your clipboard.")
    except Exception as e:
        print(f"\n[-] Failed to copy to clipboard automatically: {e}")

    if has_error:
        sys.exit(1)


if __name__ == "__main__":
    main()
