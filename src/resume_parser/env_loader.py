"""Safe .env loading.

`.env` is committed git-crypt-encrypted (see docs/SECRETS.md) so it round
-trips through `git clone`/`git pull`. On machines/CI runners where the repo
hasn't been `git-crypt unlock`ed, the file on disk is still the raw encrypted
blob, which is not valid UTF-8/dotenv syntax. Loading it is a pure
convenience on top of whatever's already in the environment, so a decode
failure here is reported and skipped rather than crashing every module that
imports this at import time.
"""
import logging
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def load_dotenv_safely(path: Path) -> None:
    try:
        load_dotenv(path)
    except (UnicodeDecodeError, ValueError) as error:
        logger.warning(
            "[env_loader] Failed to load %s (likely still git-crypt encrypted, "
            "e.g. in CI or before `git-crypt unlock`): %s. "
            "Remedy: skipping .env load, relying on real environment variables.",
            path,
            error,
        )
