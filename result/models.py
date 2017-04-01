from django.core import validators
from django.db import models

from college.models import Subject, Semester
from student.models import Student

from decimal import Decimal

# Create your models here.

class Score(models.Model):
	total_marks = models.PositiveSmallIntegerField()
	internal_marks = models.PositiveSmallIntegerField()
	external_marks = models.PositiveSmallIntegerField()
	student = models.ForeignKey(Student, related_name="scores")
	subject = models.ForeignKey(Subject, related_name="scores")
	passed = models.BooleanField(default=True)
	back = models.BooleanField(default=False, help_text="If there was a back in this subject, at any point of time. Even though if, it was cleared later on.")
	grace = models.BooleanField(default=False)

	class Meta:
		unique_together = ['student', 'subject']
