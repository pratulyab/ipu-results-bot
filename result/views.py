from django.shortcuts import render

from college.models import Batch, College, Semester, Stream, Subject
from student.models import Student
from result.models import Score

import PyPDF2 as pdf
from pdftables import get_pdf_page, page_to_tables
import re
from collections import defaultdict

# Create your views here.

'''
	IPU Results' PDF Rules:
	1) Each pdf is designated to a particular stream and semester
	2) Page having 'SCHEME OF EXAMINATIONS' holds the following data:
		-> Scheme Of Programme Code: ???
		-> Sem./Year: ?? SEMESTER (Eg. 01)
		-> Institution Code: ???
		-> Table of subjects for this programme, whose scores are displayed for students, until the next page with 'SCHEME OF EXAMINATIONS' heading
	3) If no such heading is there on the page, i.e. text not found, then following helpful data is present:
		-> Batch: ???? (Eg.2011 , signifying the back students' result)
		-> Sem.Year: ?? SEMESTER (Eg. 01)
		-> Examination: _______ (REAPPEAR/REGULAR/REVISED REAPPEAR/RECHECKING REGULAR)
'''

class PDFReader:
	
	def __init__(self, filepath, *args, **kwargs):
#		try:
		self.f = open(filepath, 'rb')
		self.doc = pdf.PdfFileReader(self.f)
		check = defaultdict(list)
		for key,value in kwargs.get('check', {}).items():
			check[key] = value
		self.start_reading(check)
		# 'check' dictionary is used to allow specific colleges', streams' or batches' data to be scraped from the pdf

#		except FileNotFoundError:
#			print('No such file found.')
#			exit()
#		except Exception as e:
#			print(e)
#			exit()
#		finally:
#			print('Closing file...')
#			self.f.close()

	def __del__(self):
		self.f.close()

	def handle_heading_page(self, text, table):
		stream = re.search(r'Scheme of Programme Code: (\d{3})', text).groups()[0]
		stream = Stream.objects.get_or_create(code=stream, defaults={'max_semesters': 12})[0] # Rectify max later on
		college = re.search(r'Institution Code: (\d{3})', text).groups()[0]
		college= College.objects.get_or_create(code=college)[0]
		college.streams.add(stream)
		
		rows = table[0]
		subjects = []
	# Creating subjects
		for i,row in enumerate(rows):
			if i == 0:
				continue
			subject_code = row[1].strip()
			subject_name = row[3].title().strip()
			subject_type = row[5].strip()[0]
			credits = int(row[4].strip())
			subjects.append(Subject.objects.get_or_create(paper_code=subject_code, defaults={'name':subject_name, 'credits':credits, 'type':subject_type})[0])
		subjects = [sub.pk for sub in subjects]
		return (Subject.objects.filter(pk__in=subjects)) # QuerySet
	
	def handle_result_page(self, text, check):
	# Extracting relevant text
		stream = re.search(r'Result of Programme Code: (\d{3})', text).groups()[0]
		college = re.search(r'Institution Code: (\d{3})', text).groups()[0]
		year = re.search(r'Batch: (\d{4})', text).groups()[0]

		if (check['streams'] and not stream in check['streams']) or (check['colleges'] and not college in check['colleges']) or (check['batches'] and not year in check['batches']):
			return
		
		examination = re.search(r'Examination: ([A-Z\s]+)', text).groups()[0]
		sem = int(re.search(r'Sem./Year: (\d{2})', text).groups()[0])
#		batch_str = stream + college + year[2:]
		text = re.sub(r'SID: \d{12}SchemeID: \d{12}', '', text)
		text = re.split(r'RTSID: \d{22}', text)[1]
	# Extracting objects
		stream = Stream.objects.get_or_create(code=stream, defaults={'max_semesters': 12})[0] # Rectify max later on
		college= College.objects.get_or_create(code=college)[0]
		college.streams.add(stream)
		batch = Batch.objects.get_or_create(college=college, stream=stream, year=year)[0]
		semester = Semester.objects.get_or_create(number=sem, batch=batch)[0]
	
	# Regex PHEW! __--__
		student_wise_pattern = r'(\d{11}[a-zA-Z\s]+(?P<sub>\d{5,6}\(\d\)(\s*(\d{1,3}\*?|A|\-)){3}\s*)+)'
		student_pattern = r'(\d{11})([a-zA-Z\s]+)'
		details_pattern = r'(\d{5,6})\s*\((\d)\)\s*(\d{1,3}\*?|A|\-)\s*(\d{1,3}\*?|A|\-)\s*(\d{1,3}\*?|A|\-)'
		
		student_wise_details = re.findall(student_wise_pattern, text)
		sem_credits = 0
	# Creating entries for students and their results
		for i,each in enumerate(student_wise_details):
			each = each[0].strip()
			enrollment, name = re.findall(student_pattern, each)[0]
		# Handling rare discrepancies in PDF
			coll, strm, yr = re.match(r'\d{3}(\d{3})(\d{3})(\d{2})', enrollment).groups()
			new_year = '20' + yr
			if coll != college.code:
				print('College %s != %s' % (coll, college.code))
				college = College.objects.get_or_create(code=coll)[0]
			if strm != stream.code:
				print('Stream %s != %s' % (strm, stream.code))
				stream = Stream.objects.get_or_create(code=strm, defaults={'max_semesters': 12})[0]
			college.streams.add(stream)
			if batch.year[2:] != yr:
				# then, an year drop student.. Therefore, create/retrieve batch according to him
				print('Batch %s != %s' % (batch.year[2:], yr))
				batch = Batch.objects.get_or_create(college=college, stream=stream, year=new_year)[0]
			if batch != semester.batch:
				semester = Semester.objects.get_or_create(number=sem, batch=batch)[0]
			name = name.title().split()
			student = Student.objects.get_or_create(enrollment=enrollment, defaults={'first_name':name[0], 'last_name':' '.join(name[1:]), 'batch':batch})[0]
			'''
			try:
				semester.students.add(student) # Add student to semester
			except Exception as e:
				print(e)
				print(semester)
				print(student)
				continue
			'''
			details = re.findall(details_pattern, each)
			for every in details:
				paper_code, credits, internal, external, total = every
				grace = False
				if '*' in total:
					total = total.replace('*', '')
					grace = True
				credits = int(credits)
				internal = 0 if not internal.isnumeric() else int(internal)
				external = 0 if not external.isnumeric() else int(external)
				total = 0 if not total.isnumeric() else int(total)
				verdict = 'F' if total < 50 else 'P'
				back = True if verdict == 'F' else False
				if i == 0:
					sem_credits += credits
			# Creating subjects
				try:
					subject = self.subjects.get(paper_code=paper_code)
				except Subject.DoesNotExist:
					# Create new subject and add it to self.subjects for subsequent queries
					subject = Subject.objects.create(paper_code=paper_code, credits=credits)
					subject_pks = [s.pk for s in self.subjects.all()] + [subject.pk]
					subject_pks = set(subject_pks)
					self.subjects = Subject.objects.filter(pk__in = subject_pks)
				semester.subjects.add(subject)
				score, created = Score.objects.get_or_create(student=student, subject=subject, defaults={'total_marks':total, 'internal_marks':internal, 'external_marks':external, 'verdict':verdict, 'back':back})
				if not created:
					if 'REGULAR' in examination:
					# Not updating grace and back if it is REAPPER or RECHECKING result
						Score.objects.filter(student=student, subject=subject).update(total_marks=total, internal_marks=internal, external_marks=external, grace=grace, back=back)
					else:
						Score.objects.filter(student=student, subject=subject).update(total_marks=total, internal_marks=internal, external_marks=external)
		semester.credits = sem_credits
		semester.save()
	
	def start_reading(self, check):
		total = self.doc.numPages
		for num in range(0, total):
			page = self.doc.getPage(num)
			text = page.extractText().strip().replace('\n','')
			if text.find("(SCHEME OF EXAMINATIONS)") == -1:
				self.handle_result_page(text, check)
			else:
				table = page_to_tables(get_pdf_page(self.f, num+1))
				self.subjects = self.handle_heading_page(text, table)
			# Subjects Extracted from scheme page. Therefore, subsequent pages  will be having results of these subjects, until next scheme
