# for parser1.py pip install pdfplumber docx docx2txt typing_extensions
# for resume_parser.py pip install dotenv-python pydantic anthropic
# for tests pip install pytest-lazy-fixture

import sys
import argparse
import re
import pdfplumber
from docx import Document
import difflib
import logging
import docx2txt

logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# handles phone numbers like +1 857-891-0896, +1 (857) 891-0896, 8578910896, 857-891-0896, 857.891.0896, 856_891_0896
PHONE_REG = re.compile(r'(\+\d+)? ?((\(\d{3}\) ?)|(\d{3}\D?))?\d{3}\D?\d{4}')
# PHONE_REG = re.compile(r'(\+?\d{1,2}\s?)?(\(?\d{3}\)?[\s.-_]?)?\d{3}[\s.-_]?\d{4}')
# handles emails like 0b2J4@example.com shawn.becker@yahoo.com, 1.2.3@a.b.c
EMAIL_REG = re.compile(r'[A-Za-z0-9\._%+\-]+@[A-Za-z0-9\.\-]+\.[A-Za-z]{2,}')
# EMAIL_REG =   re.compile(r'[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+')

def extract_emails(resume_text):
    return re.findall(EMAIL_REG, resume_text)

def extract_phone_numbers(resume_text):
    return re.findall(PHONE_REG, resume_text)

def extract_text_from_docx_1(docx_path):
    doc = Document(docx_path)
    full_text = []
    for paragraph in doc.paragraphs:
        full_text.append(paragraph.text)
    return '\n'.join(full_text)

def extract_text_from_docx_2(docx_path):
    txt = docx2txt.process(docx_path)
    if txt:
        return txt.replace('\t', ' ')
    return None

def extract_text_from_docx(docx_path):
    text1 = extract_text_from_docx_1(docx_path)
    text2 = extract_text_from_docx_2(docx_path)
    if text1 and text2:
        print(show_diff(text1, text2))
        return text1
    elif text2:
        return text2
    else:
        return None
    
    
def show_diff(text1, text2):
    diff = difflib.ndiff(text1.splitlines(), text2.splitlines())
    return '\n'.join(diff)

def extract_text_from_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        full_text = []
        for page in pdf.pages:
            full_text.append(page.extract_text())
    return '\n'.join(full_text)

def main(args):
    
    input_resume_path = args[1]
    output_resume_json_path = args[2]
    
    print(f"input_resume_path: {input_resume_path}")
    print(f"output_resume_json_path: {output_resume_json_path}")

    if input_resume_path.lower().endswith('.pdf'):
        text = extract_text_from_pdf(input_resume_path)
        logger.info(f"text from pdf: {text}")
    elif input_resume_path.lower().endswith('.docx'):
        text = extract_text_from_docx(input_resume_path)
        logger.info(f"text from docx: {text}")
    else:
        print("Invalid input file format. Only PDF and DOCX files are supported.")
        
    emails = extract_emails(text)
    if emails:
        logger.info(f"emails: {emails}")

    phone_numbers = extract_phone_numbers(text)
    if phone_numbers:
        logger.info(f"phone_numbers:{phone_numbers}") 


if __name__ == '__main__':
    main(sys.args)
