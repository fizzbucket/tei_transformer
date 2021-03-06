import os
import yaml

with open(os.path.join(os.path.dirname(__file__), "config.yaml"), "r") as f:
    config = yaml.load(f)


def update_config(curdir):
    """Update config with custom settings."""
    custom_settings = os.path.join(str(curdir), 'resources', 'config.yaml')
    try:
        with open(custom_settings) as f:
            custom_settings = yaml.load(f)
        config.update(custom_settings)
    except FileNotFoundError:
        pass
