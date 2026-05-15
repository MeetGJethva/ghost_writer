from .base import BaseParser
from langchain_core.messages import HumanMessage

class ImageParser(BaseParser):
    def parse(self, file_path: str, llm, vision, file_data: bytes, user_query: str) -> str:
        message = HumanMessage(content=[
            {
                "type": "text",
                "text": f"Based on the user query '{user_query}', analyze the image and provide a concise answer."
            },
            {
                "type": "image_url",
                "image_url": f"data:image/jpeg;base64,{base64.b64encode(file_data).decode('utf-8')}"
            }
        ])
        response = llm.invoke(messages=[message])
        return response.content
        