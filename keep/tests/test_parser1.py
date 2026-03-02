import os
import sys
import unittest
from unittest.mock import patch
from ..parser1 import main, extract_emails, extract_phone_numbers, extract_text_from_pdf

class TestParser1(unittest.TestCase):

    @patch('sys.argv', ['../parser1.py', '../data-engineer.pdf', '../data-engineer-pdf-1.json'])
    def test_main_with_pdf(self):
        with patch('parser1.extract_text_from_pdf', return_value='Contact me at john.doe@example.com or call 123-456-7890'):
            with self.assertLogs('parser1', level='INFO') as log:
                main()
                self.assertIn("INFO:parser1:emails: ['john.doe@example.com']", log.output)
                self.assertIn("INFO:parser1:phone_numbers:['123-456-7890']", log.output)

    @patch('sys.argv', ['../parser1.py', '../data-engineer.docx', '../data-engineer-docx-1.json'])
    def test_main_with_docx(self):
        with patch('parser1.extract_text_from_docx', return_value='Contact me at john.doe@example.com or call 123-456-7890'):
            with self.assertLogs('parser1', level='INFO') as log:
                main()
                self.assertIn("INFO:parser1:emails: ['john.doe@example.com']", log.output)
                self.assertIn("INFO:parser1:phone_numbers:['123-456-7890']", log.output)

if __name__ == '__main__':
    unittest.main()