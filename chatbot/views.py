from django.conf import settings
from django.http import HttpResponse, Http404
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.generic import View
from django.views.decorators.csrf import csrf_exempt

from college.models import Batch, College, Semester, Stream, Subject
from result.models import Score
from student.models import Student

from .utils import get_user_details, send_action, send_message, send_quickreplies, subscribe_app_to_page, whitelist_domain

import json, re, requests

# Create your views here.

class ResultsBotView(View):
	standard_reply = 'Oops. I don\'t know how to handle that.\nPlease send \'help\' to see how can I serve you.'
	enrollment_pattern = r'(\d{3})(\d{3})(\d{3})(\d{2})'
	
	def get(self, request, *args, **kwargs):
		if request.GET.get('hub.verify_token', None) == settings.VERIFY_TOKEN:
			return HttpResponse(request.GET.get('hub.challenge'))
		else:
			raise Http404('Invalid token')
	
	@method_decorator(csrf_exempt)
	def dispatch(self, request, *args, **kwargs):
		return View.dispatch(self, request, *args, **kwargs)
	
	def send_semesters_qr(self, uid, student, token, *args, **kwargs):
		semesters = student.batch.semesters.all().order_by('number')
		if not semesters:
			payload = {'recipient':{'id':uid}, 'message':{'text':'Sorry, I don\'t have any data for you'}}
			send_message(payload)
		else:
			payload = {
				"recipient":{"id": uid},
				"message":{
					"text": "Choose a semester:"
				}
			}
			quick_replies = []
			for semester in semesters:
				sem = {
					"content_type":"text",
					"title":"Sem %d" % semester.number,
					"payload": "%s_%d" % (token, semester.number)
				}
				quick_replies.append(sem)
			payload['message']['quick_replies'] = quick_replies
			send_quickreplies(payload)

	def valid_enrollment(self, token):
		try:
			roll, coll, strm, yr = re.match(self.enrollment_pattern, token).groups()
		except:
			return None
		try:
			college = College.objects.get(code=coll)
		except College.DoesNotExist:
			return None
		try:
			stream = Stream.objects.get(code=strm)
		except Stream.DoesNotExist:
			return None
		try:
			batch = Batch.objects.get(college=college, stream=stream, year='20'+yr)
		except Batch.DoesNotExist:
			return None
		try:
			student = Student.objects.get(enrollment=token)
		except Student.DoesNotExist:
			return None
		return student

	def handle_text(self, uid, text):
		text = text.split()
		student = None
		for token in text:
			student = self.valid_enrollment(token)
			if student:
				break
		if not student:
			reply_404 = 'OOPS! No valid enrollment number provided.\n\nPlease type \'help\' for further instructions.'
			if re.search(self.enrollment_pattern, ''.join(text)):
				reply_404 = 'Sorry, I don\'t know results for this enrollment number. -.-\''
			payload = {'recipient':{'id':uid}, 'message':{'text':reply_404}}
			send_message(payload)
		else:
			self.send_semesters_qr(uid, student, token)

	def send_format(self, uid):
		format_str1 = "Result will be displayed in following format:\n"
		format_str2 = "Subject Name - Paper ID (Credits)\nInternal Marks + External Marks = Total Marks\n\n"
		payload = {'recipient':{'id':uid}, 'message':{'text': format_str1 + format_str2}}
		send_message(payload)

	def send_percentage_buttons(self, uid, student, semester, sem_subject_pks):
		payload = {
			"recipient" : {"id" : uid},
			"message": {
				"attachment":{
					"type": "template",
					"payload": {
						"template_type": "button",
						"text": "Find out the percentages for the enrollment number %s\n" % (student.enrollment,),
						"buttons": [
							{
								"type": "postback",
								"title": "For %d Semester" % (semester.number),
								"payload": "%d_%d<%s" % (student.pk, semester.number, (','.join(sem_subject_pks)))
							},
							{
								"type": "postback",
								"title": "Aggregate",
								"payload": "%d_ALL<" % (student.pk)
							}
						]
					}
				}
			}
		}
		send_message(payload)

	def handle_quickreply(self, uid, token):
		# Send a semester's result
		# Not using try, except because payload is generated for valid data only
		enrollment, sem = token.split('_')
		sem = int(sem)
		student = Student.objects.get(enrollment=enrollment)
		semester = student.batch.semesters.get(number=sem)
		subjects = semester.subjects.all()
		subject_pks = [str(subject.pk) for subject in subjects]
		reply = []
		for subject in subjects:
			score = student.scores.get(subject=subject, student=student)
			name = subject.name or subject.paper_code
			code = subject.paper_code
			credits = subject.credits
			internal = score.internal_marks
			external = score.external_marks
			total = score.total_marks
			reply.append("%s - %s (%d)\n%d + %d = %d\n\n" % (name, code, credits, internal, external, total))
		for msg in reply:
			payload = {'recipient':{'id':uid}, 'message':{'text':msg}}
			send_message(payload)
		self.send_percentage_buttons(uid, student, semester, subject_pks)

	def handle_percentage_postback(self, uid, token):
		print(token)
		student_pk, token = token.split('_')
		sem, subjects = token.split('<')
		sems_list = []
		student = Student.objects.get(pk=student_pk)
		credits_percentage = 0 # ALL(Credit*Marks)/(total credits * 100)
		normal_percentage = 0 # (Sum of marks)/(total subjects * 100)
		if sem == 'ALL':
			total_credits = 0
			weighted_marks = 0 # sum of Marks * Credit
			normal_marks = 0 # sum of Marks * 1
			total_subjects = 0
			semesters = student.batch.semesters.order_by('number')
			for semester in semesters:
				sems_list.append(semester)
				subjects = semester.subjects.all()
				for subject in subjects:
					score = student.scores.get(subject=subject)
					credits = subject.credits
					marks = score.total_marks
					total_credits += credits
					weighted_marks += credits*marks
					normal_marks += marks
					total_subjects += 1
			credits_percentage = (weighted_marks/(total_credits * 100)) * 100
			normal_percentage = (normal_marks/(total_subjects * 100)) * 100
		else:
			subjects = subjects.split(',')
			total_credits = 0
			weighted_marks = 0 # sum of Marks * Credit
			normal_marks = 0 # sum of Marks * 1
			total_subjects = 0
			subjects = Subject.objects.filter(pk__in = subjects)
			sems_list.append(Semester.objects.get(subjects__pk__in=[subjects[0].pk], students__pk__in=[student.pk]))
			for subject in subjects:
				score = student.scores.get(subject=subject)
				credits = subject.credits
				marks = score.total_marks
				total_credits += credits
				weighted_marks += credits*marks
				normal_marks += marks
				total_subjects += 1
			credits_percentage = (weighted_marks/(total_credits * 100)) * 100
			normal_percentage = (normal_marks/(total_subjects * 100)) * 100
		sems = [str(s.number) for s in sems_list]
		payload = {
			"recipient" : {"id" : uid},
			"message": {
				"attachment": {
					"type": "template",
					"payload": {
						"template_type": "list",
						"top_element_style": "compact",
						"elements": [
						{
							"title": "Percentages for %s" % enrollment,
							"subtitle": "1) w/ Credits\n2) w/o Credits",
						},
						{
							"title": "%.2f" % credits_percentage,
							"subtitle": "Semesters: %s" % ', '.join(sems),
							"buttons": [
							{
								"type": "element_share"
							}]
						},
						{
							"title": "%.2f" % normal_percentage,
							"subtitle": "Semesters: %s" % ', '.join(sems),
							"buttons": [
							{
								"type": "element_share"
							}]
						}],
						"buttons": [
						{
							"type": "element_share",
						}]
					}
				}
			}
		}
		from pprint import pprint
		pprint(payload)
		send_message(payload)
	
	def post(self, request, *args, **kwargs):
		response = json.loads(request.body.decode('utf-8'))
		print('*'*20)
		for entry in response['entry']:
			for message in entry['messaging']:
				print(message)
				uid = message['sender']['id']
				send_action(uid, "typing_on")
				if 'postback' in message:
				# Percentage
					self.handle_percentage_postback(uid, message['postback']['payload'])
				elif 'attachments' in message:
					payload = {'recipient':{'id':uid}, 'message':{'text':self.standard_reply}}
					send_message(payload)
				elif 'quick_reply' in message.get('message', ''):
				# Sem Result
					self.send_format(uid)
					self.handle_quickreply(uid, message['message']['quick_reply']['payload'])
				elif 'attachment' in message.get('message', ''):
					payload = {'recipient':{'id':uid}, 'message':{'text':self.standard_reply}}
					send_message(payload)
				else:
					text = message['message']['text']
					self.handle_text(uid, text)
		return HttpResponse()
