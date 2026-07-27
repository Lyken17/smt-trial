FROM satcomp-infrastructure

USER root
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        build-essential \
        ca-certificates \
        cmake \
        git \
        m4 \
        ninja-build \
        python3 \
    && rm -rf /var/lib/apt/lists/*

ARG CVC5_REPOSITORY=https://github.com/cvc5/cvc5.git
ARG CVC5_REV=6f2bc560651b6b739de93519f5cc815c182a0027
RUN git clone --filter=blob:none --no-checkout "${CVC5_REPOSITORY}" /src/cvc5 \
    && git -C /src/cvc5 fetch --depth 1 origin "${CVC5_REV}" \
    && git -C /src/cvc5 checkout --detach "${CVC5_REV}" \
    && test "$(git -C /src/cvc5 rev-parse HEAD)" = "${CVC5_REV}"

WORKDIR /src/cvc5
RUN ./configure.sh competition \
        --auto-download \
        --ninja \
        --static \
        --prefix=/opt/cvc5 \
    && cmake --build build --parallel "$(nproc)" --target cvc5-bin \
    && cmake --install build --strip \
    && /opt/cvc5/bin/cvc5 --version

WORKDIR /
COPY cvc5_cloud /opt/cvc5-cloud/cvc5_cloud
COPY aws-build/solver_cmd.py /opt/amazon/scripting/harness/entrypoints/solver_cmd.py

RUN chown -R ecs-user:ecs-user /opt/cvc5-cloud /opt/cvc5
USER ecs-user
