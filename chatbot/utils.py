from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render

import json, requests

def whitelist_domain(request):
	headers = {'Content-Type': 'application/json'}
	url = "https://graph.facebook.com/v2.6/me/thread_settings?access_token=%s" % settings.PAGE_ACCESS_TOKEN
	payload = {
		"setting_type" : "domain_whitelisting",
		"whitelisted_domains" : ["https://ipuresultsbot.herokuapp.com"],
		"domain_action_type": "add"
	}
	payload = json.dumps(payload)
	r = requests.post(url, headers=headers, data=payload)
	return HttpResponse(r.text)

def get_user_details(uid, params=['first_name', 'last_name',]):# 'profile_pic', 'gender', 'locale', 'timezone']):
#	payload = {'fields': ','.join(params), 'access_token': settings.PAGE_ACCESS_TOKEN}
	url = "https://graph.facebook.com/v2.6/%s?fields=%s&access_token=%s" % (uid, ','.join(params), settings.PAGE_ACCESS_TOKEN, )
	try:
		r = requests.get(url)
	except:
		return {}
	print("USER: ", r.text)
	r = json.loads(r.text)
	return r

def send_message(payload):
	headers = {'Content-Type': 'application/json'}
	url = "https://graph.facebook.com/v2.6/me/messages?access_token=%s" % (settings.PAGE_ACCESS_TOKEN, )
#	send_action(payload['recipient']['id'], "typing_off")
	payload = json.dumps(payload)
	r = requests.post(url, headers=headers, data=payload)
	if 'error' in r:
		r = json.loads(r.text)
		code = r['error']['code']
		if code in settings.SEND_ERROR_CODES:
			# Mail admins
			print ('-+' * 20)
			print(r)
			print ('-+' * 20)
			pass
		else:
			print("Error Occurred: %s" % (code, ))
			print(r)

def send_action(uid, action):
	headers = {'Content-Type': 'application/json'}
	url = "https://graph.facebook.com/v2.6/me/messages?access_token=%s" % (settings.PAGE_ACCESS_TOKEN, )
	payload = {
		"recipient": {
			"id" : uid
		},
		"sender_action": action
	}
	payload = json.dumps(payload)
	return requests.post(url, headers=headers, data=payload)

def send_quickreplies(payload):
	headers = {'Content-Type': 'application/json'}
	url = "https://graph.facebook.com/v2.6/me/messages?access_token=%s" % (settings.PAGE_ACCESS_TOKEN, )
	payload = json.dumps(payload)
	r = requests.post(url, headers=headers, data=payload)

def subscribe_app_to_page(request):
	url = "https://graph.facebook.com/v2.6/me/subscribed_apps?access_token=%s" % settings.PAGE_ACCESS_TOKEN
	r = requests.post(url)
	r = json.loads(r.text)
	print (r)
	if r['success']:
		print("App has been successfully subscribed to the page!")
	else:
		print("Unsuccessful subscription request")
	return HttpResponse(r)
