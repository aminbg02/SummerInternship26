"""if the  flask env = production it requires jwt and ferent keys to work
"""
import os

from app import create_app
from app.config import Config, ProductionConfig

IS_PRODUCTION = os.environ.get("FLASK_ENV", "development") == "production"

app = create_app(ProductionConfig if IS_PRODUCTION else Config)

if __name__ == "__main__":

    app.run(host="127.0.0.1", port=5000, debug=not IS_PRODUCTION, threaded=True)
