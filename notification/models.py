from django.db import models
from django.utils import timezone
from users.models import CustomUserProfile

NOTI_ACTION_CHOICES = [('CREATE', 'Create'),
                      ('UPDATE', 'Update'),
                      ('CANCEL', 'Cancel')]

NOTI_STATUS_CHOICES = [('PENDING', 'Pending'),
                      ('DECLINED', 'Declined'),
                      ('MATCHED', 'Matched'),
                      ('PAID', 'Paid'),
                      ('CANCELLED_BY_PHOTOGRAPHER', 'Cancelled by photographer'),
                      ('CANCELLED_BY_CUSTOMER', 'Cancelled by customer'),
                      ('PROCESSING', 'Processing Photos'),
                      ('COMPLETED', 'Completed'),
                      ('CLOSED', 'Closed'),
                      ('REVIEWED', 'Reviewed')]

NOTI_READ_CHOICES = [('UNREAD', 'Unread'),
                      ('READ', 'Read')]

class Notification(models.Model): 
    noti_id = models.AutoField(primary_key=True)
    noti_job_id = models.IntegerField()
    noti_receiver = models.ForeignKey(CustomUserProfile,blank=False,related_name='noti_receiver',on_delete=models.CASCADE)
    noti_actor = models.ForeignKey(CustomUserProfile,blank=False,related_name='noti_actor',on_delete=models.CASCADE)
    noti_action = models.CharField(max_length=100)
    noti_status = models.CharField(choices=NOTI_STATUS_CHOICES, max_length=25)
    noti_description = models.TextField(blank=True, null=True,max_length=250)
    noti_timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    noti_read = models.CharField(choices=NOTI_READ_CHOICES, default='UNREAD', max_length=10)

    # public = models.BooleanField(default=False, db_index=True)

    def __str__(self):
        return self.noti_actor.user.username + ' -> ' + self.noti_receiver.user.username \
        + ': ' + self.noti_action