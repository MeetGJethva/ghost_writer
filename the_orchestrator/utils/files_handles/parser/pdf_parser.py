from langchain_community.document_loaders import PyPDFLoader

from .base import BaseParser

class PDFParse(BaseParser):
    async def parse(self, file_path: str = None, llm=None, vision=None, file_data: bytes= None, user_query: str = None) -> str:
        if file_path is None:
            return "File path is not provided"
        loader = PyPDFLoader(file_path)
        documents = loader.load()
        return "\n".join([doc.page_content for doc in documents])


