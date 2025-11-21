import os
import tomllib

from typing import Any

STATIC_FOLDER = "static"
BUFFER_SIZE = 1024


class Configuration:
    def __init__(self, config_file: str) -> None:
        self.__config_path = config_file
        self.__config_data: dict[str, dict[str, Any]] = {}

        if os.path.exists(config_file):
            self.reload()
        else:
            self.__config_data = {
                "raccoon": {
                    "cookie_name": "__rsession",
                    "host_ip": "0.0.0.0",
                    "host_port": 80,
                    "max_header_size_bytes": 1024,
                    "max_body_size_bytes": 1_000_000_000,
                    "challenge_time_ms": 5000,
                    "cookie_expire_time_minutes": 60,
                },
                "routes": {
                    "default": "127.0.0.1:8000",
                    "example_com": "127.0.0.1:8000"
                }
            }

            with open(config_file, "w") as f:
                for key, config in self.__config_data.items():
                    f.write(f"[{key}]\n")
                    for subkey, value in config.items():
                        if isinstance(value, str):
                            f.write(f"{subkey} = \"{value}\"\n")
                        else:
                            f.write(f"{subkey} = {value}\n")
                    f.write("\n")

    def get_value(self, config_name: str, key: str) -> Any | None:
        if config_name not in self.__config_data:
            return None
        if key not in self.__config_data[config_name]:
            return None
        return self.__config_data[config_name][key]

    def get_config(self, config_name: str) -> dict[str, Any] | None:
        if config_name not in self.__config_data:
            return None
        return self.__config_data[config_name]

    def reload(self) -> None:
        with open(self.__config_path, "rb") as f:
            self.__config_data = tomllib.load(f)
