# LibNora

**A smart library management system with automated testing and
deployment.**

LibNora simplifies library operations through a web interface for
managing books, users, and borrowing transactions. The project combines
a Python application with persistent MongoDB storage and a containerized
deployment workflow.

## Overview

LibNora is designed to make everyday library tasks easier while
demonstrating a practical DevOps workflow. The application runs on the
project team's laptop in Docker containers and can be shared externally
through an ngrok tunnel when required.

## Features

-   **Book management:** Add, view, search, update, and remove book
    records.
-   **User records:** Maintain library user information.
-   **Issue and return:** Record borrowing and returns.
-   **Availability tracking:** Track which books are available or
    issued.
-   **Persistent storage:** Store application records in MongoDB.
-   **Automated validation:** Run application tests as part of the CI/CD
    workflow.
-   **Containerized deployment:** Package and run the application
    consistently with Docker.
-   **External access:** Optionally expose the local application through
    ngrok.

## Technology Stack

  -----------------------------------------------------------------------
  Component               Technology              Purpose
  ----------------------- ----------------------- -----------------------
  User interface          Streamlit               Interactive web
                                                  interface

  Application logic       Python                  Library operations and
                                                  business rules

  Database                MongoDB                 Persistent storage

  Database driver         PyMongo                 Python-to-MongoDB
                                                  connectivity

  Containers              Docker, Docker Compose  Package and run
                                                  application services

  Version control         Git, GitHub             Source control and
                                                  collaboration

  CI/CD                   Jenkins                 Automate testing, image
                                                  building, and
                                                  deployment

  Testing                 Pytest                  Automated application
                                                  tests

  External access         ngrok                   Securely expose the
                                                  local web interface
                                                  when needed
  -----------------------------------------------------------------------

## Architecture

``` text
User's browser
     |
     v
ngrok tunnel (optional)
     |
     v
Streamlit application
(Python UI and application logic)
     |
     v
MongoDB
(books, users, borrowing records)

GitHub --> Jenkins --> Tests --> Docker image --> Local deployment
```

The application and database communicate over the Docker Compose
network. MongoDB should not be exposed directly to the public internet.
ngrok is used only to provide access to the application interface.

## Getting Started

### Prerequisites

Install the following before running the project:

-   Python and pip, if running without Docker
-   Docker and Docker Compose
-   Git
-   Jenkins, for the CI/CD workflow
-   An ngrok account and client, if external access is needed

### 1. Clone the repository

``` bash
git clone https://github.com/SarahSohaib/LibNora.git
cd LibNora
```

### 2. Configure environment variables

Copy the example file to `.env` in the repository root. Compose reads
these values when it starts the services:

``` env
MONGODB_URI=mongodb://mongodb:27017
MONGODB_DATABASE=libnora
```

The values above match the Compose MongoDB service and the database name
used by the application. Keep `.env` local; `.env.example` contains only
non-secret defaults. MongoDB has no host-published port and is reachable
only by services on the Compose network.

To create the local file, run `cp .env.example .env` in a Unix-like
shell, or `Copy-Item .env.example .env` in PowerShell. The defaults also
work without a `.env` file.

### 3. Run with Docker Compose

From the repository root, run:

``` bash
docker compose up --build -d
```

Open the Streamlit application at:

``` text
http://localhost:8501
```

To inspect running services and logs:

``` bash
docker compose ps
docker compose logs -f
```

To stop the services:

``` bash
docker compose down
```

The Compose file uses a persistent Docker volume for MongoDB so records
are retained when containers are recreated.

### 4. Run tests

Install the runtime dependencies and Pytest, then run the existing test
suite:

``` bash
python -m pip install -r requirements.txt pytest
python -m pytest
```

The Pytest configuration discovers tests under `tests/`. Existing tests
exercise book and member validation, availability, search, and
issue/return workflows without requiring a running MongoDB instance.

### 5. Enable external access with ngrok

With the Compose application running, start ngrok on the Streamlit host
port:

``` bash
ngrok http 8501
```

ngrok forwards port 8501, which is the Streamlit application only; do
not tunnel MongoDB. Keep the application and ngrok running, restrict
sharing of the forwarding URL, and stop the tunnel when it is no longer
needed.

## CI/CD Workflow

Configure a Jenkins Multibranch Pipeline job to use this GitHub
repository and its `Jenkinsfile`. The Jenkins agent must have
Python 3, Docker, and the Docker Compose plugin installed, and must be
able to access the local Docker daemon. The pipeline runs these stages:

1.  **Checkout:** Check out the revision supplied by the configured
    GitHub job.
2.  **Test:** Install `requirements.txt` and Pytest, then run the suite.
    Jenkins stops on failure, so later stages do not run.
3.  **Build:** Build the Compose `app` image.
4.  **Deploy:** On `main` only, start/update the app and MongoDB with
    Compose, using the image built in the preceding stage.

The Jenkins agent must run on the project laptop (or have access to its
Docker daemon) for deployment to be local. Configure GitHub access in
Jenkins when required by the repository; do not put access tokens or
database credentials in the `Jenkinsfile` or repository.

## Project Structure

A project structure:

``` text
LibNora/
├── app.py                  # Streamlit entry point
├── requirements.txt        # Python dependencies
├── .env.example            # Example environment variables
├── .gitignore
├── Dockerfile              # Application image definition
├── compose.yaml            # Application and database services
├── Jenkinsfile             # CI/CD pipeline definition
├── pytest.ini               # Pytest discovery settings
├── tests/
│   └── test_app.py          # Application tests
└── README.md
```

The Jenkins pipeline runs tests before building and deploys with Docker
Compose on the `main` branch. Start ngrok separately with
`ngrok http 8501` after the application is healthy; Jenkins does not
publish MongoDB.

## Team Responsibilities

-   **Samar:** Streamlit interface, Python application logic, MongoDB
    integration, core library features, and application-level tests.
-   **Sarah:** Docker, Docker Compose, Jenkins pipeline, CI/CD test
    integration, laptop deployment, ngrok setup, and DevOps
    documentation.

Both contributors share responsibility for integration, debugging,
end-to-end validation, and the final demonstration.

## Security and Limitations

-   Do not commit `.env` files, credentials, or sensitive user data.
-   Do not expose MongoDB directly through ngrok or a public port.
-   Restrict access to the ngrok URL and add authentication where
    appropriate.
-   Local deployment depends on the laptop's availability, network
    connectivity, and running services.
-   This project is intended as an academic implementation and should be
    security-reviewed before use with real library or personal data.

## License

Add a license file if the project is intended for public reuse. Until a
license is specified, reuse is not explicitly granted.
