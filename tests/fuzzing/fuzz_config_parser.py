#!/usr/bin/env python
"""
Fuzzing tests for Ember config parser functionality.

This module tests the robustness of the ConfigManager class against malformed input.
"""

import configparser
import os
import sys
import tempfile
from typing import Optional

import atheris

# Ensure Ember is in the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from ember.core.config.manager import create_config_manager


def fuzz_config_file(data):
    """Fuzz test the ConfigManager by creating malformed config files."""
    fdp = atheris.FuzzedDataProvider(data)

    # Create a temporary file for the config
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as temp_file:
        try:
            # Generate random config content
            num_sections = fdp.ConsumeIntInRange(0, 10)
            config_content = ""

            for _ in range(num_sections):
                # Create section header
                if fdp.ConsumeBool():  # Sometimes create malformed section headers
                    section_name = fdp.ConsumeString(fdp.ConsumeIntInRange(1, 50))
                    config_content += f"[{section_name}]\n"
                else:
                    # Create intentionally malformed section
                    config_content += (
                        fdp.ConsumeString(fdp.ConsumeIntInRange(1, 20)) + "\n"
                    )

                # Add key-value pairs to the section
                num_pairs = fdp.ConsumeIntInRange(0, 20)
                for _ in range(num_pairs):
                    if fdp.ConsumeBool():  # Sometimes create well-formed KV pairs
                        key = fdp.ConsumeString(fdp.ConsumeIntInRange(1, 30))
                        value = fdp.ConsumeString(fdp.ConsumeIntInRange(0, 100))
                        config_content += f"{key} = {value}\n"
                    else:
                        # Create malformed KV pairs
                        config_content += (
                            fdp.ConsumeString(fdp.ConsumeIntInRange(1, 100)) + "\n"
                        )

            # Write the fuzzer-generated config to the temp file
            temp_file.write(config_content)
            temp_file.flush()

            # Try to load it with ConfigManager
            try:
                config_manager = create_config_manager(config_path=temp_file.name)

                # Perform some operations to exercise the code
                config = config_manager.get_config()
                # Access some attributes to exercise the code
                if hasattr(config, "registry"):
                    providers = getattr(config.registry, "providers", {})
                    for provider_name, provider in providers.items():
                        if hasattr(provider, "models"):
                            models = provider.models

            except Exception as e:
                # We expect some exceptions due to malformed configs,
                # but we should never crash with segfaults or other critical errors
                if isinstance(e, (configparser.Error, ValueError, OSError)):
                    # These are expected errors for malformed configs
                    pass
                else:
                    # Unexpected error type, re-raise
                    raise

        finally:
            # Clean up
            try:
                os.unlink(temp_file.name)
            except:
                pass


def run_fuzzer(time_limit: Optional[int] = None):
    """Run the fuzzer with the specified time limit or default iterations."""
    atheris.instrument_all()

    if time_limit:
        atheris.Setup(sys.argv, fuzz_config_file, time_limit=time_limit)
    else:
        atheris.Setup(sys.argv, fuzz_config_file)

    atheris.Fuzz()


if __name__ == "__main__":
    run_fuzzer()
