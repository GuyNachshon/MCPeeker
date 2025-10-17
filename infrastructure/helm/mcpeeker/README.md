# MCPeeker Helm Chart

This Helm chart deploys the MCPeeker MCP Detection and Registry Platform on Kubernetes.

## Prerequisites

- Kubernetes 1.24+
- Helm 3.8+
- PV provisioner support in the underlying infrastructure (for persistence)
- cert-manager (optional, for TLS certificate management)
- metrics-server (optional, for autoscaling)
- Ingress controller (nginx recommended)

## Installation

### Quick Start

```bash
helm install mcpeeker infrastructure/helm/mcpeeker \
  --namespace mcpeeker \
  --create-namespace \
  --set global.domain=mcpeeker.example.com \
  --set judge.anthropicApiKey=YOUR_ANTHROPIC_API_KEY
```

### Install with Custom Values

Create a custom values file and install:

```bash
helm install mcpeeker infrastructure/helm/mcpeeker \
  --namespace mcpeeker \
  --create-namespace \
  --values my-values.yaml
```

## Configuration

### Global Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| global.domain | Domain name for the application | mcpeeker.example.com |
| global.environment | Environment name | production |
| global.nats.url | NATS connection URL | nats://nats:4222 |
| global.postgres.host | PostgreSQL host | postgres |
| global.postgres.port | PostgreSQL port | 5432 |
| global.clickhouse.host | ClickHouse host | clickhouse |
| global.clickhouse.port | ClickHouse port | 9000 |

### Service Configuration

Each service supports:
- enabled: Enable the service
- replicaCount: Number of replicas
- image.repository: Image repository
- image.tag: Image tag
- resources: CPU and memory requests/limits

### Ingress Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| ingress.enabled | Enable ingress | true |
| ingress.class | Ingress class name | nginx |
| ingress.tls.enabled | Enable TLS | true |
| ingress.certManager.enabled | Use cert-manager | false |

### Security Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| mtls.enabled | Enable mTLS | false |
| rbac.enabled | Enable RBAC | true |
| networkPolicy.enabled | Enable NetworkPolicy | false |

### Autoscaling Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| autoscaling.enabled | Enable HPA | false |

## Upgrading

```bash
helm upgrade mcpeeker infrastructure/helm/mcpeeker \
  --namespace mcpeeker \
  --values my-values.yaml
```

## Uninstallation

```bash
helm uninstall mcpeeker -n mcpeeker
```

## Architecture

The platform consists of 6 microservices:
- Scanner: Endpoint detection
- Correlator: Multi-layer correlation
- Signature Engine: Rule-based enrichment
- Judge: AI-powered classification
- Registry API: Backend API
- Frontend: React UI

## Troubleshooting

### Check Pod Status

```bash
kubectl get pods -n mcpeeker
kubectl describe pod <pod-name> -n mcpeeker
```

### View Logs

```bash
kubectl logs -n mcpeeker -l app=registry-api --tail=100
```

### Check Service Health

```bash
kubectl exec -n mcpeeker deployment/registry-api -- curl http://localhost:8000/health
```

### Database Migrations

```bash
kubectl exec -n mcpeeker -it deployment/registry-api -- alembic upgrade head
```

## Production Recommendations

1. Use external secret management
2. Use high-performance storage for ClickHouse
3. Enable HPA with metrics-server
4. Deploy Prometheus and Grafana
5. Enable ingress TLS with cert-manager
6. Configure regular backups
7. Adjust resource limits based on workload
8. Enable NetworkPolicy for security

## Support

- Documentation: https://github.com/ozlabs/mcpeeker
- Issues: https://github.com/ozlabs/mcpeeker/issues
