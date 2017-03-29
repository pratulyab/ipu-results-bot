from django.core import validators
from django.db import models

from college.models import Subject, Semester
from student.models import Student

from decimal import Decimal

# Create your models here.

class Score(models.Model):
	VERDICT = (
				('P', 'Pass'),
				('F', 'Fail'),
			)
	total_marks = models.PositiveSmallIntegerField()
	internal_marks = models.PositiveSmallIntegerField()
	external_marks = models.PositiveSmallIntegerField()
	student = models.ForeignKey(Student, related_name="scores")
	subject = models.ForeignKey(Subject, related_name="scores")
	verdict = models.CharField(max_length=1, choices=VERDICT, default='P')
	back = models.BooleanField(default=False, help_text="If there was a back in this subject, at any point of time. Even though if, it was cleared later on.")
	grace = models.BooleanField(default=False)

	class Meta:
		unique_together = ['student', 'subject']

class SemWiseResult(models.Model):
	student = models.ForeignKey(Student, related_name="sem_results")
	semester = models.ForeignKey(Semester, related_name="results")
	credits_percentage = models.DecimalField(max_digits=4, decimal_places=2, validators=[validators.MinValueValidator(0), validators.MaxValueValidator(100)])
	normal_percentage = models.DecimalField(max_digits=4, decimal_places=2, validators=[validators.MinValueValidator(0), validators.MaxValueValidator(100)])
