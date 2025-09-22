"""Configuration handler for data retention policy."""
import os

import yaml

dirname = os.path.dirname(__file__)
with open(os.path.join(dirname, "data_retention.yaml"), "r") as f:
    data_retention_config = yaml.load(f, Loader=yaml.FullLoader)
