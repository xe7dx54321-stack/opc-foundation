from .loader import load_yaml_config, load_json_config
from .schema import FoundationConfig

# Convenience alias used by public API docs
def load_config(path, fmt="yaml"):
    """Load config file; fmt='yaml' (default) or 'json'."""
    if fmt == "json":
        return load_json_config(path)
    return load_yaml_config(path)

__all__ = [
    "load_yaml_config",
    "load_json_config",
    "load_config",
    "FoundationConfig",
]