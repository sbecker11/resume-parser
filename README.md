# resume-parser
attempts to read a PDF file and parse it into common resume sections

## Setup
<pre>
python3 -m venv venv; 
source venv/bin/activate; 
python3 -m pip install --upgrade pip; 
python3 -m pip install -r requirements.txt;
</pre>

### use anthropic claude to extract json structure from a pdf file
<pre>python resume_parser.py proj-mngr.pdf proj-mngr-pdf.json</pre>

### use anthropic claude to extract json structure from a docx file
<pre>python resume_parser.py proj-mngr.docx proj-mngr-docx.json</pre>

### verify that the extracted json files are -nearly- identical  
<pre>diff proj-mngr-pdf.json proj-mngr-docx.json</pre>

### compute the json-schema of the json file from the pdf file
<pre>python compute_json_schema.py proj-mngr-pdf.json proj-mngr-pdf-schema.json</pre>

### compute the json-schema of the json file from the docx file
<pre>python compute_json_schema.py proj-mngr-docx.json proj-mngr-docx-schema.json</pre>

### verify that the json-schema files are -nearly- identical
<pre>diff proj-mngr-pdf-schema.json proj-mngr-docx-schema.json</pre>

