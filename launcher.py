"""
Zen MCP Server Launcher

This script acts as the main entry point for the `cell-mcp-server` executable.
Its primary responsibilities are:

1.  **Argument Handling**: Checks for command-line arguments like `--version` to
    provide quick information without fully initializing the server.

2.  **Environment Configuration**: Sets default environment variables required for the
    server to run correctly. This logic was previously in the wrapper shell scripts
    and is centralized here to make the package portable. It uses a helper function
    to ensure that any externally set, non-empty environment variables take precedence,
    maintaining flexibility for developers.

3.  **Server Execution**: After configuring the environment, it imports and calls
    the `run()` function from the main `server.py` module to start the MCP server.

This approach ensures that the server starts in a correctly configured environment,
regardless of how it's installed or executed, resolving issues with package
installation tools like `uv` or `pip` that autogenerate executable wrappers.
"""

import argparse
import importlib.metadata
import os
import sys


def set_default_env(name: str, value: str):
    """
    Set a default environment variable only if it's not already set to a non-empty value.
    This prevents empty strings in the environment from overriding the defaults.
    """
    if not os.environ.get(name):  # Catches None or empty string
        os.environ[name] = value


def main():
    """
    Parses arguments, sets up the environment, and runs the MCP server.
    """
    # --- Argument Parsing ---
    # This is done first to handle flags like --version before any heavy lifting.
    try:
        # Prioritize getting version from installed package metadata
        version = importlib.metadata.version("cell-mcp-server")
    except importlib.metadata.PackageNotFoundError:
        # Fallback for development environments where the package isn't installed
        try:
            from config import __version__ as version
        except ImportError:
            version = "unknown"

    parser = argparse.ArgumentParser(description="Cell MCP Server")
    parser.add_argument("--version", action="version", version=f"%(prog)s {version}")
    # Use parse_known_args() to handle --version and ignore any other args
    # that might be intended for the underlying server process.
    parser.parse_known_args()

    # --- Environment Configuration ---
    # Set default environment variables for compatibility with Gemini CLI and other clients.
    set_default_env("DISABLED_TOOLS", "tracer")
    set_default_env("DEFAULT_MODEL", "grok-code-fast")
    set_default_env("CONVERSATION_TIMEOUT_HOURS", "8")
    set_default_env("MAX_CONVERSATION_TURNS", "20")
    set_default_env("LOG_LEVEL", "ERROR")

    # --- Server Execution ---
    try:
        # Now that the environment is configured, import and run the server.
        # We import here to ensure the environment is set *before* any
        # server modules are loaded, as they may depend on these variables
        # at import time.
        from server import run

        sys.exit(run())
    except ImportError as e:
        print(
            f"Error: Failed to import the server. Make sure all dependencies are installed. Details: {e}",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
