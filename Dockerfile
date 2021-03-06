FROM ubuntu:16.04

RUN apt-get update && \
    apt-get install -y \
      python3 python3-pip python3-pil \
      build-essential libboost-all-dev \
      clang pkg-config && \
    python3 -m pip install jupyter

RUN mkdir /python-modules
ADD fakerepl_kernel /python-modules/fakerepl_kernel
COPY start-console.sh /usr/bin/start-console.sh
COPY start-notebook.sh /usr/bin/start-notebook.sh
RUN chmod +x /usr/bin/start-console.sh && \
    chmod +x /usr/bin/start-notebook.sh

ENV USER darklord
RUN useradd -ms /bin/bash $USER
ENV HOME /home/$USER
env PYTHONPATH /python-modules
USER $USER
WORKDIR /home/$USER
RUN python3 /python-modules/fakerepl_kernel/install.py

CMD ["start-console.sh"]
