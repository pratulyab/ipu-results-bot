import os, sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "resultsbot.settings")
import django
django.setup()
import requests
import tempfile

from result.views import PDFReader as pdf

check = {'batches': ['2014','2015'], 'colleges': ['164']}

def parse(url):
	print('Parsing ', url)
	f = tempfile.NamedTemporaryFile(delete=False)
	try:
		r = requests.get(url)
		f.write(r.content)
		pdf(f.name, check=check)
		f.close()
	finally:
		os.remove(f.name)

if __name__ == '__main__':
	if len(sys.argv) == 2:
		try:
			f = open(sys.argv[1], 'r')
		except:
			print('Please provide valid file name as argument')
			exit(0)
		link = f.readline()
		while link:
			parse(link.replace('\n', ''))
			link = f.readline()
	else:
		while(1):
			url = input('Enter URL to IPU Result PDF doc: ')
			if url == 'year':
				only_year = input('year')
				check['batches'] = list(only_year)
				continue
			parse(url)
