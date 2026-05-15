from .parser_gateway import process_file
import asyncio

from langchain_groq import ChatGroq
from dotenv import load_dotenv

import base64
import os

load_dotenv()

async def main():

    def get_llm():
        return ChatGroq(
            model="meta-llama/llama-4-scout-17b-16e-instruct"
        )

    llm = get_llm()


    with open("payslip_686b166efe7f1e17a26497bd_2025_08 (2).pdf", "rb") as f:
        result = await process_file(file_path = "payslip_686b166efe7f1e17a26497bd_2025_08 (2).pdf",file_data=f.read(), llm=llm, vision=None, query="test")
        print("PDF DONE")
        print(result)


    with open("test.jpeg", "rb") as f:
        result = await process_file(file_data=f.read(), llm=llm, file_path=None, vision=None, query="test")
    print("PNG DONE")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())

