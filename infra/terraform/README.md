# Terraform

## Prerequisites

- [Terraform ≥ 1.7](https://developer.hashicorp.com/terraform/downloads)
- AWS credentials configured (`aws configure` or env vars)

## Usage

```bash
cd infra/terraform
terraform init
terraform plan -var="environment=dev"
terraform apply
```

## Modules

| Module | Purpose |
|--------|---------|
| `vpc`  | Networking (VPC, subnets, NAT) |

Add new modules under `modules/` and reference them in `main.tf`.
