# resume-parser
attempts to read a PDF file and parse it into common resume sections

## Setup
<pre>
python3 -m venv venv; 
source venv/bin/activate; 
python3 -m pip install --upgrade pip; 
python3 -m pip install -r requirements.txt;
</pre>

### use anthropic claude to extract structure as json from a pdf file
<pre>python parser4.py proj-mngr.pdf proj-mngr-pdf.json</pre>

### compute the json-schema of the json file
<pre>python compute_schema.py proj-mngr-pdf.json proj-mngr-pdf-schema.json</pre>

### likewise lets extract json data from a docx filed
<pre>python parser4.py proj-mngr.docx proj-mngr-docx.json</pre>

### compute the json-schema of the json file
<pre>python compute_schema.py proj-mngr-docx.json proj-mngr-docx-schema.json</pre>

### verify that the json-schema files are identical
<pre>diff proj-mngr-pdf-schema.json proj-mngr-docx-schema.json</pre>

### verify that the extracted json files are identical  
<pre>diff proj-mngr-pdf.json proj-mngr-docx.json</pre>