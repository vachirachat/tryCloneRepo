from django.db import models
from customers.models import Customer
from photographers.models import Photographer
from jobs.models import JobInfo

PAYMENT_STATUS_CHOICES = [('DEPOSIT', 'Deposit'),
                          ('REMAINING', 'Remaining')]

# Create your models here.
# create model
class Payment(models.Model):
    payment_id = models.AutoField(primary_key=True)
    payment_status = models.CharField(choices=PAYMENT_STATUS_CHOICES, max_length=10)
    payment_customer = models.ForeignKey(Customer, related_name='payment_customer', on_delete=models.CASCADE)
    payment_photographer = models.ForeignKey(Photographer, related_name='payment_photographer', on_delete=models.CASCADE)
    payment_job = models.ForeignKey(JobInfo, related_name='payment_for_job', on_delete=models.CASCADE)
    payment_amount = models.FloatField()

    def __str__(self):
        return str(self.payment_id) + " " + self.payment_customer.profile.user.first_name + " to " + self.payment_photographer.profile.user.first_name