FROM ubuntu:20.04

ARG DIR=/opt

WORKDIR $DIR

ENV TZ 'Europe/Berlin'

# timezone stuff (https://dawnbringer.net/blog/600/Docker:%20tzdata)
RUN echo $TZ > /etc/timezone && \
    apt update -y && apt install -y tzdata && \
    rm /etc/localtime && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata

# apt packages
RUN apt update -y && apt install -y \
      vim \
      git \
      gcc \
      make \
      unzip \
      wget \
      libblkid-dev \
      libncurses5 \
      python \
      virtualenv \
      tar && \
      apt-get clean

# Get Android platform tools
RUN mkdir Android
RUN wget https://dl.google.com/android/repository/platform-tools-latest-linux.zip
RUN unzip platform-tools-latest-linux.zip -d ./Android/
ENV PATH=$DIR/Android/platform-tools:$PATH

# setup NDK
WORKDIR $DIR/Android
RUN wget https://dl.google.com/android/repository/android-ndk-r15c-linux-x86_64.zip && \
	unzip android-ndk-r15c-linux-x86_64.zip
ENV PATH=$DIR/Android/android-ndk-r15c:$PATH

# setup venv and install requirements.txt
WORKDIR /root
RUN --mount=type=bind,source=./requirements.txt,target=/src/requirements.txt \
    virtualenv -p python3 .venv && \
    . .venv/bin/activate && \
    pip install -r /src/requirements.txt

WORKDIR /root
