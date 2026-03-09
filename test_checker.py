import sys
sys.path.append("/Users/mac/Desktop/Ivybound/pipeline")
from bulk_email_checker import verify_email_bulk

emails_to_test = [
    "504folder@conroeisd.net",
    "boldrighinil@pearlandisd.org",
    "communications@iltexas.org"
]

for email in emails_to_test:
    result = verify_email_bulk(email)
    print(f"{email}: {result}")
