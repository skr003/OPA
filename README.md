# Bharath CSPM — OPA-Based Azure Compliance Automation

A Cloud Security Posture Management (CSPM) framework for Microsoft Azure that enforces CIS Azure Foundations Benchmark v3.0 controls through two Jenkins CI/CD pipelines: one **preventive** (blocks non-compliant IaC before deployment) and one **remediative** (detects drift in live infrastructure and auto-remediates).

---

## Project Structure

```
OPA-main/
├── Jenkinsfile.preventive        Jenkins pipeline — pre-deployment policy gate (5 scenarios)
├── Jenkinsfile.remediative       Jenkins pipeline — drift detection & auto-fix
├── requirements.txt              Python dependencies
├── policies/
│   ├── cis_azure.rego            OPA: CIS Azure Benchmark v3.0 (tfsec-based)
│   ├── vm_size.rego              OPA: VM size enforcement per environment
│   └── tags.rego                 OPA: mandatory tag governance
├── scripts/
│   └── cis_mapper.py             Drift findings → remediation command generator
└── terraform/
    ├── main.tf                   Azure provider + resource group
    ├── variables.tf              Input variables
    ├── outputs.tf                Output resource IDs
    ├── storage_pass.tf           Compliant storage account (passes all checks)
    └── storage_fail.tf           Non-compliant storage account (for testing)
```

---

## CIS Controls Enforced

| CIS Rule | Benchmark | tfsec ID | Description |
|----------|-----------|----------|-------------|
| 3.1 | Secure Transfer | AVD-AZU-0010 | HTTPS-only access required |
| 3.2 | Infrastructure Encryption | AVD-AZU-0014 | Encryption at rest required |
| 3.6 | Blob Public Access | AVD-AZU-0012 | Public blob access must be disabled |
| 3.7 | Default Network Action | AVD-AZU-0011 | Network default action must be Deny |
| 3.10 | Minimum TLS Version | AVD-AZU-0013 | TLS 1.2 or higher required |

---

## Technology Stack

| Layer | Tool |
|-------|------|
| Policy Engine | Open Policy Agent (OPA) + Rego |
| IaC Scanners | tfsec + Checkov (parallel) |
| Infrastructure | Terraform (azurerm provider v4.0+) |
| Cloud Platform | Microsoft Azure |
| CI/CD | Jenkins (Windows agent) |
| Scripting | Python 3.12, Windows Batch |
| Cloud API | Azure CLI, Azure Resource Graph |
| Notifications | Microsoft Teams (incoming webhook) |

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

### Jenkins Credentials Store

| Credential ID | Used By | Description |
|---------------|---------|-------------|
| `AZURE_SUBSCRIPTION_ID` | remediative | Azure subscription ID |
| `AZURE_CLIENT_ID` | remediative | Service principal App ID |
| `AZURE_CLIENT_SECRET` | remediative | Service principal secret |
| `AZURE_TENANT_ID` | remediative | Azure AD tenant ID |
| `TEAMS_WEBHOOK_URL` | preventive | Teams incoming webhook URL |

The service principal requires **Reader** access to query Azure Resource Graph and **Contributor** access on target storage accounts for remediation.

### Python Dependencies

```
pip install -r requirements.txt
```

---

## Pipeline 1 — Preventive (`Jenkinsfile.preventive`)

Runs on every pull request or push to a protected branch. Demonstrates five layered compliance scenarios end-to-end.

| Scenario | What it demonstrates | Gate |
|----------|---------------------|------|
| 1 — Perfect PR | Fully compliant code travels through every stage and deploys | All pass → apply |
| 2 — Insecure Cloud Defaults | tfsec + Checkov catch encryption-off, public access, etc. with exact file:line | CRITICAL/HIGH → fail fast |
| 3 — VM Size Policy | OPA blocks oversized VMs in dev/staging regardless of security status | Cost violation → blocked |
| 4 — Missing Tags | OPA rejects resources missing `Environment`, `CostCenter`, or `ManagedBy` | Governance violation → blocked |
| 5 — Advise & Notify | MEDIUM/LOW findings deploy successfully but fire a Teams advisory message | Non-blocking warning |

**Stages:**

1. **Checkout** — pull code from SCM
2. **IaC Static Analysis** — tfsec + Checkov run in parallel; both write JSON output
3. **Evaluate Security Findings** — CRITICAL/HIGH block the build with file:line detail; MEDIUM/LOW queued as warnings
4. **Terraform Plan** — generates `tfplan.json` and `env_config.json` for OPA plan-based checks
5. **OPA Policy Checks** — three checks in parallel: CIS Compliance, VM Size Policy, Mandatory Tags
6. **Terraform Apply** — reuses the pre-validated plan; only reached if every check above passes
7. **Notify Warnings** — posts advisory findings to Teams (MessageCard); conditional on warnings existing; build stays GREEN

Set `ENVIRONMENT = 'dev' | 'staging' | 'prod'` in the pipeline env block to control which VM-size allowlist OPA enforces.

---

## Pipeline 2 — Remediative (`Jenkinsfile.remediative`)

Runs on a schedule (or on demand) against live Azure resources. Queries Azure Resource Graph for CIS 3.6 drift (public blob access), generates fix commands, and applies them automatically.

**Stages:**

1. **Initialize Workspace** — creates `outputs/` directory, clears previous run artefacts
2. **Detect Infrastructure Drift** — logs in via service principal; Azure Resource Graph query for `allowBlobPublicAccess == true`; results written to `outputs/drift_results.json`
3. **CIS Benchmark Mapping** — `cis_mapper.py` reads the drift results and writes `outputs/remediate_drift.bat` (only when non-compliant resources are found)
4. **Remediate & Notify** — executes the `.bat` if it exists; each command runs `az storage account update --allow-blob-public-access false`; prints "COMPLIANCE VERIFIED" if no drift was found

---

## OPA Policies

### `cis_azure.rego` — CIS Azure Benchmark (input: `tfsec_results.json`)

Evaluates tfsec findings against five CIS rules. Resources can be whitelisted in `exception_list` to suppress known-approved violations:

```rego
exception_list := {"resource_name_here"}
```

### `vm_size.rego` — VM Size Enforcement (input: `tfplan.json` + `env_config.json`)

Blocks VM deployments that use a size not on the environment's allowlist:

| Environment | Permitted sizes |
|-------------|----------------|
| `dev` | B1s, B2s, B2ms, B4ms, D2s_v3, D4s_v3 |
| `staging` | B2s, B4ms, D2s_v3, D4s_v3, D8s_v3 |
| `prod` | D2–D16s_v3, E4–E16s_v3 |

Covers both `azurerm_linux/windows_virtual_machine` (field: `size`) and legacy `azurerm_virtual_machine` (field: `vm_size`).

### `tags.rego` — Mandatory Tag Governance (input: `tfplan.json`)

Every tracked resource must carry all three mandatory tags or the deployment is blocked:

| Tag | Purpose |
|-----|---------|
| `Environment` | Traceability (dev / staging / prod) |
| `CostCenter` | Financial attribution |
| `ManagedBy` | Operational ownership |

Tracked types: `azurerm_resource_group`, `azurerm_storage_account`, VMs, Key Vault, SQL Server, App Service.

---

## Terraform Test Resources

The `terraform/` directory contains two intentionally contrasting storage accounts for validating the preventive pipeline end-to-end:

- **`storage_pass.tf`** — fully CIS-compliant: TLS 1.2, public access disabled, network default Deny, infrastructure encryption enabled, versioning and soft delete active.
- **`storage_fail.tf`** — intentionally violates CIS 3.6 (public blob access enabled, no network rules). Used to verify the pipeline correctly blocks non-compliant deployments.

---

## Outputs

| File | Created By | Contents |
|------|-----------|---------|
| `tfsec_results.json` | tfsec (Stage 2, preventive) | Static analysis findings with AVD rule IDs and severity |
| `checkov_results.json` | Checkov (Stage 2, preventive) | Additional IaC scan findings |
| `warnings.txt` | Evaluate stage (Stage 3, preventive) | MEDIUM/LOW findings for Slack notification |
| `env_config.json` | Terraform Plan stage (Stage 4, preventive) | `{"config":{"environment":"dev"}}` — OPA environment context |
| `tfplan.json` | Terraform (Stage 4, preventive) | Full Terraform plan in JSON — OPA VM size + tags input |
| `teams_payload.json` | Notify Warnings stage (Stage 7, preventive) | Teams MessageCard payload |
| `outputs/drift_results.json` | Azure CLI (Stage 2, remediative) | Resource Graph query results |
| `outputs/remediate_drift.bat` | `cis_mapper.py` (Stage 3, remediative) | Azure CLI remediation commands — only created when drift is found |
