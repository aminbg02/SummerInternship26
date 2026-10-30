import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mlflow

from app.blueprints.query import SYSTEM_PROMPT
from app.config import Config

PROMPT_NAME = "rag-system-prompt"


def main():
    mlflow.set_tracking_uri(Config.MLFLOW_TRACKING_URI)

    version = mlflow.genai.register_prompt(
        name=PROMPT_NAME,
        template=SYSTEM_PROMPT,
        commit_message="Registered from blueprints/query.py's SYSTEM_PROMPT constant.",

    )
    print(f"Registered '{PROMPT_NAME}' version {version.version}")

    mlflow.genai.set_prompt_alias(name=PROMPT_NAME, alias="production", version=version.version)
    print(f"Alias 'production' -> version {version.version}")


if __name__ == "__main__":
    main()
