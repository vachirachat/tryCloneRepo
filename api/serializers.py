from rest_framework import fields, serializers, status
from rest_framework.response import Response
from django.contrib.auth.validators import UnicodeUsernameValidator
from djoser.serializers import UserCreateSerializer as BaseUserRegistrationSerializer
from rest_framework.validators import UniqueValidator
from drf_writable_nested.serializers import WritableNestedModelSerializer
from drf_writable_nested.mixins import UniqueFieldsMixin, NestedUpdateMixin
from django.db.models import Q, Sum
# Import App Models
from photographers.models import Photographer, Photo, AvailTime, Equipment, Style
from customers.models import Customer
from jobs.models import JobInfo, JobReservation
from users.models import CustomUser, CustomUserProfile
from notification.models import Notification
from reviews.models import ReviewInfo
from payments.models import Payment
import datetime


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        exclude = ('is_superuser', 'is_staff', 'is_active', 'date_joined', 'groups', 'user_permissions','password')
        extra_kwargs = {
            'username': {
                'validators': [UnicodeUsernameValidator()],
            }
        }

    def create(self, validated_data):
        user = CustomUser.objects.create_user(username=validated_data['username'],
                                              password=validated_data['password'],
                                              user_type=validated_data['user_type'],
                                              email=validated_data['email'],
                                              first_name=validated_data['first_name'],
                                              last_name=validated_data['last_name']
                                              )
        return user

    def update(self, instance, validated_data):
        # special case to hash password
        if 'password' in validated_data :
            raw_password = validated_data.pop('password')
            if not instance.check_password(raw_password):
                instance.set_password(raw_password)
            
        instance.username = validated_data.get('username', instance.username)
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.email = validated_data.get('email', instance.email)
        instance.save()
        return instance

class ChangePasswordSerializer(serializers.ModelSerializer):
    old_password = serializers.CharField(max_length=128, write_only=True, required=True)
    new_password = serializers.CharField(max_length=128, write_only=True, required=True)
    class Meta:
        model = CustomUser
        fields = ['old_password','new_password']

    def update(self, instance, validated_data):
        old_password = validated_data.pop('old_password')
        new_password = validated_data.pop('new_password')
        if not instance.check_password(old_password):
            raise serializers.ValidationError('Your old password was entered incorrectly. Please enter it again.')
        else:
                instance.set_password(new_password)
        instance.save()
        return instance

class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(required=True, partial=True)

    class Meta:
        model = CustomUserProfile
        fields = '__all__'

    # Override default create method to auto create nested user from profile
    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user = UserSerializer.create(UserSerializer(), validated_data=user_data)
        validated_data['user'] = user
        profile = CustomUserProfile.objects.create(**validated_data)
        return profile

    def update (self, instance, validated_data):
        # update user instance before updating profile
        if 'user' in validated_data:
            user_data = dict(validated_data.pop('user'))
            user = UserSerializer.update(UserSerializer(required=False),instance=instance.user,validated_data=user_data)

        # update profile instance
        instance.user = user
        instance.ssn = validated_data.pop('ssn')
        instance.bank_account_number = validated_data.pop('bank_account_number')
        instance.bank_name = validated_data.pop('bank_name')
        instance.bank_account_name = validated_data.pop('bank_account_name')
        instance.phone = validated_data.pop('phone')

        instance.save()
        return instance

class PhotoSerializer(UniqueFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = Photo
        fields = '__all__'
        extra_kwargs = {
            'photo_link':{
                'validators' : [UniqueValidator(queryset=Photo.objects.all())]
            }
        }


class AvailTimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvailTime
        fields = '__all__'


class StyleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Style
        fields = '__all__'


class EquipmentSerializer(UniqueFieldsMixin,NestedUpdateMixin,serializers.ModelSerializer):
    class Meta:
        model = Equipment
        fields = '__all__'
        extra_kwargs = {
            'equipment_name': {
                'validators': [UniqueValidator(queryset=Equipment.objects.all())]
            },
        }


class PhotographerSerializer(WritableNestedModelSerializer):
    profile = ProfileSerializer(required=True, partial=True)
    photographer_photos = PhotoSerializer(many=True, required=False, allow_null=True)
    photographer_equipment = EquipmentSerializer(many=True, required=False, allow_null=True)
    photographer_styles = StyleSerializer(many=True, required=False)
    photographer_avail_time = AvailTimeSerializer(many=True, required=False)

    class Meta:
        model = Photographer
        fields = '__all__'

    # Override default create method to auto create nested profile from photographer
    def create(self, validated_data):
        profile_data = validated_data.pop('profile')
        profile = ProfileSerializer.create(ProfileSerializer(), validated_data=profile_data)
        photographer = Photographer.objects.create(profile=profile,
                                                   photographer_last_online_time=validated_data.pop('photographer_last_online_time'),
                                                   )

        # create photo instance then add to photographer_photos field
        # (photo_links are always unique)
        for photo_data in validated_data.pop('photographer_photos'):
            photo_data = dict(photo_data)
            photo_instance = Photo.objects.create(photo_link=photo_data['photo_link'])
            photographer.photographer_photos.add(photo_instance)

        # create equipment instance then add to photographer_equipments field
        for equipment_data in validated_data.pop('photographer_equipment'):
            equipment_data = dict(equipment_data)
            try :
                equipment_instance = Equipment.objects.get(equipment_name=equipment_data['equipment_name'])
            except :
                equipment_instance = Equipment.objects.create(equipment_name=equipment_data['equipment_name'])
            photographer.photographer_equipment.add(equipment_instance)

        # add selected style to photographer_style
        for style_data in validated_data.pop('photographer_style'):
            style_instance = Style.objects.get(style_name=style_data)
            photographer.photographer_style.add(style_instance)

        # add avail time
        # avail_list = []
        for avail_time_data in validated_data.pop('photographer_avail_time'):
            avail_time_data = dict(avail_time_data)
            try :
                avail_time_instance = AvailTime.objects.get(avail_date=avail_time_data['avail_date'],
                                                            avail_time=avail_time_data['avail_time'],
                                                            photographer_price=avail_time_data['photographer_price'])
            except :
                avail_time_instance = AvailTime.objects.create(**avail_time_data)
            photographer.photographer_avail_time.add(avail_time_instance)

            # avail_date=avail_time_data['avail_date']
            # photographer_price2=(avail_time_data['photographer_price'])/2
            # photographer_price3=(avail_time_data['photographer_price'])/3
            # if avail_time_data['avail_time'] == 'FULL_DAY':
            #     avail_list.append({'avail_date': avail_date, 'avail_time': 'HALF_DAY_MORNING', \
            #     'photographer_price': photographer_price2})
            #     avail_list.append({'avail_date': avail_date, 'avail_time': 'HALF_DAY_NOON', \
            #     'photographer_price': photographer_price2})
            # elif avail_time_data['avail_time'] == 'FULL_DAY_NIGHT':
            #     avail_list.append({'avail_date': avail_date, 'avail_time': 'HALF_DAY_MORNING', \
            #     'photographer_price': photographer_price3})
            #     avail_list.append({'avail_date': avail_date, 'avail_time': 'HALF_DAY_NOON', \
            #     'photographer_price': photographer_price3})
            #     avail_list.append({'avail_date': avail_date, 'avail_time': 'FULL_DAY', \
            #     'photographer_price': 2*photographer_price3})
            #     avail_list.append({'avail_date': avail_date, 'avail_time': 'NIGHT', \
            #     'photographer_price': photographer_price3})

        # # for full day:add 2halfs, full day night: add 3parts
        # for avail_time_data in avail_list:
        #     # avail_time_data = dict(avail_time_data)
        #     try :
        #         avail_time_instance = AvailTime.objects.get(avail_date=avail_time_data['avail_date'],
        #                                                     avail_time=avail_time_data['avail_time'],
        #                                                     photographer_price=avail_time_data['photographer_price'])
        #     except :
        #         avail_time_instance = AvailTime.objects.create(**avail_time_data)
        #     photographer.photographer_avail_time.add(avail_time_instance)

        profile.save()
        photographer.save()
        return photographer

    def update (self, instance, validated_data):
        # update profile
        if 'profile' in validated_data:
            profile_data = dict(validated_data['profile'])
            if 'user' in profile_data:
                profile_data_dict = dict(profile_data['user'])
                profile_instance = ProfileSerializer.update(ProfileSerializer(required=False), instance=instance.profile, validated_data=profile_data)

        # update photographer_photos
        if 'photographer_photos' in validated_data:
            instance.photographer_photos.clear()
            for photo_data in validated_data.pop('photographer_photos'):
                photo_data = dict(photo_data)
                try:
                    photo_instance = Photo.objects.get(photo_link=photo_data['photo_link'])
                except:
                    photo_instance = Photo.objects.create(photo_link=photo_data['photo_link'])
                instance.photographer_photos.add(photo_instance)

        # photographer_equipment
        if 'photographer_equipment' in validated_data:
            instance.photographer_equipment.clear()
            for equipment_data in validated_data.pop('photographer_equipment'):
                equipment_data = dict(equipment_data)
                try :
                    equipment_instance = Equipment.objects.get(equipment_name=equipment_data['equipment_name'])
                except :
                    equipment_instance = Equipment.objects.create(equipment_name=equipment_data['equipment_name'])
                instance.photographer_equipment.add(equipment_instance)

        # # photographer_avail_time
        if 'photographer_avail_time' in validated_data:
            instance.photographer_avail_time.clear()
        #     avail_list = []
            for avail_time_data in validated_data.pop('photographer_avail_time'):
                avail_time_data = dict(avail_time_data)
                try :
                    avail_time_instance = AvailTime.objects.get(avail_date=avail_time_data['avail_date'],
                                                                avail_time=avail_time_data['avail_time'],
                                                                photographer_price=avail_time_data['photographer_price'])
                except :
                    avail_time_instance = AvailTime.objects.create(**avail_time_data)
                instance.photographer_avail_time.add(avail_time_instance)            
            
        #         # check if fullday/fulldaynight
        #         avail_date=avail_time_data['avail_date']
        #         photographer_price2=(avail_time_data['photographer_price'])/2
        #         photographer_price3=(avail_time_data['photographer_price'])/3
        #         if avail_time_data['avail_time'] == 'FULL_DAY':
        #             avail_list.append({'avail_date': avail_date, 'avail_time': 'HALF_DAY_MORNING', \
        #             'photographer_price': photographer_price2})
        #             avail_list.append({'avail_date': avail_date, 'avail_time': 'HALF_DAY_NOON', \
        #             'photographer_price': photographer_price2})
        #         elif avail_time_data['avail_time'] == 'FULL_DAY_NIGHT':
        #             avail_list.append({'avail_date': avail_date, 'avail_time': 'HALF_DAY_MORNING', \
        #             'photographer_price': photographer_price3})
        #             avail_list.append({'avail_date': avail_date, 'avail_time': 'HALF_DAY_NOON', \
        #             'photographer_price': photographer_price3})
        #             avail_list.append({'avail_date': avail_date, 'avail_time': 'FULL_DAY', \
        #             'photographer_price': 2*photographer_price3})
        #             avail_list.append({'avail_date': avail_date, 'avail_time': 'NIGHT', \
        #             'photographer_price': photographer_price3})

        #     # for full day:add 2halfs, full day night: add 3parts
        #     for avail_time_data in avail_list:
        #         try :
        #             avail_time_instance = AvailTime.objects.get(avail_date=avail_time_data['avail_date'],
        #                                                         avail_time=avail_time_data['avail_time'],
        #                                                         photographer_price=avail_time_data['photographer_price'])
        #         except :
        #             avail_time_instance = AvailTime.objects.create(**avail_time_data)
        #         instance.photographer_avail_time.add(avail_time_instance)


        # photographer_last_online_time
        if 'photographer_last_online_time' in validated_data:
            instance.photographer_last_online_time = validated_data.pop('photographer_last_online_time')

        # photographer_style
        if 'photographer_style' in validated_data:
            instance.photographer_style.clear()
            for style_data in validated_data.pop('photographer_style'):
                style_instance = Style.objects.get(style_name=style_data)
                instance.photographer_style.add(style_instance)

        instance.save()
        return instance

class CustomerSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(required=True, partial=True)
    # fav_photographers = PhotographerSerializer(required=True, partial=True)
    # jobs_by_customer = JobSerializer(many=True)

    class Meta:
        model = Customer
        fields = '__all__'

        # Override default create method to auto create user from customer
    def create(self, validated_data):
        profile_data = validated_data.pop('profile')
        profile = ProfileSerializer.create(ProfileSerializer(), validated_data=profile_data)
        customer = Customer.objects.create(profile=profile)
        customer.fav_photographers.set(validated_data.pop('fav_photographers'))

        customer.save()
        profile.save()
        return customer

    def update (self, instance, validated_data):
        # update profile
        if 'profile' in validated_data:
            profile_data = dict(validated_data['profile'])
            if 'user' in profile_data:
                username = dict(profile_data['user'])['username']
                profile_instance = CustomUserProfile.objects.get(user__username=username)
                profile_instance = ProfileSerializer.update(ProfileSerializer, instance=profile_instance, validated_data=profile_data)

        if 'fav_photographers' in validated_data:
            instance.fav_photographers.clear()
            for favphotographers_data in validated_data.pop('fav_photographers'):
                if favphotographers_data != []:
                    instance.fav_photographers.add(favphotographers_data)

        instance.save()
        return instance


class NotificationSerializer(serializers.ModelSerializer):
    noti_actor = serializers.CharField(source='noti_actor.user.username')
    noti_receiver = serializers.CharField(source='noti_receiver.user.username')

    class Meta:
        model = Notification
        fields = '__all__'
    
    def create(self, validated_data):
        notification = Notification.objects.create(**validated_data)
        notification.save()
        return notification

    def update(self, instance, validated_data):
        if 'noti_read' in validated_data:
            for noti_instance in Notification.objects.filter(noti_receiver__user__username = instance.noti_receiver):
                    noti_instance.noti_read = validated_data['noti_read']
                    noti_instance.save()
            return noti_instance

class JobReservationSerializer(serializers.ModelSerializer):
    job_avail_time = AvailTimeSerializer(required=False, partial=True)
    class Meta:
        model = JobReservation
        fields = '__all__'

class JobSerializer(serializers.ModelSerializer):
    job_customer = serializers.CharField(source='job_customer.profile.user.username')
    job_photographer = serializers.CharField(source='job_photographer.profile.user.username')
    # job_customer = CustomerSerializer(required=True, partial=True)
    # job_photographer = PhotographerSerializer(required=True, partial=True)
    job_reservation = JobReservationSerializer(many=True, required=False, partial=True)
    job_total_price = serializers.FloatField(read_only=True)

    class Meta:
        model = JobInfo
        fields = '__all__'


    # Override default create method to auto create nested profile from photographer
    def create(self, validated_data):
        job_customer=validated_data.pop('job_customer')
        job_customer=Customer.objects.get(profile__user__username=job_customer['profile']['user']['username'])
        
        job_photographer_username=validated_data.pop('job_photographer')['profile']['user']['username']
        job_photographer=Photographer.objects.get(profile__user__username=job_photographer_username)

        job_status = "PENDING"
        
        # total_price = 0
        reservation_list = []
        # create job reservation instances and store them in reservation_list        
        for reservation_data in validated_data.pop('job_reservation'):
            reservation_data = dict(reservation_data)
            job_avail_time_data = dict(reservation_data['job_avail_time'])
            photoshoot_date = reservation_data['photoshoot_date']
            photoshoot_time = reservation_data['photoshoot_time']

            # Check if start date is valid
            if photoshoot_date < datetime.date.today():
                raise serializers.ValidationError('The selected date should not be before today.')
            # Check valid start&end date
            if validated_data["job_expected_complete_date"] < photoshoot_date:
                raise serializers.ValidationError('End date should not be before start date.')

            # check if reservation date and time is valid
            is_vaild = False
            week_days = ("MONDAY","TUESDAY","WEDNESDAY","THURSDAY","FRIDAY","SATURDAY","SUNDAY")
            for avail_time_instance in job_photographer.photographer_avail_time.all():
                if avail_time_instance.avail_date == week_days[photoshoot_date.weekday()] and avail_time_instance.avail_time == photoshoot_time:
                    # prevent creating job when photographer already has a job in the selected time
                    if JobInfo.objects.filter(Q(job_photographer__profile__user__username=job_photographer_username) &
                                              Q(job_reservation__photoshoot_date=photoshoot_date) & #old: no photoshoot_time
                                              Q(job_reservation__photoshoot_time=photoshoot_time) &
                                              Q(job_status='MATCHED')).exists(): #reconsider for more job_status
                        raise serializers.ValidationError('''The photographer is not available on your selected date and time''')                   
                    # if photoshoot_time == 'FULL_DAY' or photoshoot_time == 'FULL_DAY_NIGHT':
                    #     if JobInfo.objects.filter(Q(job_photographer__profile__user__username=job_photographer_username) &
                    #                           Q(job_reservation__photoshoot_date=photoshoot_date) &
                    #                           (Q(job_reservation__photoshoot_time='HALF_DAY_MORNING') |
                    #                           Q(job_reservation__photoshoot_time='HALF_DAY_NOON')) &
                    #                           Q(job_status='MATCHED')).exists():
                    #         raise serializers.ValidationError('''The photographer is not available on your selected date and time''')
                    #     if photoshoot_time == 'FULL_DAY_NIGHT' :
                    #         if JobInfo.objects.filter(Q(job_photographer__profile__user__username=job_photographer_username) &
                    #                           Q(job_reservation__photoshoot_date=photoshoot_date) &
                    #                           (Q(job_reservation__photoshoot_time='FULL_DAY') |
                    #                           Q(job_reservation__photoshoot_time='NIGHT')) &
                    #                           Q(job_status='MATCHED')).exists(): 
                    #             raise serializers.ValidationError('''The photographer is not available on your selected date and time''')
                    # elif photoshoot_time == 'NIGHT' :
                    #     if JobInfo.objects.filter(Q(job_photographer__profile__user__username=job_photographer_username) &
                    #                           Q(job_reservation__photoshoot_date=photoshoot_date) &
                    #                           Q(job_reservation__photoshoot_time='FULL_DAY_NIGHT') &
                    #                           Q(job_status='MATCHED')).exists():
                    #         raise serializers.ValidationError('''The photographer is not available on your selected date and time''')
                    # else:
                    #     if JobInfo.objects.filter(Q(job_photographer__profile__user__username=job_photographer_username) &
                    #                           Q(job_reservation__photoshoot_date=photoshoot_date) &
                    #                           (Q(job_reservation__photoshoot_time='FULL_DAY') |
                    #                           Q(job_reservation__photoshoot_time='FULL_DAY_NIGHT')) &
                    #                           Q(job_status='MATCHED')).exists():
                    #         raise serializers.ValidationError('''The photographer is not available on your selected date and time''')

                    try :
                        reservation_instance = JobReservation.objects.get(photoshoot_date=photoshoot_date,
                                                                          photoshoot_time=photoshoot_time,
                                                                          job_avail_time=avail_time_instance)
                    except :
                        reservation_instance = JobReservation.objects.create(photoshoot_date=photoshoot_date,
                                                                             photoshoot_time=photoshoot_time,
                                                                             job_avail_time=avail_time_instance)
                ##########################################################################
                    # total_price += avail_time_instance.photographer_price
                    reservation_list.append(reservation_instance)
                    
                    is_vaild = True
            if not is_vaild:
                raise serializers.ValidationError('''Your selected date and time for reservation is invalid for the photographer, please checkout photographer's available time''')
        job_info = JobInfo.objects.create(job_title=validated_data.pop('job_title'), 
                                        job_description=validated_data.pop('job_description'), 
                                        job_customer=job_customer, 
                                        job_photographer=job_photographer, 
                                        job_status='PENDING',
                                        job_style=validated_data.pop('job_style'),
                                        job_location=validated_data.pop('job_location'),
                                        job_expected_complete_date=validated_data.pop('job_expected_complete_date'),
                                        job_special_requirement=validated_data.pop('job_special_requirement'))
        job_info.job_reservation.add(*reservation_list)
        job_info.save()

        # Create a notification
        NotificationSerializer.create(self,validated_data={'noti_job_id': job_info.job_id, 'noti_receiver':job_photographer.profile, \
        'noti_actor':job_customer.profile, 'noti_action':'CREATE', 'noti_status':job_status, 'noti_read': 'UNREAD'})

        return job_info

    def update(self, instance, validated_data):
        # job_status
        if 'job_status' in validated_data:
            updated_status = validated_data.pop('job_status')
            if instance.job_status == 'DECLINED' or instance.job_status == 'CANCELLED_BY_CUSTOMER' \
                 or instance.job_status == 'CANCELLED_BY_PHOTOGRAPHER':
                raise serializers.ValidationError('The job has already been cancelled or declined')
            elif instance.job_status == 'REVIEWED':
                raise serializers.ValidationError('This job is done')
            elif instance.job_status == 'PENDING' and updated_status not in ['DECLINED', 'MATCHED', 'CANCELLED_BY_CUSTOMER'] :
                raise serializers.ValidationError('The job cannot be updated to this status')
            elif instance.job_status == 'MATCHED' and updated_status not in ['PAID', 'CANCELLED_BY_PHOTOGRAPHER', \
                 'CANCELLED_BY_CUSTOMER'] :
                raise serializers.ValidationError('The job cannot be updated to this status')
            elif instance.job_status == 'PAID' and updated_status not in ['PROCESSING', 'CANCELLED_BY_PHOTOGRAPHER', \
                 'CANCELLED_BY_CUSTOMER'] :
                raise serializers.ValidationError('The job cannot be updated to this status')
            elif instance.job_status == 'PROCESSING' and updated_status not in ['COMPLETED'] :
                raise serializers.ValidationError('The job cannot be updated to this status')
            elif instance.job_status == 'COMPLETED' and updated_status not in ['CLOSED'] :
                raise serializers.ValidationError('The job cannot be updated to this status')
            elif instance.job_status == 'CLOSED' and updated_status not in ['REVIEWED'] :
                raise serializers.ValidationError('The job cannot be updated to this status')
            else :
            # instance.job_status = validated_data.pop('job_status')
                instance.job_status = updated_status
            # Create a notification
                if instance.job_status == 'CANCELLED_BY_CUSTOMER' or instance.job_status == 'CANCELLED_BY_PHOTOGRAPHER' :
                    noti_action = 'CANCEL'
                else: noti_action = 'UPDATE'

                if instance.job_status == 'CANCELLED_BY_CUSTOMER' or instance.job_status == 'PAID' or instance.job_status == 'CLOSED' or instance.job_status == 'REVIEWED' :
                    NotificationSerializer.create(self,validated_data={'noti_job_id': instance.job_id, 'noti_receiver':instance.job_photographer.profile, \
                    'noti_actor':instance.job_customer.profile, 'noti_action':noti_action, 'noti_status':instance.job_status, 'noti_read':'UNREAD'})
                else:
                    NotificationSerializer.create(self,validated_data={'noti_job_id': instance.job_id, 'noti_receiver':instance.job_customer.profile, \
                    'noti_actor':instance.job_photographer.profile, 'noti_action': noti_action, 'noti_status':instance.job_status, 'noti_read':'UNREAD'})
            #insert job url
            if 'job_url' in validated_data:
                instance.job_url = validated_data.pop('job_url')

            instance.save()
            return instance

class GetJobsSerializer(serializers.ModelSerializer):
    job_customer = CustomerSerializer(required=True, partial=True)
    job_photographer = PhotographerSerializer(required=True, partial=True)
    job_reservation = JobReservationSerializer(many=True, required=False, partial=True)
    job_total_price = serializers.FloatField(read_only=True)

    class Meta:
        model = JobInfo
        fields = '__all__'

class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewInfo
        fields = '__all__'

class PaymentSerializer(serializers.ModelSerializer):
    payment_customer = serializers.CharField(source='payment_customer.profile.user.username')
    payment_photographer = serializers.CharField(source='payment_photographer.profile.user.username')

    class Meta:
        model = Payment
        fields = '__all__'
    
    def create(self, validated_data):
        payment_customer=validated_data.pop('payment_customer')
        payment_customer=Customer.objects.get(profile__user__username=payment_customer['profile']['user']['username'])
        
        payment_photographer_username=validated_data.pop('payment_photographer')['profile']['user']['username']
        payment_photographer=Photographer.objects.get(profile__user__username=payment_photographer_username)

        payments = Payment.objects.create(payment_status=validated_data.pop('payment_status'),
                                        payment_customer=payment_customer, 
                                        payment_photographer=payment_photographer, 
                                        payment_job=validated_data.pop('payment_job'), 
                                        payment_amount=validated_data.pop('payment_amount'))
        payments.save()
        return payments
    
    def update(self, instance, validated_data) :
        if validated_data['payment_status'] == "DEPOSIT" :
            instance.update(job_status="PAID")
        elif validated_data['payment_status'] == "REMAINING" :
            instance.update(job_status="CLOSED")


class GetFavPhotographersSerializer(serializers.ModelSerializer):
    # profile = ProfileSerializer(required=True, partial=True)
    fav_photographers = PhotographerSerializer(required=True, partial=True,many = True)

    class Meta:
        model = Customer
        fields = '__all__'


class GetPaymentToPhotographerSerializer(serializers.ModelSerializer):
    payment_job = JobSerializer(required=True, partial=True)

    class Meta:
        model = Payment
        fields = '__all__'

class GetPaymentToCustomerSerializer(serializers.ModelSerializer):
    payment_job = JobSerializer(required=True, partial=True)

    class Meta:
        model = Payment
        fields = '__all__'







