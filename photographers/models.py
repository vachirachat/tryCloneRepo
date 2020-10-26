from django.db import models
from users.models import CustomUserProfile
# Create your models here.


DAY_CHOICES = [('SUNDAY', 'Sunday'),
               ('MONDAY', 'Monday'),
               ('TUESDAY', 'Tuesday'),
               ('WEDNESDAY', 'Wednesday'),
               ('THURSDAY', 'Thursday'),
               ('FRIDAY', 'Friday'),
               ('SATURDAY', 'Saturday')]

STYLE_CHOICES = [('GRADUATION', 'Graduation'),
                 ('LANDSCAPE', 'Landscape'),
                 ('PORTRAIT', 'Portrait'),
                 ('PRODUCT', 'Product'),
                 ('FASHION', 'Fashion'),
                 ('EVENT', 'Event'),
                 ('WEDDING', 'Wedding'),
                 ('NONE', 'None')]

TIME_CHOICES = [('HALF_DAY_MORNING', "Half-day(Morning-Noon)"),
                     ('HALF_DAY_NOON', "Half-day(Noon-Evening)"),
                     ('FULL_DAY', "Full-Day"),
                     ('NIGHT', "Night"),
                     ('FULL_DAY_NIGHT', "Full-Day and Night")]


class Photo(models.Model):
    photo_link = models.URLField(primary_key=True, unique=True)

    def __str__(self):
        return self.photo_link


class AvailTime(models.Model):
    avail_date = models.CharField(max_length=20, choices=DAY_CHOICES)
    avail_time = models.CharField(max_length=16, choices=TIME_CHOICES)
    photographer_price = models.FloatField()

    def __str__(self):     
        return self.avail_date + " " + self.avail_time


class Equipment(models.Model):
    equipment_name = models.CharField(primary_key=True, unique=True, max_length=100)

    def __str__(self):
        return self.equipment_name


class Style(models.Model):
    style_name = models.CharField(primary_key=True, unique=True, max_length=20, choices=STYLE_CHOICES)

    def __str__(self):
        return self.style_name


class Photographer(models.Model):
    profile = models.OneToOneField(CustomUserProfile, on_delete=models.CASCADE, primary_key=True)
    # # Common fields
    # PhotographerID = models.AutoField(primary_key=True)
    # PhotographerFName = models.CharField(max_length=50)
    # PhotographerLName = models.CharField(max_length=50)
    # PhotographerSSN = models.CharField(max_length=13)
    # PhotographerEmail = models.EmailField()
    # PhotographerPassword = models.CharField(max_length=50)
    # Photographer fields
    # TODO Correctly implement fetching last online time
    photographer_last_online_time = models.DateTimeField(null=True, blank=True)
    photographer_style = models.ManyToManyField(Style,null=True, blank=True, related_name='styles')
    photographer_avail_time = models.ManyToManyField(AvailTime, blank=True, null=True)
    photographer_equipment = models.ManyToManyField(Equipment,related_name='photographer_equipment', null=True, blank=True)
    photographer_photos = models.ManyToManyField(Photo, related_name='photographer_photos', null=True, blank=True)

    def __str__(self):
        return self.profile.user.username


