FROM ubuntu:20.04

RUN apt-get update && apt-get -y install xinetd && apt-get -y install gdbserver

RUN useradd -M jqr

WORKDIR /jqr

COPY xinetd.conf /etc/xinetd.d/jqr
COPY banner_fail ./
COPY flag.txt ./
COPY challenge.sh ./

COPY start.sh ./
RUN chmod +x ./start.sh

COPY chal ./
RUN chmod +x ./chal

EXPOSE 1337

CMD ["/jqr/start.sh"]