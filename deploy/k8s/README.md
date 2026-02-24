# OwlClaw Kubernetes Manifests

## Files

- `cron-deployment.yaml`: OwlClaw cron deployment with replicas, resources, probes, and Prometheus annotations.
- `cron-service.yaml`: internal ClusterIP service for HTTP/metrics exposure.
- `owlhub-api-deployment.yaml`: OwlHub API deployment with health probes, resources, and Prometheus annotations.
- `owlhub-api-service.yaml`: ClusterIP service exposing OwlHub API HTTP traffic.
- `owlhub-api-configmap.yaml`: non-sensitive OwlHub API runtime configuration.
- `owlhub-api-secret.yaml`: secret template for database and redis connection settings.
- `owlhub-api-ingress.yaml`: ingress rule mapping `owlhub.local` to OwlHub API service.

## Apply

```bash
kubectl apply -f deploy/k8s/cron-deployment.yaml
kubectl apply -f deploy/k8s/cron-service.yaml
kubectl apply -f deploy/k8s/owlhub-api-configmap.yaml
kubectl apply -f deploy/k8s/owlhub-api-secret.yaml
kubectl apply -f deploy/k8s/owlhub-api-deployment.yaml
kubectl apply -f deploy/k8s/owlhub-api-service.yaml
kubectl apply -f deploy/k8s/owlhub-api-ingress.yaml
```

## Required Secret

Create Hatchet token secret before deployment:

```bash
kubectl create secret generic hatchet-secret --from-literal=api_token=<your-token>
```

For OwlHub API, you can apply the included secret template directly or replace values with your own:

```bash
kubectl apply -f deploy/k8s/owlhub-api-secret.yaml
```

## CI/CD

OwlHub API deployment workflow:

- `.github/workflows/owlhub-api-deploy.yml`

Required GitHub Environments/Secrets/Variables:

- Environment `owlhub-staging`
  - Secret: `KUBE_CONFIG_STAGING_B64`
  - Variable: `OWLHUB_K8S_NAMESPACE_STAGING`
  - Variable: `OWLHUB_API_BASE_URL_STAGING`
- Environment `owlhub-production`
  - Secret: `KUBE_CONFIG_PRODUCTION_B64`
  - Variable: `OWLHUB_K8S_NAMESPACE_PRODUCTION`
  - Variable: `OWLHUB_API_BASE_URL_PRODUCTION`

The workflow runs:

1. Build and push API image to GHCR.
2. Apply Kubernetes manifests and roll out new image.
3. Run `alembic upgrade head` in running API pod.
4. Execute post-deploy smoke checks (`/health`, `/metrics`).
