from rest_framework.decorators import action
from rest_framework import status, viewsets, filters, mixins, pagination
from rest_framework.response import Response
from .permissions import IsUser
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q, Avg, Case, IntegerField, Value, When, Sum
from django.http import HttpResponseBadRequest
import datetime
import os
import omise

# Import Serializers of apps
from .serializers import PhotographerSerializer, CustomerSerializer, JobSerializer, JobReservationSerializer, UserSerializer, \
    PhotoSerializer, AvailTimeSerializer, EquipmentSerializer, ProfileSerializer, StyleSerializer, NotificationSerializer, ChangePasswordSerializer, \
    ReviewSerializer, PaymentSerializer, GetJobsSerializer, GetPaymentToPhotographerSerializer, GetPaymentToCustomerSerializer, GetFavPhotographersSerializer,\
    UserSerializer
# Import models of apps for queryset
from photographers.models import Photographer, Photo, AvailTime, Equipment, Style
from customers.models import Customer
from jobs.models import JobInfo, JobReservation
from users.models import CustomUser, CustomUserProfile
from notification.models import Notification
from reviews.models import ReviewInfo
from payments.models import Payment


class PhotographerViewSet(viewsets.ModelViewSet):
    serializer_class = PhotographerSerializer
    queryset = Photographer.objects.all()
    # permission_classes = [AllowAny]
    lookup_field = 'profile__user__username'
    filter_backends = [filters.SearchFilter]
    search_fields = ['profile__user__username',"profile__user__first_name","profile__user__last_name"]


class PhotoViewSet(viewsets.ModelViewSet):
    serializer_class = PhotoSerializer
    queryset = Photo.objects.all()


class AvailTimeViewSet(viewsets.ModelViewSet):
    serializer_class = AvailTimeSerializer
    queryset = AvailTime.objects.all()


class StyleViewSet(viewsets.ModelViewSet):
    serializer_class = StyleSerializer
    queryset = Style.objects.all()

class PhotographerSearchPagination(pagination.PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'

class PhotographerSearchViewSet(viewsets.ModelViewSet) :
    serializer_class = PhotographerSerializer
    pagination_class = PhotographerSearchPagination
    def get_queryset(self):
        #Filter name
        user = self.request.query_params.get('user')
        if user is not None :
            nameset = Photographer.objects.filter(Q(profile__user__username__icontains=user)|Q(profile__user__first_name__icontains=user)|Q(profile__user__last_name__icontains=user))
        else : nameset = Photographer.objects.all()

        #Filter other parameters
        style = self.request.query_params.get('style')
        time = self.request.query_params.get('time')
        metafil = {'photographer_style__style_name': style, 'photographer_avail_time__avail_time': time}
        filters = {k: v for k, v in metafil.items() if v is not None}
        paraset = nameset.filter(**filters)

        #Filter Date (allphotographer - photographerwithjobs)
        date = self.request.query_params.get('date')
        if date is not None :
            #Filter Photographer by date
            day, month, year = (int(x) for x in date.split('_')) 
            sel_date = (datetime.date(year, month, day)).strftime('%A')
            dateset = paraset.filter(photographer_avail_time__avail_date = sel_date)
            #Filter out reserved photographer
            compdate = "-".join(date.split("_")[::-1])
            jobset = JobInfo.objects.filter(job_reservation__photoshoot_date = compdate).values_list('job_photographer_id', flat=True)
            toremove = []
            for cid in jobset :
                if dateset.filter(profile__user__id=cid) is not None:
                    toremove.append(cid)
            queryset = dateset.filter(~Q(profile__user__id__in=toremove))
        else : queryset = paraset
        
        #Sort
        sort = self.request.query_params.get('sort')
        if sort == "time_des" :
            return queryset.order_by("-photographer_last_online_time")
        elif sort == "time_asc" :
            return queryset.order_by("photographer_last_online_time")
        elif sort == "price_des" :
            return queryset.annotate(price=Avg('photographer_avail_time__photographer_price')).order_by('-price')
        elif sort == "price_asc" :
            return queryset.annotate(price=Avg('photographer_avail_time__photographer_price')).order_by('price')
        elif sort == "review_des":
            counts = dict()
            jobidlist = ReviewInfo.objects.values_list('reviewJob', flat=True)
            for i in jobidlist :
                pid = JobInfo.objects.filter(job_id=i).values_list('job_photographer_id', flat=True)
                counts[pid[0]] = counts.get(pid[0], 0) + 1
            return queryset.annotate(
                            score=Case(
                            *[When(profile__user__id=k, then=Value(v)) for k,v in counts.items()],
                            default=None,
                            output_field=IntegerField(null=True)
                            )).order_by('-score')
        elif sort == "review_asc" :
            counts = dict()
            jobidlist = ReviewInfo.objects.values_list('reviewJob', flat=True)
            for i in jobidlist :
                pid = JobInfo.objects.filter(job_id=i).values_list('job_photographer_id', flat=True)
                counts[pid[0]] = counts.get(pid[0], 0) + 1
            return queryset.annotate(
                            score=Case(
                            *[When(profile__user__id=k, then=Value(v)) for k,v in counts.items()],
                            default=None,
                            output_field=IntegerField(null=True)
                            )).order_by('score')
        return queryset


class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    queryset = Payment.objects.all()
    # permission_classes = [AllowAny]
    def create(self, request, *args, **kwargs):
        data = {}
        jid = request.data['job_id']
        cardtoken = request.data['omiseToken']

        #Create object
        if not JobInfo.objects.filter(job_id=jid).exists() :
            return Response(data="Job ID is invalid.")
        job = JobInfo.objects.filter(job_id=jid)
        data['payment_customer'] = job.values_list('job_customer__profile__user__username', flat=True)[0]
        data['payment_photographer'] = job.values_list('job_photographer__profile__user__username', flat=True)[0]
        data['payment_job'] = jid
        amount = job.annotate(job_total_price=Sum('job_reservation__job_avail_time__photographer_price')).values_list('job_total_price', flat=True)[0]
        job_status = job.values_list('job_status', flat=True)[0]
        if job_status == "MATCHED" :
            amount = amount * 0.3
            data['payment_amount'] = amount
            data['payment_status'] = "DEPOSIT"
        elif job_status == "COMPLETED" :
            amount = amount * 0.7
            data['payment_amount'] = amount
            data['payment_status'] = "REMAINING"
        else :
            return Response(data="Job Status is invalid.")
        
        #Omise Payment
        path = os.path.dirname(os.path.abspath(__file__))
        tokenfile = os.path.join(path, 'token.txt')
        with open(tokenfile, "r") as f :
            token = f.read()
        if not token : return Response(data="Server Token Error")
        omise.api_secret = token
        try :
            charge = omise.Charge.create(amount=int(amount)*100, currency="thb", card=cardtoken)
        except Exception as e :
            return HttpResponseBadRequest(str(e))

        #Update Job Status
        PaymentSerializer.update(self, job, validated_data=data)

        #Create Payment Object
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        return Response(data="Payment Successful.")

class GetPaymentToPhotographerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = GetPaymentToPhotographerSerializer

    def get_queryset(self):
        return Payment.objects.exclude(payment_job__job_status="CANCELLED_BY_PHOTOGRAPHER")

class GetPaymentToCustomerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = GetPaymentToCustomerSerializer

    def get_queryset(self):
        return Payment.objects.filter(payment_job__job_status="CANCELLED_BY_PHOTOGRAPHER")

class EquipmentViewSet(viewsets.ModelViewSet):
    serializer_class = EquipmentSerializer
    queryset = Equipment.objects.all()


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    # permission_classes = [AllowAny]
    lookup_field = 'profile__user__username'
    filter_backends = [filters.SearchFilter]
    search_fields = ['profile__user__username']


class JobsViewSet(viewsets.ModelViewSet):
    queryset = JobInfo.objects.all()
    serializer_class = JobSerializer
    # permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter]
    search_fields = ['job_photographer__profile__user__username','job_customer__profile__user__username']

    def get_queryset(self):
        return JobInfo.objects.annotate(
            job_total_price=Sum('job_reservation__job_avail_time__photographer_price')
        )

class GetjobsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = JobInfo.objects.all()
    serializer_class = GetJobsSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['job_photographer__profile__user__username','job_customer__profile__user__username'] 

    def get_queryset(self):
        return JobInfo.objects.annotate(
            job_total_price=Sum('job_reservation__job_avail_time__photographer_price')
        )    

class JobReservationViewSet(viewsets.ModelViewSet):
    queryset = JobReservation.objects.all()
    serializer_class = JobReservationSerializer
    # permission_classes = [AllowAny]


class UserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    # permission_classes = [AllowAny]
    lookup_field = 'username'
    filter_backends = [filters.SearchFilter]
    search_fields = ['username']    

class ChangePasswordViewSet(mixins.UpdateModelMixin,viewsets.GenericViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = ChangePasswordSerializer
    # permission_classes = [AllowAny]
    lookup_field = 'username'   

class RegisterViewSet(mixins.CreateModelMixin,viewsets.GenericViewSet):
    permission_classes = [AllowAny]
    serializer_class = ProfileSerializer

    def create(self, request, *args, **kwargs):
        user_type = request.data['profile']['user']['user_type']
        username = request.data['profile']['user']['username']
        message = 'Hello '+username+'! Your registeration is successful.'
        if user_type == 1: # photographer
            user = PhotographerSerializer.create(PhotographerSerializer(), validated_data=request.data)
        elif user_type == 2: # customer
            user = CustomerSerializer.create(CustomerSerializer(), validated_data=request.data)
        return Response(data={'message': message})

class ProfileViewSet(viewsets.ModelViewSet):
    queryset = CustomUserProfile.objects.all()
    serializer_class = ProfileSerializer
    # permission_classes = [AllowAny]
    lookup_field = 'user__username'
    filter_backends = [filters.SearchFilter]
    search_fields = ['user__username']

class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    queryset = Notification.objects.all()
    # permission_classes = [AllowAny]
    lookup_field = 'noti_id'
    filter_backends = [filters.SearchFilter]
    search_fields = ['noti_receiver__user__username']

class ReviewViewSet(viewsets.ModelViewSet):
    queryset = ReviewInfo.objects.filter()
    serializer_class = ReviewSerializer
    permission_classes = [AllowAny]
    lookup_field = 'reviewJob__job_id'
    filter_backends = [filters.SearchFilter]
    search_fields = ['reviewJob__job_photographer__profile__user__username','reviewJob__job_customer__profile__user__username']

class GetFavPhotographersViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = GetFavPhotographersSerializer
    lookup_field = 'profile__user__username'
    # filter_backends = [filters.SearchFilter]
    # search_fields = ['profile_id__profile__user__username']