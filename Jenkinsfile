pipeline {
    agent any

    options {
        skipDefaultCheckout()
        disableConcurrentBuilds()
        timestamps()
    }

    triggers {
        pollSCM('H/5 * * * *')
    }

    parameters {
        string(name: 'IMAGE_REPOSITORY', defaultValue: 'acefitness', description: 'For publishing, use your Docker Hub username/repository.')
        booleanParam(name: 'RUN_SONAR', defaultValue: false, description: 'Run SonarQube analysis and enforce its quality gate.')
        booleanParam(name: 'PUBLISH_IMAGE', defaultValue: false, description: 'Push the runtime image to Docker Hub after tests pass.')
        booleanParam(name: 'DEPLOY', defaultValue: false, description: 'Deploy the published image to Kubernetes.')
        string(name: 'KUBE_NAMESPACE', defaultValue: 'default', description: 'Existing Kubernetes namespace.')
    }

    stages {
        stage('Checkout and validate') {
            steps {
                checkout scm
                script {
                    def version = readFile('VERSION').trim()
                    if (!(version ==~ /\d+\.\d+\.\d+/)) {
                        error('VERSION must use MAJOR.MINOR.PATCH format.')
                    }
                    if (!(params.IMAGE_REPOSITORY ==~ /[a-z0-9]+([._-][a-z0-9]+)*(\/[a-z0-9]+([._-][a-z0-9]+)*)?/)) {
                        error('IMAGE_REPOSITORY must be a lowercase Docker Hub name, optionally prefixed with username/.')
                    }
                    if (params.PUBLISH_IMAGE && !params.IMAGE_REPOSITORY.contains('/')) {
                        error('IMAGE_REPOSITORY must include your Docker Hub username when publishing.')
                    }
                    if (params.DEPLOY && !params.PUBLISH_IMAGE) {
                        error('Enable PUBLISH_IMAGE before deploying so the cluster can pull the image.')
                    }
                    if (!(params.KUBE_NAMESPACE ==~ /[a-z0-9]([-a-z0-9]*[a-z0-9])?/)) {
                        error('KUBE_NAMESPACE must be a lowercase Kubernetes namespace name.')
                    }
                    def commit = sh(script: 'git rev-parse --short=12 HEAD', returnStdout: true).trim()
                    env.IMAGE_TAG = "${version}-${commit}-${env.BUILD_NUMBER}"
                    env.APP_IMAGE = "${params.IMAGE_REPOSITORY}:${env.IMAGE_TAG}"
                    env.TEST_IMAGE = "acefitness-test:${commit}-${env.BUILD_NUMBER}"
                }
                echo "Image: ${env.APP_IMAGE}"
            }
        }

        stage('Test in container') {
            steps {
                sh '''
                    set -eu
                    mkdir -p test-results
                    rm -f test-results/pytest.xml
                    docker build --target test -t "$TEST_IMAGE" .
                    docker run --rm -v "$WORKSPACE/test-results:/reports" "$TEST_IMAGE" \
                        pytest -q --junitxml=/reports/pytest.xml
                '''
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'test-results/pytest.xml'
                }
            }
        }

        stage('SonarQube analysis') {
            when { expression { params.RUN_SONAR } }
            steps {
                withSonarQubeEnv('SonarQube') {
                    sh 'sonar-scanner'
                }
            }
        }

        stage('Quality gate') {
            when { expression { params.RUN_SONAR } }
            steps {
                timeout(time: 10, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        stage('Build runtime image') {
            steps {
                sh 'docker build --target runtime -t "$APP_IMAGE" .'
            }
        }

        stage('Publish image') {
            when { expression { params.PUBLISH_IMAGE } }
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub', usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASSWORD')]) {
                    sh '''
                        set -eu
                        export DOCKER_CONFIG="$WORKSPACE/.docker-jenkins-$BUILD_NUMBER"
                        mkdir -p "$DOCKER_CONFIG"
                        trap 'rm -f "$DOCKER_CONFIG/config.json"; rmdir "$DOCKER_CONFIG"' EXIT
                        printf '%s' "$DOCKER_PASSWORD" | docker login --username "$DOCKER_USER" --password-stdin
                        docker push "$APP_IMAGE"
                    '''
                }
            }
        }

        stage('Deploy rolling update') {
            when { expression { params.DEPLOY } }
            steps {
                sh '''#!/usr/bin/env bash
                    set -euo pipefail
                    kubectl -n "$KUBE_NAMESPACE" apply -f k8s/service.yaml
                    kubectl set image -f k8s/deployment.yaml "web=$APP_IMAGE" --local -o yaml |
                        kubectl -n "$KUBE_NAMESPACE" apply -f -
                    if ! kubectl -n "$KUBE_NAMESPACE" rollout status deployment/acefitness --timeout=180s; then
                        echo "Rollout failed; attempting to restore the previous revision."
                        kubectl -n "$KUBE_NAMESPACE" rollout undo deployment/acefitness || echo "No previous revision is available."
                        exit 1
                    fi
                '''
            }
        }
    }
}
