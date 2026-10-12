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
git clone <repository-url>
cd LibNora
```

Replace `<repository-url>` with the project's GitHub repository URL.

### 2. Configure environment variables

Create a local `.env` file using the variables expected by the
application. For example:

``` env
MONGODB_URI=mongodb://mongodb:27017
MONGODB_DATABASE=libnora
```

Use `mongodb://localhost:27017` for a Python process running directly on
the host when MongoDB is also exposed on the host. When the application
runs inside Docker Compose, use the MongoDB service name as the
hostname.

Keep credentials and secret values out of source control. Add `.env` to
`.gitignore` and commit a `.env.example` containing placeholders only.

### 3. Run with Docker Compose

From the directory containing `compose.yaml` or `docker-compose.yml`,
run:

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

Use a persistent Docker volume for MongoDB so records are retained when
containers are recreated. Confirm the actual Compose filename and
service configuration in the repository before running these commands.

### 4. Run tests

Install the project's dependencies, then run:

``` bash
pytest
```

The test suite should cover key application operations, including book
management, availability, and issue/return workflows.

### 5. Enable external access with ngrok

Start the application locally, then run:

``` bash
ngrok http 8501
```

Use the HTTPS forwarding URL provided by ngrok to access the Streamlit
interface remotely. The laptop, application container, and ngrok process
must remain running. Share the URL only with intended users, and avoid
exposing sensitive records or administrative functions without
appropriate access controls.

## CI/CD Workflow

The intended Jenkins pipeline follows these stages:

1.  **Checkout:** Retrieve the latest source code from GitHub.
2.  **Test:** Run automated tests and stop the pipeline if they fail.
3.  **Build:** Build the application Docker image.
4.  **Deploy:** Update the running application on the project laptop.
5.  **Verify:** Check that the application starts and responds as
    expected.

Configure Jenkins credentials securely and avoid storing tokens,
passwords, or database secrets in the repository or pipeline script. The
exact trigger and deployment steps depend on the Jenkins configuration
and repository setup.

## Project Structure

A possible structure for the project is:

``` text
LibNora/
├── app.py                  # Streamlit entry point
├── requirements.txt        # Python dependencies
├── Dockerfile              # Application image definition
├── compose.yaml            # Application and database services
├── .env.example            # Example environment variables
├── .gitignore
├── tests/                  # Pytest test suite
├── Jenkinsfile             # CI/CD pipeline definition
└── README.md
```

File names may differ in the implemented repository.

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
