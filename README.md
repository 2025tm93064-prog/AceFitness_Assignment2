# ACEest Fitness - Assignment 2

Version 1.0.0 is a Flask adaptation of the original Tkinter v1.0: choose a
fitness program to view its workout and nutrition plan. The application is
read-only and has no database. `/health` is used by Kubernetes health probes.

## What is included

- `ACEest_Fitness.py`, `templates/`, and `static/`: application.
- `tests/`: Pytest tests.
- `VERSION`: application version.
- `Dockerfile`: separate test and runtime image targets.
- `Jenkinsfile`: containerized tests, optional SonarQube quality gate, image
  build, optional Docker Hub push and Kubernetes deployment.
- `k8s/`: a two-replica rolling Deployment and NodePort Service.

The commands below assume a Linux VM, a shell in the repository directory, and
the relevant tools already installed. No credentials should be committed.

## Run and test locally

Python 3.12 is the runtime used by the container. Create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest -q
flask --app ACEest_Fitness run --host 0.0.0.0 --port 5000
```

Open `http://localhost:5000`, select a program and click **Show plan**. From
another terminal, check the health endpoint with:

```bash
curl -f http://localhost:5000/health
```

For a remote VM, use its accessible IP address instead of `localhost`. The
Flask development server is for local testing only.

## Build, test and run with Docker

```bash
docker build --target test -t acefitness-test:1.0.0 .
docker run --rm acefitness-test:1.0.0
docker build --target runtime -t acefitness:1.0.0 .
docker run --rm -d --name acefitness -p 5000:5000 acefitness:1.0.0
curl -f http://localhost:5000/health
docker stop acefitness
```

The runtime image uses Gunicorn and excludes the test dependencies. To publish
it to Docker Hub, replace `YOUR_DOCKERHUB_USER` with your own account:

```bash
docker login
docker tag acefitness:1.0.0 YOUR_DOCKERHUB_USER/acefitness:1.0.0
docker push YOUR_DOCKERHUB_USER/acefitness:1.0.0
```

Use unique tags for later releases; do not overwrite a deployed release tag.

## Deploy to Kubernetes

These commands assume an existing cluster, configured `kubectl` context, and
an image pushed to a registry accessible by the cluster. `default` is the
namespace used below. For a private Docker Hub repository, configure a
Kubernetes image pull secret separately.

```bash
export IMAGE=YOUR_DOCKERHUB_USER/acefitness:1.0.0
kubectl -n default apply -f k8s/service.yaml
kubectl set image -f k8s/deployment.yaml "web=$IMAGE" --local -o yaml \
  | kubectl -n default apply -f -
kubectl -n default rollout status deployment/acefitness --timeout=180s
kubectl -n default get deployments,pods,services
```

The image in the manifest is a placeholder: always substitute your published
image as above. With Minikube, get the service address on the VM using:

```bash
minikube service acefitness --url -n default
```

The returned address may only be reachable from the VM. For assessment access,
configure suitable network access or an ingress/load balancer; confirm the
endpoint is reachable by the reviewer. On other clusters, use a node IP and the
NodePort shown by `kubectl -n default get service acefitness`.

For a later version, push a new image and update the Deployment:

```bash
kubectl -n default set image deployment/acefitness web=YOUR_DOCKERHUB_USER/acefitness:NEW_TAG
kubectl -n default rollout status deployment/acefitness --timeout=180s
kubectl -n default rollout history deployment/acefitness
kubectl -n default rollout undo deployment/acefitness
kubectl -n default rollout status deployment/acefitness --timeout=180s
```

Rollback requires a previous Deployment revision. The pipeline attempts a
rollback if a rollout fails, then marks the build failed. An initial deployment
has no previous version to restore.

## Jenkins setup

1. Install the Pipeline, Git, Docker-related and SonarQube Scanner for Jenkins
   plugins as needed. The Jenkins agent must have Docker and Bash; its user must
   be able to build and run containers. For deployment it also needs `kubectl`
   and a kubeconfig authorized for the target namespace. Docker access grants
   powerful host privileges; use a trusted agent.
2. Create a Pipeline job **from SCM**, select Git, and provide this repository
   URL and branch (`main`). Use `Jenkinsfile` as the script path. Grant access
   if the repository is private. The pipeline polls SCM approximately every
   five minutes; a GitHub webhook can also trigger it if configured in Jenkins.
3. For image publishing, create a Jenkins **username/password** credential
   with ID `dockerhub`. Use your Docker Hub username and an access token.
   The job's `IMAGE_REPOSITORY` must be `yourusername/acefitness`. If using a
   private image, configure the cluster's pull secret independently.
4. For SonarQube, configure a Jenkins server installation named `SonarQube`,
   provide `sonar-scanner` on the agent's PATH, and configure SonarQube's webhook
   to `https://YOUR_JENKINS_URL/sonarqube-webhook/` (use your actual scheme
   and address). The webhook must be reachable by SonarQube. Configure the
   SonarQube project/quality gate and credentials as appropriate.
5. Run **Build with Parameters**. The default build checks out the source,
   runs Pytest in the test image, publishes the JUnit result, and builds the
   runtime image. Enable `RUN_SONAR` to enforce the quality gate. Enable
   `PUBLISH_IMAGE` to push; enable both `PUBLISH_IMAGE` and `DEPLOY` to deploy.
   `KUBE_NAMESPACE` must already exist. The pushed image is tagged
   `VERSION-shortGitCommit-buildNumber`; use the build log to find it.

The build needs registry access for the base image and Python packages. Configure
the Jenkins URL and GitHub webhook separately if choosing webhooks; SCM polling
is already in the Jenkinsfile. Keep test reports and SonarQube results as
submission evidence.

## Version control and releases

This repository starts at **1.0.0**. Use `main` for stable code and short-lived
feature branches for changes. Update `VERSION` using semantic versioning:
patch for fixes, minor for backward-compatible features, major for breaking
changes. Run tests before committing. For the first release, review the files,
then create a commit and an annotated tag:

```bash
git status
git add .
git commit -m "Add ACEest Fitness version 1.0.0"
git tag -a v1.0.0 -m "ACEest Fitness version 1.0.0"
git push -u origin main
git push origin v1.0.0
```

For later work, create a branch (`git switch -c feature/description`), commit
the changes, merge via a pull request, and tag the release commit with the new
version. Keep Git tags, `VERSION`, and release image tags aligned.

## Assignment scope still to complete

This initial version demonstrates a rolling update and rollback only. Blue-green,
canary, shadow and A/B deployment require additional routing/configuration and
demonstrations. A successful Jenkins run, SonarQube report, image repository,
reviewer-accessible endpoint and 2-3 page report must be produced on the VM for
the final submission.
