#################
# CONFIG PARSER #
#################

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

######################
# BUILD DEPENDENCIES #
######################

FROM ubuntu:24.04

ARG CONFIG="/tmp/config.json"
ARG EXT_DEP_ROOT="/ext"
ARG AMREX_INSTALL_ROOT="${EXT_DEP_ROOT}/amrex"

COPY --from=parser /build/config.json "$CONFIG"

RUN apt-get update \
    && apt-get install -y jq \
    && apt-get install -y $(jq -r '.system_packages | join(" ")' "$CONFIG") \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
RUN git clone $(jq -r '.git.repository' "$CONFIG") . \
    && git checkout $(jq -r '.git.branch' "$CONFIG")

# Build AMReX
# -----------
RUN \
    mkdir -p "${AMREX_INSTALL_ROOT}"; \
    # get path to AMReX checkout
    amrex_checkout_dir=$(jq -r '.amrex_build_config.amrex_dir' "$CONFIG"); \
    # get base configuration command and do a configure to checkout AMReX
    base_configure_cmd=$(jq -r '.amrex_build_config.configure_cmd' "$CONFIG"); \
    "$base_configure_cmd"; \
    # get AMReX version
    amrex_version=$(git -C "$amrex_checkout_dir" describe --always --dirty); \
    # parse and loop over configuration commands
    jq -c '.configure_commands[]' "$CONFIG" | \
    while read -r target_dict; do \
        # get target and args for this configuration command
        target="$(echo $target_dict | jq -r '.target')-$amrex_version"; \
        args=$(echo $target_dict | jq -r '.configure_cmd | join(" ")'); \
        echo "Configuring and building AMReX ($target) with: $base_configure_cmd $args"; \
        # configure and make
        "$base_configure_cmd" $args && \
        make -j$(nproc) "$target" && \
        # move to installation dir
        mv "$target" "${AMREX_INSTALL_ROOT}" && \
        # cleanup for next build
        make realclean; \
    done

# Clean Up Build
# --------------
WORKDIR /app
RUN rm -rf /build
