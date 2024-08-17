import os
import requests
from dotenv import load_dotenv

url = 'https://iam.cloud.ibm.com/identity/token'
headers = {'Content-Type': 'application/x-www-form-urlencoded'}
data = {
    'grant_type': 'urn:ibm:params:oauth:grant-type:apikey',
    'apikey': os.getenv('IBMWATSON_API_KEY')
}

response = requests.post(url, headers=headers, data=data)

print(response.status_code)
print(response.json())
