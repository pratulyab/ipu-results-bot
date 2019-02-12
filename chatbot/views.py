from django.conf import settings
from django.http import HttpResponse, Http404
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.generic import View
from django.views.decorators.csrf import csrf_exempt

from college.models import Batch, College, Semester, Stream, Subject
from result.models import Score
from student.models import Student, SemWiseResult

from .utils import get_user_details, send_action, send_message, send_quickreplies, subscribe_app_to_page, whitelist_domain

import json, re, requests

# Create your views here.

class ResultsBotView(View):
	standard_reply = 'Oops. I don\'t know how to handle that.\nPlease send \'help\' to see how can I serve you .'
	enrollment_pattern = r'(\d{1,3})(\d{3})(\d{3})(\d{2})'
	greetings_pattern = r'(h+e+ll+o+|y+o+|h+i+|h+e+y+|s+u+p+)!*\?*'
	appreciation_pattern = r'(th[ae]nk.*|coo+l|w+o+w+|a+w+e+s+o+m+e+|n+a*i+c+e+)!*'
	help_text = 'Hey %s!\nI\'m a Chatbot who is here to help you with your results related query. :)\n\nI am intended to serve you by providing the results of an 11-digits long enrollment number. :D\n\n Try sending me an enrollment number.\n\n Please consider liking and sharing the page if you find my work helpful. :)'
	
	def get(self, request, *args, **kwargs):
		if request.GET.get('hub.verify_token', None) == settings.VERIFY_TOKEN:
			return HttpResponse(request.GET.get('hub.challenge'))
		else:
			raise Http404('Invalid token')
	
	@method_decorator(csrf_exempt)
	def dispatch(self, request, *args, **kwargs):
		return View.dispatch(self, request, *args, **kwargs)
	
	def send_semesters_qr(self, uid, student, token, *args, **kwargs):
		semesters = student.sem_results.values('semester__number').order_by('semester__number')
		if not semesters.exists():
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
				number = semester['semester__number']
				sem = {
					"content_type":"text",
					"title":"Sem %d" % number,
					"payload": token+"_%d" % number
				}
				quick_replies.append(sem)
			payload['message']['quick_replies'] = quick_replies
			send_quickreplies(payload)

	def send_choices(self, uid, student):
		''' Send quick reply to choose b/w percentage and result '''
		payload = {
			"recipient":{"id": uid},
			"message":{
				"text": "What can I help you with?\nChoose: ",
				"quick_replies": [
				{
					"content_type": "text",
					"title": "Marks",
					"payload": "%d=SCORE" % student.pk
				},
				{
					"content_type": "text",
					"title": "Percentage",
					"payload": "%d=PERCENTAGE" % student.pk
				},
				]
			}
		}
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
		token = ('0'*(11 - len(token))) + token
		try:
			student = Student.objects.get(enrollment=token)
		except Student.DoesNotExist:
			return None
		return student

	def handle_text(self, uid, text):
		text = text.lower().split()
		student = None
		for token in text:
			student = self.valid_enrollment(token)
			if student:
				break
		if not student:
			reply_404 = 'OOPS! 😅 \n\nPlease send me an 11-digit enrollment number to get started with or send \'help\''
			found_enrollment = re.search(self.enrollment_pattern, ''.join(text))
			if found_enrollment:
				enrollment_no = ''.join(found_enrollment.groups()[:])
				enrollment_no = '0'*(11 - len(enrollment_no)) + enrollment_no
				reply_404 = 'Sorry, I don\'t know results for the enrollment number %s. -.-\'\n\nPlease visit the page to know which batches\' results do I know.\n\nTry sending me another one. :D' % (enrollment_no)
			payload = {'recipient':{'id':uid}, 'message':{'text':reply_404}}
			text = ' '.join(text)
			if re.match(self.greetings_pattern, text) or 'help' in text:
#				user_details = get_user_details(uid)
				user_details = {'first_name': 'there'}
				payload['message']['text'] = (self.help_text % (user_details['first_name'] if (user_details and user_details.get('first_name')) else 'there'))
			elif re.match(self.appreciation_pattern, text):
				payload['message']['text'] = "BOTs are here to serve you.. until singularity! 3:-)"
			send_message(payload)
		else:
			self.send_choices(uid, student)
	'''
	def send_format(self, uid):
		format_str1 = "Result will be displayed in following format:\n"
		format_str2 = "Subject Name - Paper ID (Credits)\nInternal Marks + External Marks = Total Marks\n\n"
		payload = {'recipient':{'id':uid}, 'message':{'text': format_str1 + format_str2}}
		send_message(payload)
	'''

	def send_percentage_buttons(self, uid, student, semester):
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
								"payload": "%d_%s" % (student.pk, SemWiseResult.objects.get(semester=semester, student=student).pk)
							},
							{
								"type": "postback",
								"title": "Aggregate",
								"payload": "%d_%s" % (student.pk, ','.join([str(s['pk']) for s in student.sem_results.values('pk')]))
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
		if '=' in token: # then choice has been made b/w percentage and score
			student_pk, what = token.split('=')
			student = Student.objects.get(pk=student_pk)
			token = token.replace('=', '+')
			self.send_semesters_qr(uid, student, token)
		else:
			# Sem Result
			student_pk, token = token.split('+')
			what, sem = token.split('_')
			sem = int(sem)
			student = Student.objects.get(pk=student_pk)
			semester = student.sem_results.select_related('semester').get(semester__number=sem).semester
			if what == 'SCORE':
#				self.send_format(uid)
				subjects = semester.subjects.all()

				format_str = "Subject Name - Paper ID (Credits)\nInternal Marks + External Marks = Total Marks\n\n"
				replies = []
				reply = [format_str]
				char_count = len(format_str)

				for subject in subjects:
					try:
						score = student.scores.get(subject=subject, student=student)
					except Score.DoesNotExist: # Maybe an elective that the student doesn't have
						continue
					name = subject.name or subject.paper_id
					paper_id = subject.paper_id
					credits = subject.credits
					internal = score.internal_marks
					external = score.external_marks
					total = score.total_marks
					text = "%s - %s (%d)\n%d + %d = %d\n\n" % (name, paper_id, credits, internal, external, total)
					if char_count + len(text) > settings.TEXT_MESSAGE_CHAR_LIMIT:
						replies.append(reply)
						reply = [text]
						char_count = len(text)
					else:
						reply.append(text)
						char_count += len(text)

				replies.append(reply)
				
				for msg in replies:
					msg = ''.join(msg)
					payload = {'recipient':{'id':uid}, 'message':{'text':msg}}
					send_message(payload)
				
				self.send_choices(uid, student)
			else:
				self.send_percentage_buttons(uid, student, semester)

	def handle_percentage_postback(self, uid, token):
		student_pk, token = token.split('_')
		result_pks = token.split(',')
		student = Student.objects.get(pk=student_pk)
		results = SemWiseResult.objects.select_related('semester').filter(pk__in=result_pks, student=student)
		sem_list = [sem['semester__number'] for sem in results.values('semester__number')]
		sem_subtitle = ("Sem(s): %d - %d" % (min(sem_list), max(sem_list))) if min(sem_list) != max(sem_list) else ("Semester: %d" % sem_list[0])
		values = results.values('normal_total', 'weighted_total', 'credits_obtained', 'total_credits', 'total_subjects')
		normal_total = sum(each['normal_total'] for each in values)
		weighted_total = sum(each['weighted_total'] for each in values)
		credits_obtained = sum(each['credits_obtained'] for each in values)
		total_credits = sum(each['total_credits'] for each in values)
		total_subjects = sum(each['total_subjects'] for each in values)
		credits_percentage = weighted_total / total_credits
		normal_percentage = normal_total / total_subjects

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
							"title": student.enrollment,
							"subtitle": sem_subtitle
						},
						{
							"title": "%.2f" % credits_percentage + '%',
							"subtitle": "credits based",
							"buttons": [
							{
								"type": "element_share"
							}]
						},
						{
							"title": "%.2f" % normal_percentage + '%',
							"subtitle": "w/o credits",
							"buttons": [
							{
								"type": "element_share"
							}]
						},
						{
							"title": "%d out of %d" % (credits_obtained, total_credits),
							"subtitle": "credits obtained",
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
		send_message(payload)
		self.send_choices(uid, student)
	
	def post(self, request, *args, **kwargs):
		response = json.loads(request.body.decode('utf-8'))
		for entry in response['entry']:
			for message in entry['messaging']:
				uid = message['sender']['id']
#				send_action(uid, "typing_on")
				try:
					if 'postback' in message:
					# Percentage
						self.handle_percentage_postback(uid, message['postback']['payload'])
					elif 'quick_reply' in message['message']:
						self.handle_quickreply(uid, message['message']['quick_reply']['payload'])
					elif 'attachment' in message['message'] or 'attachments' in message['message']:
						payload = {'recipient':{'id':uid}, 'message':{'text':self.standard_reply}}
						send_message(payload)
					else:
						text = message['message']['text']
						self.handle_text(uid, text)
				except Exception as e:
					print("***" + str(e))
		return HttpResponse()
