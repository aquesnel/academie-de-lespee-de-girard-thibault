# Base Image
FROM debian:bookworm-20250224-slim

ENV LD_LIBRARY_PATH=/usr/local/cuda-12.8/lib64
WORKDIR /tmp
RUN apt-get update \
	&& apt-get install -y wget \
	&& wget https://developer.download.nvidia.com/compute/cuda/repos/wsl-ubuntu/x86_64/cuda-keyring_1.1-1_all.deb \
    && dpkg -i cuda-keyring_1.1-1_all.deb \
    && apt-get update \
    && apt-get -y install cuda-toolkit-12-8 python3 python3-pip \
	&& pip3 install --break-system-packages --extra-index-url https://download.pytorch.org/whl/ kraken==5.3.0 torch==2.4.0+cu121 torchvision==0.19.0+cu121 torchaudio==2.4.0+cu121
