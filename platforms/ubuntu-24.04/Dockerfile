#################
# CONFIG PARSER #
#################

FROM python:3.10-slim AS parser

ARG INPUT_CONFIG="/tmp/config.yaml"
ARG OUTPUT_CONFIG="/tmp/config.json"

# configure working dir
WORKDIR /build

# copy scripts and configs
COPY platforms/ubuntu-24.04/config.yaml ${INPUT_CONFIG}
COPY scripts scripts
COPY pyproject.toml pyproject.toml

# install deps and parse config
RUN pip install --root-user-action ignore --upgrade pip \
    && pip install --root-user-action ignore .[container] \
    && chmod +x scripts/* \
    && scripts/parse-config.py ${INPUT_CONFIG} ${OUTPUT_CONFIG}

######################
# BUILD DEPENDENCIES #
######################

FROM ubuntu:24.04 AS build_deps

ARG OUTPUT_CONFIG="/tmp/config.json"
ARG CONFIG=${OUTPUT_CONFIG}
ARG EXT_DEP_ROOT="/ext"
ARG AMREX_INSTALL_ROOT="${EXT_DEP_ROOT}/amrex"

COPY --from=parser ${OUTPUT_CONFIG} ${CONFIG}

RUN apt-get update \
    && apt-get install -y --no-install-recommends jq \
    && apt-get install -y --no-install-recommends $(jq -r '.system_packages | join(" ")' ${CONFIG}) \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Build AMReX
# -----------
RUN git clone $(jq -r '.git.repository' ${CONFIG}) . \
    && git checkout $(jq -r '.git.branch' ${CONFIG})

RUN mkdir -p ${AMREX_INSTALL_ROOT} \
    && amrex_checkout_dir=$(jq -r '.amrex_build_config.amrex_dir' ${CONFIG}) \
    && base_configure_cmd=$(jq -r '.amrex_build_config.configure_cmd' ${CONFIG}) \
    && "$base_configure_cmd" \
    && amrex_version=$(git -C "$amrex_checkout_dir" describe --always --dirty) \
    && jq -c '.configure_commands[]' ${CONFIG} | \
    while read -r target_dict; do \
        target="$(echo $target_dict | jq -r '.target')-$amrex_version"; \
        args=$(echo $target_dict | jq -r '.configure_cmd | join(" ")'); \
        echo "Configuring and building AMReX ($target) with: $base_configure_cmd $args" \
        && "$base_configure_cmd" $args \
        && make -j$(nproc) "$target" \
        && mv "$target" ${AMREX_INSTALL_ROOT} \
        && make realclean; \
    done

#################
# RUNTIME IMAGE #
#################

FROM ubuntu:24.04

ARG OUTPUT_CONFIG="/tmp/config.json"
ARG CONFIG=${OUTPUT_CONFIG}
ARG EXT_DEP_ROOT="/ext"
ARG AMREX_INSTALL_ROOT="${EXT_DEP_ROOT}/amrex"

COPY --from=build_deps ${OUTPUT_CONFIG} ${CONFIG}
COPY --from=build_deps ${AMREX_INSTALL_ROOT} ${AMREX_INSTALL_ROOT}

ENV AMREX_INSTALL_ROOT=${AMREX_INSTALL_ROOT}

RUN apt-get update \
    && apt-get install -y --no-install-recommends jq \
    && apt-get install -y --no-install-recommends $(jq -r '.system_packages | join(" ")' ${CONFIG}) \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r alamo && useradd -r -g alamo alamo \
    && mkdir -p /app \
    && chown -R alamo:alamo /app

WORKDIR /app

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD if [ -d "${AMREX_INSTALL_ROOT}" ] && [ -n "$(ls -A ${AMREX_INSTALL_ROOT})" ]; then \
            echo "AMReX installation verified."; \
            exit 0; \
        else \
            echo "AMReX installation not found or empty."; \
            exit 1; \
        fi

USER alamo

CMD ["bash"]
