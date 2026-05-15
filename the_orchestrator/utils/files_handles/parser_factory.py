from .parser.pdf_parser import PDFParse, BaseParser
from .parser.image_parser import ImageParser

class ParserFactory:
    _register_class = {}

    @classmethod
    def register(cls, mime_type: set[str], parser_class: BaseParser):
        for m in mime_type:
            if m in cls._register_class:
                raise ValueError("Mime type already registered")
            cls._register_class[m] = parser_class

    @classmethod
    def get_parser(cls, mime: str) -> BaseParser:
        if mime in cls._register_class:
            return cls._register_class[mime]
        raise ValueError("No parser registered for mime type: {}".format(mime))


ALLOWED_PDF_MIME = {"application/pdf"}
ALLOWED_IMAGE_MIME = {"image/jpeg", "image/png", "image/gif", "image/bmp", "image/webp"}

parser = ParserFactory()

parser.register(ALLOWED_PDF_MIME, PDFParse)
parser.register(ALLOWED_IMAGE_MIME, ImageParser)
