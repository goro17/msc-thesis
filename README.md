# CRDTSign

### Requirements
- Python 3.11+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

## Usage
1. Clone the repository.
```bash
git clone https://github.com/goro17/msc-thesis.git
```
2. Point to the package directory.
```bash
cd crdtsign
```
1. Install the package dependencies and run the server.
```bash
uv sync --locked
uv run crdtsign-app
```
1. Access the web interface through the browser at the desired host+port (default: [127.0.0.1:5000](http://127.0.0.1:5000/)).

## Docker
#### Requirements

- [Docker](https://www.docker.com/)
- [Docker Compose](https://docs.docker.com/compose/)

### Build Instructions
1. Clone the repository.
```bash
git clone https://github.com/goro17/msc-thesis.git
```

2. Build the Docker image and deploy the corresponding container using `docker-compose`.
```bash
docker-compose up --build -d
```

3. Access the web interface through the browser at the desired host+port (default: [127.0.0.1:5001](http://127.0.0.1:5001/)).

> For the sake of demonstration, two additional clients can be accessed at [127.0.0.1:5002](http://127.0.0.1:5002/) and [127.0.0.1:5003](http://127.0.0.1:5003/).
