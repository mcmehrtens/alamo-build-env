##########
# PARSER #
##########

FROM python:3.10-slim AS parser

# install yaml parsing dependency
RUN pip install --root-user-action ignore --upgrade pip \
    && pip install --root-user-action ignore ruamel.yaml

# configure working dir
WORKDIR /build

# copy scripts and configs
COPY platforms/ubuntu-24.04/config.yaml .
COPY scripts scripts
RUN chmod +x scripts/*

# parse the config.yaml
RUN scripts/parse-config.py config.yaml config.json 

###############
# BUILD_AMREX #
###############

FROM ubuntu:24.04 AS build_amrex

ARG CONFIG="/tmp/config.json"

COPY --from=parser /build/config.json "$CONFIG"

RUN apt-get update \
    && apt-get install -y jq \
    && apt-get install -y $(jq -r '.system_packages | join(" ")' "$CONFIG") \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
RUN git clone $(jq -r '.git.repository' "$CONFIG") . \
    && git checkout $(jq -r '.git.branch' "$CONFIG") 
