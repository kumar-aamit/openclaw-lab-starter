# Your app's image: the shared base-app platform plus this repo's app/ folder.
# On the Kubernetes cluster the BuildConfig replaces BASE_IMAGE with the base-app ImageStreamTag and
# sets APP_COMMIT as a build env var; locally, pass --build-arg APP_COMMIT=$(git rev-parse HEAD).
ARG BASE_IMAGE=base-app:latest
FROM ${BASE_IMAGE}
ARG APP_COMMIT=dev
ENV APP_COMMIT=${APP_COMMIT}
COPY app/ /opt/app-root/app/
