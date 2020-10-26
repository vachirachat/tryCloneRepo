from django.db import models
from customers.models import Customer
from photographers.models import Photographer, AvailTime
import datetime


# Create your models here.
# TODO implement payment model that has a one to one relationship with all JobInfo with status matched
JOB_STATUS_CHOICES = [('PENDING', 'Pending'),
                      ('DECLINED', 'Declined'),
                      ('MATCHED', 'Matched'),
                      ('PAID', 'Paid'),
                      ('CANCELLED_BY_PHOTOGRAPHER', 'Cancelled by photographer'),
                      ('CANCELLED_BY_CUSTOMER', 'Cancelled by customer'),
                      ('PROCESSING', 'Processing Photos'),
                      ('COMPLETED', 'Completed'),
                      ('CLOSED', 'Closed'),
                      ('REVIEWED', 'Reviewed')]

TIME_CHOICES = [('HALF_DAY_MORNING', "Half-day(Morning-Noon)"),
                     ('HALF_DAY_NOON', "Half-day(Noon-Evening)"),
                     ('FULL_DAY', "Full-Day"),
                     ('NIGHT', "Night"),
                     ('FULL_DAY_NIGHT', "Full-Day and Night")]

STYLE_CHOICES = [('GRADUATION', 'Graduation'),
                 ('LANDSCAPE', 'Landscape'),
                 ('PORTRAIT', 'Portrait'),
                 ('PRODUCT', 'Product'),
                 ('FASHION', 'Fashion'),
                 ('EVENT', 'Event'),
                 ('WEDDING', 'Wedding'),
                 ('NONE', 'None')]

class JobReservation(models.Model):
    photoshoot_date = models.DateField()
    photoshoot_time = models.CharField(choices=TIME_CHOICES, max_length=20)
    job_avail_time = models.ForeignKey(AvailTime, related_name='photographer_avail_time', on_delete=models.CASCADE)

    def __str__(self):
        return str(self.photoshoot_date) + ' ' + self.photoshoot_time

class JobInfo(models.Model):
    # TODO write function to calculate Job Total price
    # TODO not allow job bookings from customers to photographers
    #  whose status is already past 'matched' for that time period
    job_id = models.AutoField(primary_key=True)
    job_title = models.CharField(max_length = 250)
    job_description = models.TextField(blank=True, null=True)
    job_customer = models.ForeignKey(Customer, related_name='jobs_customer', on_delete=models.CASCADE)
    job_photographer = models.ForeignKey(Photographer, related_name='jobs_of_photographer', on_delete=models.CASCADE)
    job_status = models.CharField(choices=JOB_STATUS_CHOICES, max_length=25, default='PENDING')
    job_style = models.CharField(choices=STYLE_CHOICES, max_length=15)
    job_location = models.CharField(max_length=400)    
    job_expected_complete_date = models.DateField()
    job_special_requirement = models.CharField(max_length=400, blank=True, null=True)
    job_reservation = models.ManyToManyField(JobReservation, null=True)
    job_url = models.URLField(max_length = 200, null=True, blank=True)

    # is_reviewed

    def __str__(self):
        return self.job_title + '\n' + self.job_customer.profile.user.first_name + " " + self.job_photographer.profile.user.first_name
    