FROM python:3.13-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:0.7.14 /uv /uvx /bin/

# Install uv
# The installer requires curl (and certificates) to download the release archive
RUN apt-get update \
	&& apt-get install -y --no-install-recommends build-essential curl ca-certificates \
	&& rm -rf /var/lib/apt/lists/* /usr/share/doc /usr/share/man \
	&& apt-get clean

ADD https://astral.sh/uv/0.7.14/install.sh /uv-installer.sh

RUN sh /uv-installer.sh && rm /uv-installer.sh

# Ensure the installed binary is on the `PATH`
ENV PATH="/root/.local/bin/:$PATH"

# Install the project
# Copy the project into the image
ADD crdtsign/core/. /app

# Sync the project into a new environment, asserting the lockfile is up to date
WORKDIR /app
RUN uv sync --locked

# The web application is deployed on port 5000
EXPOSE 5000

# The server runs on port 8765
EXPOSE 8765

# Run the project [default: server]
CMD [ "uv", "run", "crdtsign", "server", "--host", "0.0.0.0", "--port", "8765" ]
