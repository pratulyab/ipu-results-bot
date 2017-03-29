from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models

from college.models import Batch, College, Stream
import re

# Create your models here.

class Student(models.Model):
	first_name = models.CharField(max_length=64, blank=True)
	last_name = models.CharField(max_length=64, blank=True)
	enrollment = models.CharField(
				max_length = 11,
				unique = True,
				validators = [RegexValidator(regex=r'^\d{11}$', message="Incorrect enrollment number format.")]
			)
	fbid = models.CharField(
				max_length = 32,
				unique = True,
				null = True,
				blank = True
			)
	batch = models.ForeignKey(Batch, related_name="students")

	def clean(self, *args, **kwargs):
		super(Student, self).clean()

	# Required inorder to allow NULL in UNIQUE COLUMN. Otherwise, blank string will be stored, which would raise
	# uniqueness error on subsequent student entry with empty fbid
		self.fbid = self.fbid or None
		return

	def save(self, *args, **kwargs):
		self.full_clean()
		try:
			roll, college, stream, year = re.match(r'^(\d{3})(\d{3})(\d{3})(\d{2})$', self.enrollment).groups()
		except AttributeError:
			raise ValidationError("Invalid enrollment number.")
		try:
			college = College.objects.get(code=college)
		except College.DoesNotExist:
			raise ValidationError("College hasn't been added yet.")
		try:
			stream = Stream.objects.get(code=stream)
		except Stream.DoesNotExist:
			raise ValidationError("No such programme/stream found.")
		# Checking whether the college has the stream
		if not college.streams.filter(pk=stream.pk):
			raise ValidationError("College doesn't offer this stream.")
		
		year = "20" + year # 2016
		
		# Checking whether batch exists
		try:
			batch = Batch.objects.get(college=college, stream=stream, year=year)
		except Batch.DoesNotExist:
			raise ValidationError("Batch hasn't been created yet")
		
		self.batch = batch
		return super(Student, self).save(*args, **kwargs)

	def full_name(self):
		return "%s %s" % (self.first_name.title(), self.last_name.title())

	def __str__(self):
		return "%s (%s %s)" % (self.enrollment, self.first_name, self.last_name)
