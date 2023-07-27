FROM ubuntu:23.10
LABEL owner="zerebecki@student.agh.edu.pl"
LABEL maintainer="zerebecki@student.agh.edu.pl"

WORKDIR /backend

RUN apt-get update &&\
    apt-get install -y net-tools iputils-ping iproute2 python3.11 pip vim tcpdump libpcap-dev telnet openssh-client

COPY ../ .
