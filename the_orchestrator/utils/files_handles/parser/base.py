from abc import ABC, abstractmethod


class BaseParser(ABC):
    @abstractmethod
    async def parse(self, file_path: str, llm, vision, file_data: bytes, user_query: str) -> str:
        pass
