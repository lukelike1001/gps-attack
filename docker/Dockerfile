# syntax=docker/dockerfile:1
# ─────────────────────────────────────────────────────────────────────────────
# Stage 1: ardupilot-builder
#
# Clones ArduPilot at the requested branch, installs the full build toolchain
# via the upstream install-prereqs-ubuntu.sh script, and compiles the
# ArduCopter SITL binary. The toolchain is discarded in stage 2.
# ─────────────────────────────────────────────────────────────────────────────
FROM ubuntu:22.04 AS ardupilot-builder

ARG ARDUPILOT_CLONE_BRANCH=Copter-4.6.3
ARG ARDUPILOT_BUILD_USER=ardupilot
ARG ARDUPILOT_BUILD_UID=1000
ARG ARDUPILOT_BUILD_GID=1000
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install --no-install-recommends -y \
        git \
        lsb-release \
        sudo \
        tzdata \
        bash-completion \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid ${ARDUPILOT_BUILD_GID} ${ARDUPILOT_BUILD_USER} \
    && useradd -m -u ${ARDUPILOT_BUILD_UID} -g ${ARDUPILOT_BUILD_GID} -s /bin/bash ${ARDUPILOT_BUILD_USER} \
    && echo "${ARDUPILOT_BUILD_USER} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/${ARDUPILOT_BUILD_USER} \
    && chmod 0440 /etc/sudoers.d/${ARDUPILOT_BUILD_USER} \
    && mkdir /ardupilot \
    && chown ${ARDUPILOT_BUILD_USER}:${ARDUPILOT_BUILD_USER} /ardupilot

USER ${ARDUPILOT_BUILD_USER}
WORKDIR /home/${ARDUPILOT_BUILD_USER}

RUN git clone \
        --branch ${ARDUPILOT_CLONE_BRANCH} \
        --depth 1 \
        --recurse-submodules \
        --shallow-submodules \
        https://github.com/ArduPilot/ardupilot.git \
        /ardupilot

WORKDIR /ardupilot

RUN SKIP_AP_EXT_ENV=1 \
    SKIP_AP_GRAPHIC_ENV=1 \
    SKIP_AP_COV_ENV=1 \
    SKIP_AP_GIT_CHECK=1 \
    DO_AP_STM_ENV=0 \
    AP_DOCKER_BUILD=1 \
    USER=${ARDUPILOT_BUILD_USER} \
    Tools/environment_install/install-prereqs-ubuntu.sh -y

RUN git config --global --add safe.directory /ardupilot

RUN echo 'if [ -d "$HOME/.local/bin" ]; then PATH="$HOME/.local/bin:$PATH"; fi' \
        >> /home/${ARDUPILOT_BUILD_USER}/.ardupilot_env

RUN . /home/${ARDUPILOT_BUILD_USER}/.ardupilot_env \
    && ./waf configure --board sitl \
    && ./waf build --target bin/arducopter


# ─────────────────────────────────────────────────────────────────────────────
# Stage 2: gps-attack-runtime
#
# Minimal Ubuntu 22.04 image. Receives only the compiled SITL binary and the
# sim_vehicle.py toolchain from stage 1. Installs Python project dependencies
# from requirements.txt and copies in the gps-attack project files.
# ─────────────────────────────────────────────────────────────────────────────
FROM ubuntu:22.04 AS gps-attack-runtime

ARG ARDUPILOT_BUILD_USER=ardupilot
ARG ARDUPILOT_BUILD_UID=1000
ARG ARDUPILOT_BUILD_GID=1000
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install --no-install-recommends -y \
        python3 \
        python3-pip \
        python3-dev \
        python-is-python3 \
        sudo \
        tzdata \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid ${ARDUPILOT_BUILD_GID} ${ARDUPILOT_BUILD_USER} \
    && useradd -m -u ${ARDUPILOT_BUILD_UID} -g ${ARDUPILOT_BUILD_GID} -s /bin/bash ${ARDUPILOT_BUILD_USER} \
    && echo "${ARDUPILOT_BUILD_USER} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/${ARDUPILOT_BUILD_USER} \
    && chmod 0440 /etc/sudoers.d/${ARDUPILOT_BUILD_USER}

COPY --from=ardupilot-builder \
     /home/${ARDUPILOT_BUILD_USER}/.ardupilot_env \
     /home/${ARDUPILOT_BUILD_USER}/.ardupilot_env

COPY --from=ardupilot-builder /ardupilot/build/sitl/bin/arducopter \
     /ardupilot/build/sitl/bin/arducopter

COPY --from=ardupilot-builder /ardupilot/Tools/autotest/sim_vehicle.py \
     /ardupilot/Tools/autotest/sim_vehicle.py

COPY --from=ardupilot-builder /ardupilot/Tools/autotest/pysim \
     /ardupilot/Tools/autotest/pysim

COPY --from=ardupilot-builder \
     /home/${ARDUPILOT_BUILD_USER}/.local \
     /home/${ARDUPILOT_BUILD_USER}/.local

RUN chown -R ${ARDUPILOT_BUILD_USER}:${ARDUPILOT_BUILD_USER} \
        /ardupilot \
        /home/${ARDUPILOT_BUILD_USER}

COPY requirements.txt /gps-attack/requirements.txt
RUN pip3 install --no-cache-dir -r /gps-attack/requirements.txt

COPY sim/     /gps-attack/sim/
COPY attack/  /gps-attack/attack/
COPY analysis/ /gps-attack/analysis/

RUN mkdir -p /gps-attack/logs \
    && chown -R ${ARDUPILOT_BUILD_USER}:${ARDUPILOT_BUILD_USER} /gps-attack

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER ${ARDUPILOT_BUILD_USER}
WORKDIR /gps-attack

ENTRYPOINT ["/entrypoint.sh"]
