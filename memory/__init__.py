from typing import Any


class KeyStore:
    def __init__(self) -> None:
        self.__store: dict[Any, Any] = {}

    def set(self, key: Any, value: Any) -> None:
        self.__store[key] = value

    def get(self, key: Any) -> Any | None:
        return self.__store.get(key)

    def contains(self, key: Any) -> bool:
        return key in self.__store

    def delete(self, key: Any) -> None:
        del self.__store[key]
