from typing import Protocol


class KeyValueCachePersistenceProviderProtocol(Protocol):

    def write(self, key, value):
        ...

    def read(self, key):
        ...
