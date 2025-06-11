# CRDTSign

## Prerequisites
- Python 3.10+
- [Poetry](https://python-poetry.org/)

## Usage
1. Clone the repository.
```bash
git clone https://github.com/goro17/msc-thesis.git
```
2. Point to the package directory.
```bash
cd crdtsign
```
3. Install the package and its dependencies and run the server.
```bash
poetry install
poetry run crdtsign-app
```
4. Access the web interface through the browser at the desired host+port (default: [127.0.0.1:5000](http://127.0.0.1:5000/)).

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

3. Access the web interface through the browser at the desired host+port (default: [127.0.0.1:5000](http://127.0.0.1:5000/)).
