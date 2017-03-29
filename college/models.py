from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _

# Create your models here.

class Subject(models.Model):
	SUB_TYPE = (
			('T', 'Theory'),
			('P', 'Practical'),
		)
	paper_code = models.CharField(max_length=5, unique=True)
	name = models.CharField(max_length=128, blank=True)
	credits = models.PositiveSmallIntegerField()
	type = models.CharField(max_length=1, choices=SUB_TYPE, default='T')

	def __str__(self):
		return  "%s [%d]" % (self.paper_code, self.credits)

class Stream(models.Model):
	code = models.CharField(max_length=3, unique=True)
	name = models.CharField(max_length=32, null=True, blank=True)
	max_semesters = models.PositiveSmallIntegerField()

	def clean(self):
		super(Stream, self).clean()
		if self.max_semesters == 0 or self.max_semesters > 12:
			raise ValidationError(_('Make sure maximum number of semesters is between 1 and 12 (inclusive)'))

	def save(self, *args, **kwargs):
		self.full_clean()
		return super(Stream, self).save(*args, **kwargs)

	def __str__(self):
		if self.name:
			return "%s <%s>" % (self.name.upper(), self.code)
		else:
			return "<%s>" % (self.code, )

class College(models.Model):
	code = models.CharField(max_length=3, unique=True)
	name = models.CharField(max_length=128, null=True, blank=True)
	alias = models.CharField(max_length=16, null=True, blank=True)
	streams = models.ManyToManyField(Stream, related_name="colleges")

	def __str__(self):
		if self.alias:
			return "%s <%s>" % (self.alias.upper(), self.code)
		else:
			return "<%s>" % (self.code, )

class Batch(models.Model):
	YEAR_CHOICES = tuple(((str(y),str(y)) for y in range(2008, 2020)))
	college = models.ForeignKey(College, related_name="batches")
	stream = models.ForeignKey(Stream, related_name="batches")
	year = models.CharField(max_length=4, choices=YEAR_CHOICES)

	def __str__(self):
		return "%s%s%s" % (self.college.code, self.stream.code, self.year[2:])

	class Meta:
		verbose_name_plural = "Batches"
		unique_together = ['college', 'stream', 'year']

class Semester(models.Model):
	number = models.PositiveSmallIntegerField()
	batch = models.ForeignKey(Batch, related_name="semesters")
	subjects = models.ManyToManyField(Subject, related_name="semesters")
#	students = models.ManyToManyField('student.Student', related_name="semesters") # To avoid cyclic dependencies
	credits = models.PositiveSmallIntegerField(null=True, blank=True)

	def clean(self):
		super(Semester, self).clean()
		stream = self.batch.stream
		if self.number > int(stream.max_semesters):
			raise ValidationError(_('Invalid Semester Number. %s permits only %s semesters in total.' % (stream, stream.max_semesters)))
		elif self.number == 0:
			raise ValidationError(_('No such thing as zeroeth semester.'))

	def save(self, *args, **kwargs):
		self.full_clean()
		return super(Semester, self).save(*args, **kwargs)

	def __str__(self):
		return "%d Sem <%s>" % (self.number, self.batch.__str__())

	def get_students(self):
		return self.batch.students.all()
	
	class Meta:
		unique_together = ['number', 'batch']


# SIGNALS
@receiver(m2m_changed, sender=Semester.subjects.through)
def validate_semester_subjects(sender, **kwargs):
	semester = kwargs.get('instance')
	action = kwargs.get('action')
	subject_pks = kwargs.get('pk_set')
	batch = semester.batch
	other_semesters = batch.semesters.exclude(pk=semester.pk)
	
	if action and action == 'pre_add':
		number = semester.number
		subjects = Subject.objects.filter(pk__in = subject_pks)
		for subject in subjects:
			# Validating subject corresponding to year is chosen
			# 99101 is in first year
			# If there were a sub with code 99201, it would have been in 2nd year
			sub_year = int(subject.paper_code[2])
			sem_year = int((number+1)/2 if number%2 else number/2)
			if sub_year != sem_year:
				raise ValidationError(_('Subject %s is not intended for %s Sem, %s Year' % (subject.__str__(), number, sem_year)))
			# Validating whether subject was added for another semester, because 99101 might get included in both Sem 1 & 2
			found = [sem for sem in other_semesters if sem.subjects.filter(pk = subject.pk)]
			if found:
				raise ValidationError(_("Subject %s is already included in %d Sem" % (subject.__str__(), found[0].number)))
'''
@receiver(m2m_changed, sender=Semester.students.through)
def validate_semester_students(sender, **kwargs):
	semester = kwargs.get('instance')
	action = kwargs.get('action')
	student_pks = kwargs.get('pk_set')
	students = Student.objects.filter(pk__in=student_pks)
	batch = semester.batch
	if action and action == 'pre_add':
		for student in students:
			if student.batch != batch:
				raise ValidationError(_('Students can be added only to the semesters corresponding to their batch. %s %s %s' % (student, student.batch, batch)))
'''

from student.models import Student
