#################
# CONFIG PARSER #
#################

FROM python:3.10-slim AS parser

# args from workflow
ARG AMREX_VERSION
ARG DIMENSION
ARG COMPILER
ARG DEBUG
ARG PROFILE
ARG COVERAGE
ARG MEMCHECK

# config locations
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
    && scripts/parse-config.py ${INPUT_CONFIG} ${OUTPUT_CONFIG} ${AMREX_VERSION} ${DIMENSION} ${COMPILER} ${DEBUG} ${PROFILE} ${COVERAGE} ${MEMCHECK}

######################
# BUILD DEPENDENCIES #
######################

FROM ubuntu:24.04 AS build_deps

ARG PARSED_CONFIG="/tmp/config.json"
ARG CONFIG=${PARSED_CONFIG}
ARG EXT_DEP_ROOT="/ext"
ARG AMREX_INSTALL_ROOT="${EXT_DEP_ROOT}/amrex"

COPY --from=parser ${PARSED_CONFIG} ${CONFIG}

RUN apt-get update \
    && apt-get install -y --no-install-recommends jq \
    && apt-get install -y --no-install-recommends $(jq -r '.system_packages | join(" ")' ${CONFIG}) \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# -----------
# Build AMReX
# -----------
RUN git clone $(jq -r '.git.repository' ${CONFIG}) . \
    && git checkout $(jq -r '.git.branch' ${CONFIG})

RUN mkdir -p ${AMREX_INSTALL_ROOT} \
    && configure_cmd=$(jq -r '.configure_cmd | join(" ")' ${CONFIG}) \
    && make_target=$(jq -r '.make_target' ${CONFIG}) \
    && $configure_cmd \
    && make -j$(nproc) $make_target \
    && mv $make_target/* ${AMREX_INSTALL_ROOT}

# --------
# Clean Up
# --------

WORKDIR /app

RUN rm -rf /build

RUN useradd -m -s /bin/bash alamo
USER alamo
CMD ["bash"]

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD if [ -d "${AMREX_INSTALL_ROOT}" ] && [ -n "$(ls -A ${AMREX_INSTALL_ROOT})" ]; then \
            echo "AMReX installation verified."; \
            exit 0; \
        else \
            echo "AMReX installation not found or empty."; \
            exit 1; \
        fi
