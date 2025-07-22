# Multi-stage build for optimized image size and caching
FROM python:3.11-slim-bookworm AS base

# Install system dependencies and security tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Basic utilities
    curl \
    wget \
    git \
    gcc \
    g++ \
    make \
    # Security tools
    nmap \
    hydra \
    smbclient \
    openssl \
    # Additional dependencies for enum4linux-ng
    python3-ldap3 \
    python3-yaml \
    python3-impacket \
    # Dependencies for nikto
    perl \
    libnet-ssleay-perl \
    # Dependencies for searchsploit
    jq \
    # Clean up
    && rm -rf /var/lib/apt/lists/*

# Install nikto from GitHub
RUN git clone https://github.com/sullo/nikto.git /opt/nikto \
    && chmod +x /opt/nikto/program/nikto.pl \
    && ln -s /opt/nikto/program/nikto.pl /usr/local/bin/nikto

# Install enum4linux-ng from GitHub (not in apt repos)
RUN git clone https://github.com/cddmp/enum4linux-ng.git /opt/enum4linux-ng \
    && chmod +x /opt/enum4linux-ng/enum4linux-ng.py \
    && ln -s /opt/enum4linux-ng/enum4linux-ng.py /usr/local/bin/enum4linux-ng

# Install ffuf (with architecture detection)
RUN ARCH=$(dpkg --print-architecture) && \
    if [ "$ARCH" = "amd64" ]; then FFUF_ARCH="amd64"; \
    elif [ "$ARCH" = "arm64" ]; then FFUF_ARCH="arm64"; \
    else echo "Unsupported architecture: $ARCH" && exit 1; fi && \
    curl -L "https://github.com/ffuf/ffuf/releases/download/v2.1.0/ffuf_2.1.0_linux_${FFUF_ARCH}.tar.gz" | tar xz -C /usr/local/bin/

# Install searchsploit (exploitdb) - optional, continue on failure
RUN git clone --depth 1 https://github.com/offensive-security/exploitdb.git /opt/exploitdb && \
    ln -s /opt/exploitdb/searchsploit /usr/local/bin/searchsploit && \
    chmod +x /opt/exploitdb/searchsploit || \
    echo "WARNING: Failed to install searchsploit, continuing without it"

# Install SecLists wordlists - optional, continue on failure
RUN git clone --depth 1 https://github.com/danielmiessler/SecLists.git /usr/share/wordlists/seclists || \
    echo "WARNING: Failed to install SecLists, continuing without it"

# Install Poetry
ENV POETRY_HOME=/opt/poetry \
    POETRY_VERSION=1.7.1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1 \
    PATH="/opt/poetry/bin:$PATH"

RUN curl -sSL https://install.python-poetry.org | python3 - \
    && poetry --version

# Create non-root user
RUN groupadd -g 1000 alienrecon \
    && useradd -u 1000 -g alienrecon -s /bin/bash -m alienrecon \
    && mkdir -p /home/alienrecon/.cache \
    && chown -R alienrecon:alienrecon /home/alienrecon

# Set working directory
WORKDIR /app

# Copy dependency files first for better caching
COPY --chown=alienrecon:alienrecon pyproject.toml poetry.lock ./

# Install Python dependencies
RUN poetry install --no-root --no-dev

# Copy source code
COPY --chown=alienrecon:alienrecon src/ ./src/
COPY --chown=alienrecon:alienrecon README.md ./

# Install the application
RUN poetry install --only-root

# Create directories for data persistence
RUN mkdir -p /data/sessions /data/cache /data/missions \
    && chown -R alienrecon:alienrecon /data

# Configure searchsploit for the alienrecon user (if installed)
RUN if [ -f /opt/exploitdb/.searchsploit_rc ]; then \
        cp /opt/exploitdb/.searchsploit_rc /home/alienrecon/.searchsploit_rc && \
        sed -i 's|/opt/exploitdb|/opt/exploitdb|g' /home/alienrecon/.searchsploit_rc && \
        chown alienrecon:alienrecon /home/alienrecon/.searchsploit_rc; \
    fi

# Switch to non-root user
USER alienrecon

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    ALIENRECON_DATA_DIR=/data \
    ALIENRECON_CACHE_DIR=/data/cache \
    ALIENRECON_SESSIONS_DIR=/data/sessions \
    ALIENRECON_MISSIONS_DIR=/data/missions

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD alienrecon doctor || exit 1

# Default command
CMD ["alienrecon", "--help"]
