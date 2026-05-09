# Pipeline Workflows

---

## Pipeline 1 — Preventive Controls

**Trigger:** Pull request or push to a protected branch  
**Goal:** Five layered gates that enforce security, cost, and governance policy before any resource reaches Azure

```
Developer pushes Terraform code
          │
          ▼
┌──────────────────────────┐
│  Stage 1: Checkout       │
│  Pull code from SCM      │
└──────────┬───────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│  Stage 2: IaC Static Analysis  [SCENARIO 2]                 │
│  tfsec and Checkov run in PARALLEL                          │
│                                                             │
│  ┌──────────────────────────┐  ┌──────────────────────────┐ │
│  │ tfsec terraform          │  │ checkov -d terraform     │ │
│  │   --format json          │  │   --output json          │ │
│  │   --include-passed       │  │   --soft-fail            │ │
│  │ > tfsec_results.json     │  │ > checkov_results.json   │ │
│  └──────────────────────────┘  └──────────────────────────┘ │
└─────────────────────────────────────────┬───────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Stage 3: Evaluate Security Findings  [SCENARIOS 2 + 5]             │
│                                                                     │
│  Parse tfsec_results.json + checkov_results.json                    │
│                                                                     │
│    CRITICAL / HIGH  ──→  blocking[]     MEDIUM / LOW  ──→  warnings[] │
│                                                                     │
│  Writes warnings.txt (consumed by Slack notification in Stage 7)    │
└──────────┬────────────────────────────────────────┬────────────────┘
           │  blocking = []                         │  blocking has entries
           │                                        ▼
           │                         ┌──────────────────────────────┐
           │                         │  PIPELINE FAILS [SCENARIO 2] │
           │                         │                              │
           │                         │  rule ID | severity          │
           │                         │  description                 │
           │                         │  filename : line number      │
           │                         │  Deployment blocked.         │
           │                         └──────────────────────────────┘
           ▼
┌─────────────────────────────────────────────────────────────┐
│  Stage 4: Terraform Plan                                    │
│                                                             │
│  Writes env_config.json:                                    │
│    {"config": {"environment": "dev|staging|prod"}}          │
│                                                             │
│  terraform init -upgrade                                    │
│  terraform plan -out=tfplan                                 │
│  terraform show -json tfplan > tfplan.json                  │
│                                                             │
│  tfplan.json is the input for the OPA cost + tags checks    │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Stage 5: OPA Policy Checks  [SCENARIOS 2, 3, 4]                    │
│  Three checks run in PARALLEL                                       │
│                                                                     │
│  ┌───────────────────────┐ ┌────────────────────────┐ ┌──────────┐  │
│  │ CIS Compliance        │ │ VM Size Policy         │ │ Mandatory│  │
│  │ [Scenario 2]          │ │ [Scenario 3]           │ │ Tags     │  │
│  │                       │ │                        │ │ [Scen. 4]│  │
│  │ -i tfsec_results.json │ │ -i tfplan.json         │ │          │  │
│  │ -d cis_azure.rego     │ │ -d vm_size.rego        │ │ -i tfplan│  │
│  │                       │ │ -d env_config.json     │ │   .json  │  │
│  │ data.cis.azure.deny   │ │                        │ │ -d tags  │  │
│  │                       │ │ data.policy.vm_size    │ │   .rego  │  │
│  │ Checks AVD rule IDs   │ │   .deny                │ │          │  │
│  │ against exception     │ │                        │ │ data     │  │
│  │ list; 5 CIS rules     │ │ Checks VM size vs      │ │ .policy  │  │
│  └──────────┬────────────┘ │ per-env allowlist      │ │ .tags    │  │
│             │              └──────────┬─────────────┘ │ .deny    │  │
│             │                         │               └─────┬────┘  │
└─────────────┼─────────────────────────┼─────────────────────┼───────┘
              │  any deny set           │                     │
              │  contains "VIOLATION"   │                     │
              ▼                         ▼                     ▼
   ┌──────────────────┐  ┌──────────────────────┐  ┌────────────────────┐
   │ OPA CIS FAIL     │  │ OPA COST FAIL        │  │ OPA TAGS FAIL      │
   │ [Scenario 2]     │  │ [Scenario 3]         │  │ [Scenario 4]       │
   │                  │  │                      │  │                    │
   │ Security policy  │  │ VM size not on       │  │ Missing mandatory  │
   │ violation.       │  │ allowed list for     │  │ tag: Environment,  │
   │ Deployment       │  │ this environment.    │  │ CostCenter, or     │
   │ blocked.         │  │ Deployment blocked.  │  │ ManagedBy.         │
   └──────────────────┘  └──────────────────────┘  └────────────────────┘

           │  all deny sets empty
           ▼
┌─────────────────────────────────────────────────────────────┐
│  Stage 6: Terraform Apply  [SCENARIO 1 complete]            │
│                                                             │
│  terraform apply -auto-approve tfplan                       │
│                                                             │
│  Reuses the pre-validated plan — no drift possible          │
│  between the policy check and the apply.                    │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Stage 7: Notify Warnings  [SCENARIO 5]                             │
│  (runs only when HAS_WARNINGS = true)                               │
│                                                                     │
│  Reads warnings.txt → builds Slack JSON payload                     │
│  curl POST → SLACK_WEBHOOK_URL                                      │
│                                                                     │
│  Build stays GREEN. Team triages at their own pace.                 │
└─────────────────────────────────────────────────────────────────────┘
```

### Severity Routing (Stage 3)

| Severity | Source | Outcome |
|----------|--------|---------|
| CRITICAL | tfsec or Checkov | Blocks pipeline — `rule_id \| description \| file:line` printed |
| HIGH | tfsec or Checkov | Blocks pipeline — `rule_id \| description \| file:line` printed |
| MEDIUM | tfsec or Checkov | Non-blocking — queued in `warnings.txt` for Slack advisory |
| LOW | tfsec or Checkov | Non-blocking — queued in `warnings.txt` for Slack advisory |

### CIS Rule Evaluation (Stage 5 — CIS Compliance check)

Each tfsec result is evaluated against five rules in `policies/cis_azure.rego`:

| tfsec ID | CIS # | Violation Message Produced |
|----------|-------|---------------------------|
| AVD-AZU-0010 | 3.1 | "CIS 3.1 VIOLATION: Secure transfer (HTTPS) is disabled on '{resource}'" |
| AVD-AZU-0012 | 3.6 | "CIS 3.6 VIOLATION: Public blob access is enabled on '{resource}'" |
| AVD-AZU-0011 | 3.7 | "CIS 3.7 VIOLATION: Storage account '{resource}' does not deny network traffic by default" |
| AVD-AZU-0013 | 3.10 | "CIS 3.10 VIOLATION: TLS version is outdated on '{resource}'. Must be 1.2" |
| AVD-AZU-0014 | 3.2 | "CIS 3.2 VIOLATION: Infrastructure encryption is disabled on '{resource}'" |

---

## Pipeline 2 — Remediative Controls

**Trigger:** Scheduled (cron) or manual build  
**Goal:** Find live Azure resources that have drifted from CIS compliance and auto-fix them

```
Scheduled / Manual Trigger
          │
          ▼
┌──────────────────────────────────────────────┐
│  Stage 1: Initialize Workspace               │
│                                              │
│  mkdir outputs\   (if not exists)            │
│  Delete any previous drift_results.json      │
│  Delete any previous remediate_drift.bat     │
└──────────────────┬───────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────┐
│  Stage 2: Detect Infrastructure Drift                        │
│                                                              │
│  az login --service-principal                                │
│     -u %AZURE_CLIENT_ID%                                     │
│     -p %AZURE_CLIENT_SECRET%                                 │
│     --tenant %AZURE_TENANT_ID%                               │
│                                                              │
│  az graph query -q "                                         │
│    Resources                                                 │
│    | where type =~ 'Microsoft.Storage/storageAccounts'       │
│    | where properties.allowBlobPublicAccess == true          │
│    | project id, name, resourceGroup"                        │
│  > outputs/drift_results.json                                │
│                                                              │
│  Targets CIS 3.6 — public blob access violation              │
└──────────────────┬──────────────────┬───────────────────────┘
                   │                  │
           No results          Results found
                   │                  │
                   ▼                  ▼
     ┌──────────────────────┐  ┌──────────────────────────────────┐
     │  Stage 3: Mapping    │  │  Stage 3: CIS Benchmark Mapping  │
     │                      │  │                                  │
     │  python cis_mapper   │  │  python cis_mapper.py            │
     │  No resources found  │  │                                  │
     │  → NO .bat written   │  │  Reads: drift_results.json       │
     └──────────┬───────────┘  │  For each non-compliant resource:│
                │               │    az storage account update     │
                ▼               │      --name {name}               │
     ┌──────────────────────┐   │      --resource-group {rg}       │
     │  Stage 4:            │   │      --allow-blob-public-access  │
     │  fileExists(.bat)?   │   │        false                     │
     │       → NO           │   │  Writes: remediate_drift.bat     │
     │                      │   └──────────────────┬───────────────┘
     │  "COMPLIANCE         │                      │
     │   VERIFIED"          │                      ▼
     │  No action taken     │   ┌──────────────────────────────────┐
     └──────────────────────┘   │  Stage 4: Remediate & Notify     │
                                │                                  │
                                │  fileExists(.bat)? → YES         │
                                │  Execute remediate_drift.bat     │
                                │  (one az CLI call per resource)  │
                                │                                  │
                                │  Each call sets:                 │
                                │  allowBlobPublicAccess = false   │
                                └──────────────────┬───────────────┘
                                                   │
                                                   ▼
                                ┌──────────────────────────────────┐
                                │  Post: Confirm Compliance        │
                                │  Log remediation summary         │
                                └──────────────────────────────────┘
```

### Data Flow (Remediative Pipeline)

```
Azure Resource Graph
        │
        │  JSON (resource list)
        ▼
outputs/drift_results.json
        │
        │  read by
        ▼
scripts/cis_mapper.py
        │
        │  generates (only when drift found)
        ▼
outputs/remediate_drift.bat
        │
        │  executed by Jenkins
        ▼
Azure Storage Account(s)
  allowBlobPublicAccess = false
```

---

## End-to-End Compliance Control Flow

```
                    ┌────────────────────────────┐
                    │  Developer writes Terraform │
                    └─────────────┬──────────────┘
                                  │
                    ┌─────────────▼────────────────────────────┐
                    │  Preventive Pipeline                      │
                    │  tfsec + Checkov → severity gate          │
                    │  Terraform plan → OPA (CIS, cost, tags)   │
                    └──────┬─────────────────────┬─────────────┘
                    Passes │                     │ Fails
                           │                     │
              ┌────────────▼──┐       ┌──────────▼─────────────┐
              │  Terraform    │       │  Block deployment       │
              │  Apply +      │       │  Scenario 2: security  │
              │  Slack notify │       │  Scenario 3: VM cost   │
              │  if warnings  │       │  Scenario 4: tags      │
              └────────┬──────┘       └────────────────────────┘
                       │
              ┌────────▼──────────────────────────────┐
              │  Live Azure Environment                │
              │                                       │
              │  (Manual changes / config drift        │
              │   may re-introduce violations)         │
              └────────┬──────────────────────────────┘
                       │
              ┌────────▼──────────────────────────────┐
              │  Remediative Pipeline (scheduled)      │
              │  Azure Resource Graph → detect drift   │
              │  cis_mapper.py → generate fix          │
              │  az CLI → apply fix                    │
              └────────────────────────────────────────┘
```

---

## Key Files Referenced by Each Stage

| Stage | Pipeline | Files Read | Files Written |
|-------|----------|------------|---------------|
| IaC Static Analysis | Preventive | `terraform/*.tf` | `tfsec_results.json`, `checkov_results.json` |
| Evaluate Findings | Preventive | `tfsec_results.json`, `checkov_results.json` | `warnings.txt` |
| Terraform Plan | Preventive | `terraform/*.tf` | `env_config.json`, `tfplan.json` |
| OPA — CIS | Preventive | `tfsec_results.json`, `policies/cis_azure.rego` | — |
| OPA — VM Size | Preventive | `tfplan.json`, `policies/vm_size.rego`, `env_config.json` | — |
| OPA — Tags | Preventive | `tfplan.json`, `policies/tags.rego` | — |
| Terraform Apply | Preventive | `terraform/tfplan` | Azure resources |
| Notify Warnings | Preventive | `warnings.txt` | `slack_payload.json` |
| Init Workspace | Remediative | — | `outputs/` directory |
| Drift Detection | Remediative | Azure live state | `outputs/drift_results.json` |
| CIS Mapping | Remediative | `outputs/drift_results.json` | `outputs/remediate_drift.bat` (only if drift found) |
| Remediation | Remediative | `outputs/remediate_drift.bat` | Azure resource properties |
