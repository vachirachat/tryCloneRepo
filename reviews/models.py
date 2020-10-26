from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from jobs.models import JobInfo
# Create your models here.
# TODO create model


class ReviewInfo(models.Model):
    reviewJob = models.OneToOneField(JobInfo, limit_choices_to={'JobStatus': 'Closed'}, primary_key=True, on_delete=models.CASCADE)
    reviewDetail = models.TextField(null=True, blank=True)
    rateJob  = models.IntegerField(validators=[MinValueValidator(0),
                                       MaxValueValidator(10)])
    def __str__(self):
        return self.reviewDetail

