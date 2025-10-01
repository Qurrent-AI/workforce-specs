#!/usr/bin/env python3
"""
Python script to replace bash secret processing functionality.
Fetches secrets from GCP Secret Manager and processes them into config.yaml.

This should eventually be replaced with the Qurrent OS secret management.
For now, this is a backwards compatible solution which avoids a lot of
extra dependencies.
"""

import os
import sys
from typing import Dict

import yaml
from google.cloud import secretmanager
from loguru import logger


def parse_and_export_yaml(yaml_content: str) -> Dict[str, str]:
    """
    Parse YAML content and export key-value pairs as environment variables.
    Mimics the bash parse_and_export_yaml function.

    Args:
        yaml_content: YAML content as string

    Returns:
        Dictionary of key-value pairs that were exported
    """
    exported_vars = {}

    try:
        # Parse YAML content
        data = yaml.safe_load(yaml_content)

        if isinstance(data, dict):
            # Handle nested dictionaries by flattening them
            for key, value in data.items():
                if isinstance(value, (str, int, float, bool)):
                    env_key = str(key).strip()
                    env_value = str(value).strip()
                    os.environ[env_key] = env_value
                    exported_vars[env_key] = env_value
                    logger.info(f"Exported environment variable: {env_key}")

        # Also handle simple key-value lines (like the bash version)
        for line in yaml_content.split("\n"):
            line = line.strip()
            if line.startswith("#") or ":" not in line or not line:
                continue

            try:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()
                if key and value:
                    os.environ[key] = value
                    exported_vars[key] = value
                    logger.info(
                        f"Exported environment variable from line parsing: {key}"
                    )
            except ValueError:
                continue

    except yaml.YAMLError as e:
        logger.warning(f"Failed to parse YAML, trying line-by-line parsing: {e}")
        # Fallback to line-by-line parsing like the bash version
        for line in yaml_content.split("\n"):
            line = line.strip()
            if line.startswith("#") or ":" not in line or not line:
                continue

            try:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()
                if key and value:
                    os.environ[key] = value
                    exported_vars[key] = value
                    logger.info(f"Exported environment variable: {key}")
            except ValueError:
                continue

    return exported_vars


def fetch_secret(project_id: str, secret_name: str) -> str:
    """Fetch the latest version of a secret using ADC inside GCE.

    Args:
        project_id: Google Cloud project ID.
        secret_name: Name of the secret in Secret Manager.

    Returns:
        Secret payload decoded as UTF-8 string.
    """

    client = secretmanager.SecretManagerServiceClient()
    secret_path = f"projects/{project_id}/secrets/{secret_name}/versions/latest"

    try:
        logger.info(
            f"Fetching secret: {secret_name} from project {project_id} using ADC credentials"
        )
        response = client.access_secret_version(request={"name": secret_path})
        secret_content = response.payload.data.decode("utf-8")
        logger.info(f"Successfully fetched secret: {secret_name}")
        return secret_content
    except Exception as e:
        logger.error(f"Failed to fetch secret {secret_name}: {e}")
        raise


def main():
    """
    Main function that replaces the bash secret processing logic.
    """
    logger.info("Starting Python secret processing script...")

    # Reset config.yaml before processing secrets
    logger.info("Resetting config.yaml...")
    with open("config.yaml", "w") as f:
        f.write("")  # Create empty file

    # Check if project ID environment variable is set
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        logger.error("Error: GOOGLE_CLOUD_PROJECT environment variable is not set")
        logger.error("Please set GOOGLE_CLOUD_PROJECT=your-project-id")
        sys.exit(1)

    logger.info(f"Using project ID: {project_id}")

    # Secret names defined in GCP Secrets Manager (can be added or reduced)
    secrets = ["customer_keys", "llm_keys", "additional_keys"]

    for secret_name in secrets:
        try:
            secret_content = fetch_secret(project_id, secret_name)

            # Parse and export YAML as environment variables
            exported_vars = parse_and_export_yaml(secret_content)
            logger.info(f"Exported {len(exported_vars)} variables from {secret_name}")

            # Append to config.yaml
            with open("config.yaml", "a") as f:
                f.write(secret_content)
                f.write("\n")  # Add newline for separation

            logger.info(f"Successfully processed secret: {secret_name}")

        except Exception as e:
            logger.error(f"Failed to process secret {secret_name}: {e}")
            sys.exit(1)

    logger.info("Successfully processed all secrets")


if __name__ == "__main__":
    main()
