from langchain.document_loaders import PyPDFLoader

from .base import BaseParser

class PDFParse(BaseParser):
    def parse(self, file_path: str, llm, vision, file_data: bytes) -> str:
        loader = PyPDFLoader(file_path)
        documents = loader.load()
        return "\n".join([doc.page_content for doc in documents])


