# Bharath CSPM — OPA-Based Azure Compliance Automation

A Cloud Security Posture Management (CSPM) framework for Microsoft Azure that enforces CIS Azure Foundations Benchmark v3.0 controls through two Jenkins CI/CD pipelines: one **preventive** (blocks non-compliant IaC before deployment) and one **remediative** (detects drift in live infrastructure and auto-remediates).

---

## Project Structure

```
OPA-main/
├── Jenkinsfile.preventive         Jenkins pipeline — pre-deployment policy gate
├── Jenkinsfile.remediative        Jenkins pipeline — drift detection & auto-fix
├── parse_findings.py              standalone: tfsec + Checkov JSON → blocking/warnings classifier (not called by pipelines)
├── generate_report.py             standalone: consolidated security_report.json generator (not called by pipelines)
├── requirements.txt               Python dependencies
│
├── policies/
│   ├── cis_azure.rego             OPA: CIS Azure Benchmark v3.0 (input: tfsec JSON)
│   ├── vm_size.rego               OPA: VM size enforcement per environment
│   └── tags.rego                  OPA: mandatory tag governance
│
├── scripts/
│   ├── query_azure.py             Fires all 4 Azure Resource Graph queries → *_raw.json
│   ├── detect_nsg_drift.py        CIS 6.1/6.2 — open SSH/RDP ports on NSGs
│   ├── detect_storage_drift.py    CIS 3.15/3.5 — Storage HTTPS + public blob
│   ├── detect_scaling_drift.py    Cost Governance — VMs outside IaC baseline sizes
│   ├── detect_iam_drift.py        CIS 1.1 — unauthorized high-privilege role assignments
│   ├── generate_dashboard.py      Compliance % aggregator → compliance_dashboard_*.json
│   └── cis_mapper.py              Legacy drift → remediation command generator
│
└── terraform/
    ├── main.tf                    ALL resources: provider, RG, VNet, NSG, NIC, VM, Storage
    ├── variables.tf               Input variables (environment, vm_size, prefix, etc.)
    ├── outputs.tf                 Output resource IDs
    ├── storage_pass.tf            (deprecated — resources moved to main.tf)
    └── storage_fail.tf            (deprecated — resources moved to main.tf)
```

---

## CIS Controls Enforced

### Preventive Pipeline (IaC — pre-deployment)

| Check | Tool | CIS Rule | tfsec ID | Description |
|-------|------|----------|----------|-------------|
| Static Analysis | tfsec | 3.1 | AVD-AZU-0010 | HTTPS-only required (artifact only) |
| Static Analysis | tfsec | 3.2 | AVD-AZU-0014 | Infrastructure encryption (artifact only) |
| Static Analysis | tfsec | 3.6 | AVD-AZU-0012 | Public blob access disabled (artifact only) |
| Static Analysis | tfsec | 3.7 | AVD-AZU-0011 | Network default action: Deny (artifact only) |
| Static Analysis | tfsec | 3.10 | AVD-AZU-0013 | TLS 1.2 minimum (artifact only) |
| Cost Governance | OPA | — | vm_size.rego | VM size within per-env allowlist — **blocks deployment** |
| Tag Governance | OPA | — | tags.rego | Environment, CostCenter, ManagedBy required — **blocks deployment** |

> tfsec and Checkov run in Layer A and write `tfsec_results.json` / `checkov_results.json` for review. Only OPA policy violations (VM size, mandatory tags) block the build and prevent `terraform apply`.

### Remediative Pipeline (Live Azure — post-deployment)

| Check | Tool | CIS Rule | Description |
|-------|------|----------|-------------|
| CIS Benchmark | tfsec + OPA | 3.1/3.2/3.6/3.7/3.10 | cis_azure.rego against fresh tfsec scan |
| NSG Open Ports | Python + ARG | 6.1 / 6.2 | SSH/RDP open to internet |
| Storage HTTPS | Python + ARG | 3.15 / 3.5 | HTTPS-only disabled or public blob on |
| VM Scaling | Python + ARG | Cost | VMs beyond IaC approved sizes |
| IAM Tampering | Python + ARG | 1.1 | Unauthorized Owner/Contributor assignments |

---

## Technology Stack

| Layer | Tool |
|-------|------|
| Policy Engine | Open Policy Agent (OPA) + Rego |
| IaC Scanners | tfsec + Checkov (run in parallel) |
| Infrastructure | Terraform (azurerm provider v4.0+) |
| Cloud Platform | Microsoft Azure |
| CI/CD | Jenkins (Windows agent) |
| Scripting | Python 3.12, Windows Batch |
| Cloud API | Azure CLI, Azure Resource Graph |
| Notifications | Microsoft Teams (incoming webhook) |

---

## Terraform Resources (main.tf)

All resources required by both pipelines are defined in `terraform/main.tf`:

| Resource | Type | Purpose |
|----------|------|---------|
| `azurerm_resource_group.main` | Core | Shared container for all resources |
| `azurerm_virtual_network.main` | Networking | VNet for VM placement |
| `azurerm_subnet.main` | Networking | Subnet within VNet |
| `azurerm_network_security_group.main` | Security | Deny-all NSG (no open ports) |
| `azurerm_subnet_network_security_group_association.main` | Security | Binds NSG to subnet |
| `azurerm_network_interface.main` | Networking | NIC for the Linux VM |
| `azurerm_linux_virtual_machine.main` | Compute | Exercises OPA `vm_size.rego` |
| `azurerm_storage_account.secure` | Storage | Passes all CIS 3.x checks |
| `azurerm_storage_account.vulnerable` | Storage | Intentional CIS 3.6 violation (demo) |

All tagged resources carry `Environment`, `CostCenter`, and `ManagedBy` as required by `policies/tags.rego`.

### Key Variable Defaults

| Variable | Default | Effect |
|----------|---------|--------|
| `environment` | `dev` | Controls OPA vm_size allowlist |
| `vm_size` | `Standard_B2s` | Must be in allowlist — change to trigger cost violation |
| `prefix` | `secops` | Prepended to all resource names |
| `cost_center` | `security-lab` | Value of the CostCenter mandatory tag |

---

## Prerequisites

### Jenkins Agent (Windows)

| Tool | Location |
|------|----------|
| `opa.exe` | `C:/Program Files/OPA/` |
| `tfsec.exe` | `C:/Program Files/tfsec/` |
| `terraform.exe` | `C:/Program Files/terraform/` |
| `checkov` | `pip install checkov` — must be on PATH |
| `az` (Azure CLI) | installed, on PATH |
| `curl` | ships with Windows 10/11 |
| Python 3.12 | `C:/Users/admin/AppData/Local/Programs/Python/Python312/` |

### Jenkins Credentials

| Credential ID | Used By | Description |
|---------------|---------|-------------|
| `AZURE_SUBSCRIPTION_ID` | Both | Azure subscription ID |
| `AZURE_CLIENT_ID` | Both | Service principal App ID |
| `AZURE_CLIENT_SECRET` | Both | Service principal secret |
| `AZURE_TENANT_ID` | Both | Azure AD tenant ID |
| `TEAMS_WEBHOOK_URL` | Remediative | Teams incoming webhook URL |

The service principal requires **Reader** on the subscription (Resource Graph queries) and **Contributor** on remediated resources.

---

## Pipeline 1 — Preventive (`Jenkinsfile.preventive`)

Runs on every pull request or push. OPA policy violations (VM size, mandatory tags) block `terraform apply`. tfsec then Checkov run sequentially, both with `returnStatus: true`, and generate scan artifacts for review.

### Stages

| Stage | What runs | Output |
|-------|-----------|--------|
| **Checkout Code** | `checkout scm` | — |
| **Terraform Init & Validate** | `terraform init` + `terraform validate` (catchError — UNSTABLE on failure) | — |
| **Layer A: Static Analysis** | tfsec then Checkov (sequential, both non-blocking) | `tfsec_results.json`, `tfsec_error.log`, `checkov_results.json`, `checkov_error.log` |
| **Terraform Plan generation** | `terraform plan` + `terraform show -json` (catchError — UNSTABLE on failure) | `tfplan.json`, `env_config.json` |
| **Layer B: OPA Policy Validation** | VM Size + Mandatory Tags in parallel | `opa_vm_result.json`, `opa_tags_result.json` |
| **Terraform Apply (Deploy)** | `terraform apply` — only when `currentResult == SUCCESS` | Azure resources |

### OPA Policies in Layer B

| Sub-stage | Policy | Input | Blocks On |
|-----------|--------|-------|-----------|
| VM Size Policy | `policies/vm_size.rego` | `tfplan.json` + `env_config.json` | VM size outside env allowlist |
| Mandatory Tags | `policies/tags.rego` | `tfplan.json` | Missing `Environment`, `CostCenter`, or `ManagedBy` |

---

## Pipeline 2 — Remediative (`Jenkinsfile.remediative`)

Runs on a schedule or manually against live Azure resources. Detects drift, auto-remediates where safe, and notifies for everything else.

### Stages

| Stage | What runs | Output |
|-------|-----------|--------|
| **Checkout Code** | `checkout scm` + clean `outputs/` | — |
| **Environment Setup** | `az login` + `az account set` | — |
| **Query Azure Resource Graph** | `query_azure.py` — 4 parallel ARG queries | `outputs/*_raw.json` |
| **Execute Python Audit Engine (CIS Mapping)** | 4 detect scripts + tfsec + OPA CIS check + dashboard | `outputs/*_drift.json`, `outputs/opa_cis_result.json`, `outputs/compliance_dashboard_pre_remediation.json` |
| **Generate Remediation Scripts** | Preview + archive all `*_remediate.bat` files | `outputs/*.bat` |
| **Trigger Self-Healing & Alerts** | Scenario 1 auto-fix → Scenario 2 approval → Scenario 3 notify → Scenario 4 alert → post-remediation scan → Teams | `outputs/compliance_dashboard_post_remediation.json` |

### Remediation Modes

| Scenario | Drift Detected | Action | Build Result |
|----------|---------------|--------|--------------|
| 1 — NSG open ports | Port 22/3389 open to internet | Auto-fix: set rule to Deny | SUCCESS |
| 2 — Storage HTTPS | HTTPS-only off or public blob on | Manual approval gate (30 min timeout) | SUCCESS if approved |
| 3 — VM scaling | VM size outside IaC baseline | Notify DevOps, script generated | UNSTABLE |
| 4 — IAM tampering | Unauthorized Owner/Contributor at sub scope | Alert security team, removal script generated | UNSTABLE |

---

## OPA Policies

### `cis_azure.rego` — CIS Azure Benchmark (remediative pipeline)
Input: `outputs/tfsec_scan.json` (fresh tfsec run on checked-out Terraform)

Evaluates 5 CIS controls. Resources can be whitelisted in `exception_list`.

| tfsec ID | CIS # | Violation produced |
|----------|-------|--------------------|
| AVD-AZU-0010 | 3.1 | Secure transfer (HTTPS) disabled |
| AVD-AZU-0012 | 3.6 | Public blob access enabled |
| AVD-AZU-0011 | 3.7 | Network default action not Deny |
| AVD-AZU-0013 | 3.10 | TLS below 1.2 |
| AVD-AZU-0014 | 3.2 | Infrastructure encryption disabled |

### `vm_size.rego` — VM Size Enforcement (preventive pipeline)
Input: `tfplan.json` + `env_config.json`

| Environment | Permitted sizes |
|-------------|----------------|
| `dev` | B1s, B2s, B2ms, B4ms, D2s_v3, D4s_v3 |
| `staging` | B2s, B4ms, D2s_v3, D4s_v3, D8s_v3 |
| `prod` | D2–D16s_v3, E4–E16s_v3 |

### `tags.rego` — Mandatory Tag Governance (preventive pipeline)
Input: `tfplan.json`

Required tags on all tracked resource types: `Environment`, `CostCenter`, `ManagedBy`

---

## Artifacts Reference

### Preventive Pipeline

| File | Created By | Contents |
|------|-----------|---------|
| `tfsec_results.json` | tfsec | Findings with AVD IDs, severity, file:line (advisory — review only) |
| `tfsec_error.log` | tfsec | stderr from tfsec run (deprecation notices, errors) |
| `checkov_results.json` | Checkov | Additional IaC findings written via `--output-file` (advisory — review only) |
| `checkov_error.log` | Checkov | stderr from Checkov run (warnings, errors) |
| `env_config.json` | Terraform Plan stage | `{"config":{"environment":"dev"}}` |
| `tfplan.json` | Terraform | Full plan JSON — OPA vm_size + tags input |
| `opa_vm_result.json` | OPA | VM Size Policy result (PASSED / FAILED / SKIPPED) |
| `opa_tags_result.json` | OPA | Mandatory Tags result (PASSED / FAILED / SKIPPED) |

### Remediative Pipeline

| File | Created By | Contents |
|------|-----------|---------|
| `outputs/*_raw.json` | `query_azure.py` | Raw Azure Resource Graph query results |
| `outputs/*_drift.json` | `detect_*.py` | Structured drift findings per scenario |
| `outputs/*_remediate.bat` | `detect_*.py` | Azure CLI remediation commands |
| `outputs/tfsec_scan.json` | tfsec | Fresh tfsec scan for CIS OPA check |
| `outputs/opa_cis_result.json` | OPA | CIS Azure Benchmark result |
| `outputs/compliance_dashboard_pre_remediation.json` | `generate_dashboard.py` | Compliance % before fixes |
| `outputs/compliance_dashboard_post_remediation.json` | `generate_dashboard.py` | Compliance % after fixes |
| `outputs/compliance_dashboard_latest.json` | `generate_dashboard.py` | Latest snapshot (dashboard polling) |
| `outputs/teams_payload.json` | Trigger Self-Healing & Alerts stage | Teams MessageCard payload sent to TEAMS_WEBHOOK_URL |
