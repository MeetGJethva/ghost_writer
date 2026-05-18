from .base import BaseParser
from langchain_core.messages import HumanMessage
import base64

class ImageParser(BaseParser):
    async def parse(self, file_path: str = None, llm=None, vision=None, file_data: bytes= None, user_query: str = None) -> str:
        message = HumanMessage(content=[
            {
                "type": "text",
                "text": f"Based on the user query '{user_query}', analyze the image and provide a concise answer."
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64.b64encode(file_data).decode('utf-8')}"
                }
            }
        ])
        response = await vision.ainvoke([message])
        return response.content