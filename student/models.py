from django.core import validators
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.signals import m2m_changed, pre_save
from django.dispatch import receiver

from college.models import Batch, College, Stream, Semester
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
	semesters = models.ManyToManyField(Semester, through='SemWiseResult', related_name="students", blank=True)

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

	def _get_full_name(self):
		return "%s %s" % (self.first_name.title(), self.last_name.title())

	def __str__(self):
		return "%s (%s %s)" % (self.enrollment, self.first_name, self.last_name)
	full_name = property(_get_full_name)

class SemWiseResult(models.Model):
	student = models.ForeignKey(Student, related_name="sem_results")
	semester = models.ForeignKey(Semester, related_name="results")
	normal_total = models.PositiveSmallIntegerField(null=True, blank=True)
	weighted_total = models.PositiveSmallIntegerField(null=True, blank=True)
	credits_percentage = models.DecimalField(max_digits=4, decimal_places=2, validators=[validators.MinValueValidator(0), validators.MaxValueValidator(100)])
	normal_percentage = models.DecimalField(max_digits=4, decimal_places=2, validators=[validators.MinValueValidator(0), validators.MaxValueValidator(100)])
	credits_obtained = models.PositiveSmallIntegerField(null=True, blank=True)
	total_credits = models.PositiveSmallIntegerField(null=True, blank=True)
	total_subjects = models.PositiveSmallIntegerField(null=True, blank=True)

	def update(self):
		''' Updates all fields by iterating over each subject of semester '''
		# Assumes that all the relevant scores are created already
		# Therefore, parse the pdfs in increasing order of sem number in order to create the sem result first before individual score updation
		normal_total = 0
		weighted_total = 0
		credits_obtained = 0
		subjects = self.semester.subjects.all()
		for subject in subjects:
			score = Score.objects.get(student=self.student, subject=subject)
			normal_total += score.total_marks
			weighted_total += (subject.credits * score.total_marks)
			if score.passed:
				credits_obtained += subject.credits
		sem_credits = self.semester.credits
		total_subjects = subjects.count()
		if not sem_credits or not total_subjects:
			# Finding same semester but of different batch
			sem = self.semester
			diff_batch_sems = Semester.objects.filter(number=sem.number, batch__college=sem.batch.college, batch__stream=sem.batch.stream).exclude(pk=sem.pk)
			for sem in diff_batch_sems:
				if sem.subjects.exists() and sem.credits:
					sem_credits = sem.credits
					total_subjects = sem.subjects.count()
					break
		self.normal_total = normal_total
		self.weighted_total = weighted_total
		self.credits_obtained = credits_obtained
		self.credits_percentage = weighted_total / sem_credits
		self.normal_percentage = normal_total / total_subjects
		self.total_credits = sem_credits
		self.total_subjects = total_subjects
		self.save()

	def __str__(self):
		return "%s [Sem %d]" % (self.student.enrollment, self.semester.number)

	class Meta:
		unique_together = ['student', 'semester']

@receiver(pre_save, sender=SemWiseResult)
def validate_semester_students(sender, instance, **kwargs):
	student = instance.student
	semester = instance.semester
	if student.batch != semester.batch:
		raise ValidationError("Student %s doesn't belong to batch %s." % (student.enrollment, semester.batch))

from result.models import Score
