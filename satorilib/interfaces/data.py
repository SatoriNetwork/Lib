from abc import ABC, abstractmethod


class FileManager(ABC):
    @abstractmethod
    def read(self, filePath: str):
        pass

    @abstractmethod
    def write(self, filePath: str, data):
        pass

    @abstractmethod
    def append(self, filePath: str, data):
        pass

    @abstractmethod
    def readLines(self, filePath: str, start: int, end: int):
        pass
