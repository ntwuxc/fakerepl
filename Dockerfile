FROM ubuntu:16.04

RUN apt-get update && \
    apt-get install -y \
      python3 python3-pip \
      build-essential libboost-all-dev && \
    python3 -m pip install jupyter

