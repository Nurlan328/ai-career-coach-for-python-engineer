# Deploying to AWS (EKS)

Production deploy of the FastAPI API + Celery worker to **Amazon EKS**, with
**RDS** (Postgres), **ElastiCache** (Redis), **ECR** (images) and an **ALB**
ingress. CI builds and rolls out automatically — see
[`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml).

```
GitHub Actions ──build──> ECR ──image──> EKS
                                          ├── Deployment: api  (2..6 pods, HPA)  ── Service ── ALB Ingress ── Internet
                                          ├── Deployment: worker (Celery)
                                          └── Job: migrate (alembic upgrade head)
RDS (Postgres) ◄── api / worker / migrate
ElastiCache (Redis) ◄── api (cache) + worker (broker)
```

## Prerequisites (one-time)

1. **ECR repo**: `aws ecr create-repository --repository-name ai-career-coach`
2. **EKS cluster**: `eksctl create cluster --name career-coach --region us-east-1 --nodes 2`
3. **AWS Load Balancer Controller** installed in the cluster (for the ALB Ingress).
4. **RDS Postgres** + **ElastiCache Redis** in the cluster VPC; allow the node
   security group to reach them (5432 / 6379).
5. **GitHub OIDC role** `AWS_DEPLOY_ROLE_ARN` (ECR push + EKS access) added as a
   repo secret. The `metrics-server` add-on is needed for the HPA.

## Configure

- Non-secret config → [`k8s/10-config.yaml`](k8s/10-config.yaml) (ConfigMap).
  Set `REDIS_URL` to the ElastiCache endpoint (and delete `20-redis.yaml`).
- Secrets → **never commit real values**. Create them directly:

  ```bash
  kubectl create namespace career-coach
  kubectl -n career-coach create secret generic career-coach-secrets \
    --from-literal=SECRET_KEY="$(python -c 'import secrets;print(secrets.token_urlsafe(48))')" \
    --from-literal=ANTHROPIC_API_KEY="sk-ant-..." \
    --from-literal=DATABASE_URL="postgresql+asyncpg://USER:PASS@<rds-endpoint>:5432/career_coach"
  ```

  For a managed flow, sync from AWS Secrets Manager via the External Secrets Operator.

## Deploy

Automated (recommended): push a `v*` tag or run the **Deploy** workflow. It builds,
pushes to ECR, runs the migration Job, and rolls out `api` + `worker`.

Manual:

```bash
# image
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ACCOUNT>.dkr.ecr.us-east-1.amazonaws.com
docker build -t <ACCOUNT>.dkr.ecr.us-east-1.amazonaws.com/ai-career-coach:latest .
docker push <ACCOUNT>.dkr.ecr.us-east-1.amazonaws.com/ai-career-coach:latest

# cluster
aws eks update-kubeconfig --name career-coach --region us-east-1

# manifests (edit ACCOUNT/REGION in the image refs first, or use `kubectl set image`)
kubectl apply -f deploy/k8s/

# migrate, then the Deployments pick up the image
kubectl -n career-coach wait --for=condition=complete job/migrate --timeout=180s
kubectl -n career-coach get pods
```

The public URL is the ALB address: `kubectl -n career-coach get ingress career-coach`.

## Notes

- **Migrations** run as a one-off `Job` (`alembic upgrade head`); `AUTO_CREATE_TABLES`
  is `false` in production so Alembic owns the schema.
- **Embedding model**: the first `/coach/rag` call downloads the model into the pod
  (`FASTEMBED_CACHE_PATH`). For faster cold starts, bake it into the image or mount a
  shared PVC.
- **Frontend** is deployed separately (static build) — e.g. S3 + CloudFront — with
  `VITE_API_BASE` pointing at the ALB. `npm run build` → upload `frontend/dist/`.
- The in-cluster `redis` (`20-redis.yaml`) is for demo clusters; prefer ElastiCache
  in production.
