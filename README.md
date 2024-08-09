# resume-parser
attempts to read a PDF file and parse it into common resume sections

## Setup
<pre>
python3 -m venv venv; 
source venv/bin/activate; 
python3 -m pip install --upgrade pip; 
python3 -m pip install -r requirements.txt;
</pre>

## Define the resume PDF file
<a href="./data-engineer.pdf" target="_blank">data-engineer.pdf</a>

## run the parser
<pre>python parser4.py data-engineer.pdf data-engineer.json</pre>

# see the parsed result: 
data-engineer.json  
<pre>
{
  "contactInformation": {
    "name": "SHAWN BECKER",
    "location": "Lehi, UT",
    "phone": "(857) 891-0896",
    "email": "sbecker@alum.mit.edu"
  },
  "position": "DATA ENGINEERING / DATA ARCHITECTURE / MACHINE LEARNING",
  "professionalSummary": "As an experienced data engineering professional with expertise in Data Architecture and Machine Learning, I excel in problem-solving and leading teams to deliver innovative solutions to complex challenges across diverse industries, including entertainment, healthcare, finance, and manufacturing. My expertise includes creating scalable, secure, high-volume data pipelines leveraging cloud infrastructure and domain-specific data architecture while employing machine learning models to optimize data-driven decision-making processes. I thrive in dynamic environments, applying Agile methodologies to facilitate my team's focus on building working increments of well-architecture solutions that meet product owners' expectations. Driven by a passion for continuous learning, I relish tackling new challenges and achieving excellence in every project.",
  "workExperience": [
    {
      "company": "Fannie Mae / Risk Works Analysis Data Lake",
      "location": "Remote",
      "duration": {
        "start": "Mar 2024",
        "end": "Jun 2024"
      },
      "position": "Senior Data Engineer",
      "responsibilities": [
        "Documented processes to build, test, and deploy data pipeline components for in-house ETL framework.",
        "Extensive work with SQL, AWS Redshift, Glue, S3, IAM, Lambda, REST, Postman, SNS, and dbt.",
        "Utilized Agile practices with Jira, including backlog refinements, sprint planning, daily scrums, bi-weekly sprint reviews, and end-of-sprint retrospectives. Enabled the product owner to review each shipped product increment, allowing for potential revision or re-prioritization of backlog items."
      ]
    },
  ],
  ...
  "education": [
    {
      "institution": "Massachusetts Institute of Technology, Cambridge, Massachusetts",
      "degree": "PhD, Media Arts & Sciences, Machine Vision/Video Coding"
    },
    {
      "institution": "Brigham Young University, Provo, Utah",
      "degree": "MS, Computer Science, Medical Imaging/Computer Graphics"
    },
    {
      "institution": "Brigham Young University, Provo, Utah",
      "degree": "BS, Design Engineering Technology, CAD/CAE/CAM"
    }
  ],
  ...
  "certifications": "https://www.linkedin.com/in/shawnbecker/details/certifications/",
  "publications": "https://independent.academia.edu/shawnbecker",
  "patents": "https://patents.justia.com/inventor/shawn-c-becker",
  "websites": [
    {
      "type": "LinkedIn",
      "url": "https://www.linkedin.com/in/shawnbecker"
    },
    {
      "type": "Personal",
      "url": "http://spexture.com"
    }
  ]
}
</pre>

