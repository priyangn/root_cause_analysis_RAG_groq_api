import pandas as pd
import PyPDF2
import docx
from pathlib import Path
from typing import Dict, Any
import logging

from data_limits import read_tabular

logger = logging.getLogger(__name__)


class DocumentParser:
    @staticmethod
    def parse_pdf(file_path: str) -> str:
        try:
            with open(file_path, "rb") as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except Exception as e:
            logger.error(f"Error parsing PDF {file_path}: {e}")
            return ""

    @staticmethod
    def parse_csv(file_path: str) -> pd.DataFrame:
        return read_tabular(file_path, ".csv")

    @staticmethod
    def parse_excel(file_path: str) -> pd.DataFrame:
        return read_tabular(file_path, Path(file_path).suffix.lower())

    @staticmethod
    def parse_docx(file_path: str) -> str:
        try:
            doc = docx.Document(file_path)
            text = "\n".join([para.text for para in doc.paragraphs])
            return text
        except Exception as e:
            logger.error(f"Error parsing DOCX {file_path}: {e}")
            return ""

    @staticmethod
    def parse_txt(file_path: str) -> str:
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                return file.read()
        except Exception as e:
            logger.error(f"Error parsing TXT {file_path}: {e}")
            return ""

    @classmethod
    def parse_file(cls, file_path: str) -> Dict[str, Any]:
        path = Path(file_path)
        extension = path.suffix.lower()

        result = {
            "file_path": file_path,
            "file_name": path.name,
            "file_type": extension,
            "content": None,
            "dataframe": None,
        }

        if extension == ".pdf":
            result["content"] = cls.parse_pdf(file_path)
        elif extension == ".csv":
            result["dataframe"] = cls.parse_csv(file_path)
        elif extension in [".xlsx", ".xls"]:
            result["dataframe"] = cls.parse_excel(file_path)
        elif extension == ".docx":
            result["content"] = cls.parse_docx(file_path)
        elif extension == ".txt":
            result["content"] = cls.parse_txt(file_path)
        else:
            logger.warning(f"Unsupported file type: {extension}")

        return result
