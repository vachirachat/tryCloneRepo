# REQUIRED
in your virtual environment, run the following commands

python -m pip install Django
pip install djangorestframework
pip install mysqlclient
pip install djoser
pip install djangorestframework-simplejwt
pip install django-filter
pip install django-cors-headers
pip install drf-writable-nested
pip install omise

## Prerequisites for mysqlclient
You may need to install the Python and MySQL development headers and libraries like so:
sudo apt-get install python-dev default-libmysqlclient-dev # Debian / Ubuntu
sudo yum install python-devel mysql-devel # Red Hat / CentOS
brew install mysql-client # macOS (Homebrew)

On Windows, there are binary wheels you can install without MySQLConnector/C or MSVC.

Note on Python 3 : if you are using python3 then you need to install python3-dev using the following command :
sudo apt-get install python3-dev # debian / Ubuntu
sudo yum install python3-devel # Red Hat / CentOS

## How to sync Database
After creating a new local instance connection in my sqlclient
In config/settings.py, change database settings (user and password) to correspond to your mysql local instance and run
python manage.py makemigrations
python manage.py migrate

## To create superuser that can login to localhost/admin
python manage.py createsuperuser
