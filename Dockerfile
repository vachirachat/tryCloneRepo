FROM python:3.6
ENV PYTHONUNBUFFERED 1
RUN mkdir -p /usr/src/romeo-back
WORKDIR /usr/src/romeo-back
ADD requirements.txt /usr/src/romeo-back/
RUN pip install --upgrade pip && pip install -r requirements.txt
ADD . /usr/src/romeo-back/