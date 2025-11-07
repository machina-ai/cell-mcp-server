"""Handles the creation of proxy URLs for API providers."""

import logging
import os
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urljoin, urlparse

import yaml

logger = logging.getLogger(__name__)

_proxy_config = None
_config_checked = False


def get_proxy_config() -> Optional[Dict]:
    """
    Parses the cell-cli config file to get the proxy configuration.

    Returns:
        A dictionary containing the proxy configuration, or None if not found.
    """
    global _proxy_config, _config_checked
    if _config_checked:
        return _proxy_config

    config_path = Path.home() / ".cell-cli" / "config.yaml"
    _config_checked = True

    if not config_path.is_file():
        logger.debug("Cell-cli config file not found at %s", config_path)
        return None

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            if "port" in config:
                _proxy_config = {"port": config["port"]}
                logger.info("Loaded proxy port %s from cell-cli config", config["port"])
                return _proxy_config
    except (yaml.YAMLError, IOError) as e:
        logger.error("Error reading or parsing cell-cli config file: %s", e)

    return None


def configure_proxy_for_providers(
    xai_base_url: str, openai_base_url: str, gemini_base_url: Optional[str]
) -> Dict[str, str]:
    """
    Configures the proxy for the X.AI, OpenAI, and Gemini providers.

    Args:
        xai_base_url: The default base URL for the X.AI provider.
        openai_base_url: The default base URL for the OpenAI provider.
        gemini_base_url: The default base URL for the Gemini provider.

    Returns:
        A dictionary with the updated base URLs for the providers.
    """
    proxy_config = get_proxy_config()
    if not proxy_config or "port" not in proxy_config:
        return {
            "xai": xai_base_url,
            "openai": openai_base_url,
            "gemini": gemini_base_url,
        }

    port = proxy_config["port"]
    proxy_base_url = f"http://localhost:{port}"

    # Build URLs with provider-specific paths
    xai_url = f"{proxy_base_url}/cell/v1.1/xai/v1"
    openai_url = f"{proxy_base_url}/cell/v1.1/openai/v1"
    gemini_url = f"{proxy_base_url}/cell/v1.1/gemini/"

    logger.info(f"Proxy configured. X.AI URL: {xai_url}, OpenAI URL: {openai_url}, Gemini URL: {gemini_url}")

    return {
        "xai": xai_url,
        "openai": openai_url,
        "gemini": gemini_url,
    }