import os, sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "resultsbot.settings")
import django
django.setup()
import requests
import tempfile

from result.views import PDFReader as pdf

while(1):
	url = input('Enter URL to IPU Result PDF doc: ')
	try:
		r = requests.get(url)
		f = tempfile.NamedTemporaryFile(delete=False)
		f.write(r.content)
		pdf(f.name)
		f.close()
	finally:
		os.remove(f.name)
