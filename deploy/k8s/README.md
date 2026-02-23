# OwlClaw Cron Kubernetes Manifests

## Files

- `cron-deployment.yaml`: OwlClaw cron deployment with replicas, resources, probes, and Prometheus annotations.
- `cron-service.yaml`: internal ClusterIP service for HTTP/metrics exposure.

## Apply

```bash
kubectl apply -f deploy/k8s/cron-deployment.yaml
kubectl apply -f deploy/k8s/cron-service.yaml
```

## Required Secret

Create Hatchet token secret before deployment:

```bash
kubectl create secret generic hatchet-secret --from-literal=api_token=<your-token>
```
