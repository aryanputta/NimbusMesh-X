# Terraform Simulation

This folder models Azure-style cluster and node-pool definitions for reproducible infrastructure simulation.

Use:

```bash
terraform -chdir=terraform init
terraform -chdir=terraform plan -var-file=terraform.tfvars
```

The resources are represented with `null_resource` blocks to keep this runnable in local/offline CI while preserving AKS-like structure and cost metadata.

