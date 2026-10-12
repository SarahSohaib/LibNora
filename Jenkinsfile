def runCommand(String command) {
    if (isUnix()) {
        sh command
    } else {
        bat command
    }
}

pipeline {
    agent any

    options {
        skipDefaultCheckout(true)
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Test') {
            steps {
                script {
                    def python = isUnix()
                        ? 'python3'
                        : '"C:\\Users\\Sarah Sohaib\\FOLDER OF ALL FOLDERS\\miniconda3\\python.exe"'

                    runCommand("${python} -m pip install -r requirements.txt pytest")
                    runCommand("${python} -m pytest -q")
                }
            }
        }

        stage('Build') {
            steps {
                script {
                    runCommand('docker compose build app')
                }
            }
        }

        stage('Deploy') {
            when {
                branch 'main'
            }
            steps {
                script {
                    runCommand('docker compose up -d --no-build')
                }
            }
        }
    }
}