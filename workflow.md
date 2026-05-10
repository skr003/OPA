# Pipeline Workflows

---

## Pipeline 1 — Preventive Controls

**Trigger:** Pull request or push to a protected branch  
**Goal:** OPA enforces cost and tag governance before deployment; tfsec and Checkov generate static analysis artifacts for review

```
Developer pushes Terraform code
          │
          ▼
┌──────────────────────────┐
│  Stage 1: Checkout Code  │
│  Pull code from SCM      │
└──────────┬───────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│  Stage 2: Terraform Init & Validate                          │
│                                                             │
│  terraform init -upgrade -input=false                       │
│  terraform validate                                         │
│                                                             │
│  Wrapped in catchError — build marked UNSTABLE if provider  │
│  download fails; all subsequent stages still execute.       │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│  Stage 3: Layer A — Static Analysis (Checkov / tfsec)        │
│  tfsec and Checkov run in PARALLEL                          │
│                                                             │
│  ┌──────────────────────────┐  ┌──────────────────────────┐ │
│  │ tfsec terraform          │  │ checkov -d terraform     │ │
│  │   --format json          │  │   --output json          │ │
│  │   --include-passed       │  │   --soft-fail            │ │
│  │ > tfsec_results.json     │  │ > checkov_results.json   │ │
│  └──────────────────────────┘  └──────────────────────────┘ │
│                                                             │
│  Findings written as artifacts for review only.             │
│  Neither tool blocks or marks the build here.               │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│  Stage 4: Terraform Plan generation                         │
│                                                             │
│  Writes env_config.json:                                    │
│    {"config": {"environment": "dev|staging|prod"}}          │
│                                                             │
│  terraform plan -out=tfplan -input=false                    │
│  terraform show -json tfplan > tfplan.json                  │
│                                                             │
│  tfplan.json is the input for OPA cost + tags checks        │
│  Wrapped in catchError — OPA still runs if Azure creds      │
│  are absent (tfplan.json guard skips the OPA sub-stages)    │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Stage 5: Layer B — OPA Policy Validation                            │
│  Two checks run in PARALLEL                                         │
│                                                                     │
│  ┌────────────────────────────────┐  ┌────────────────────────────┐  │
│  │ VM Size Policy                 │  │ Mandatory Tags             │  │
│  │                                │  │                            │  │
│  │ -i tfplan.json                 │  │ -i tfplan.json             │  │
│  │ -d policies/vm_size.rego       │  │ -d policies/tags.rego      │  │
│  │ -d env_config.json             │  │                            │  │
│  │                                │  │ data.policy.tags.deny      │  │
│  │ data.policy.vm_size.deny       │  │                            │  │
│  │                                │  │ Checks Environment,        │  │
│  │ Checks VM size vs              │  │ CostCenter, ManagedBy      │  │
│  │ per-env allowlist              │  │ on all taggable resources  │  │
│  │ Writes: opa_vm_result.json     │  │ Writes: opa_tags_result.json│ │
│  └──────────────┬─────────────────┘  └────────────────┬───────────┘  │
└─────────────────┼──────────────────────────────────────┼─────────────┘
                  │  any deny set contains "VIOLATION"   │
                  ▼                                      ▼
   ┌──────────────────────────────┐  ┌────────────────────────────────┐
   │ OPA COST FAIL                │  │ OPA TAGS FAIL                  │
   │                              │  │                                │
   │ VM size not on allowed list  │  │ Missing mandatory tag:         │
   │ for this environment.        │  │ Environment, CostCenter, or    │
   │ Build marked UNSTABLE.       │  │ ManagedBy.                     │
   │ Deployment blocked.          │  │ Build marked UNSTABLE. Blocked.│
   └──────────────────────────────┘  └────────────────────────────────┘

           │  all deny sets empty
           ▼
┌─────────────────────────────────────────────────────────────┐
│  Stage 6: Terraform Apply (Deploy)                          │
│                                                             │
│  when { currentBuild.currentResult == 'SUCCESS' }           │
│  terraform apply -auto-approve -input=false tfplan          │
│                                                             │
│  Reuses the pre-validated plan — no drift possible          │
│  between the policy check and the apply.                    │
│  Skipped automatically if any unstable() was called above.  │
└─────────────────────────────────────────────────────────────┘
```

### OPA VM Size Allowlist (Stage 5 — VM Size Policy)

| Environment | Permitted sizes |
|-------------|----------------|
| `dev` | B1s, B2s, B2ms, B4ms, D2s_v3, D4s_v3 |
| `staging` | B2s, B4ms, D2s_v3, D4s_v3, D8s_v3 |
| `prod` | D2–D16s_v3, E4–E16s_v3 |

> **Note:** CIS Azure Benchmark checks (`policies/cis_azure.rego`) run in the **Remediative Pipeline** against a fresh tfsec scan of the checked-out Terraform. tfsec and Checkov findings from Layer A are artifacts for review and do not block this pipeline.

---

## Pipeline 2 — Remediative Controls

**Trigger:** Scheduled (cron) or manual build  
**Goal:** Query live Azure resources, detect drift from CIS baseline, auto-fix safe violations, and alert on risky ones

```
Scheduled / Manual Trigger
          │
          ▼
┌──────────────────────────────────────────────┐
│  Stage 1: Checkout Code                      │
│                                              │
│  checkout scm                                │
│  mkdir outputs\  (if not exists)             │
│  del /f /q outputs\*.json                    │
│  del /f /q outputs\*.bat                     │
│  → clean workspace ready for this run        │
└──────────────────┬───────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────┐
│  Stage 2: Environment Setup                                  │
│                                                              │
│  az login --service-principal                                │
│     -u %AZURE_CLIENT_ID%                                     │
│     -p %AZURE_CLIENT_SECRET%                                 │
│     --tenant %AZURE_TENANT_ID%                               │
│  az account set --subscription %ARM_SUBSCRIPTION_ID%         │
│  az account show  (verify active subscription)               │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Stage 3: Query Azure Resource Graph                                 │
│                                                                      │
│  python scripts/query_azure.py                                       │
│  Fires all 4 ARG queries in parallel and saves raw results:          │
│                                                                      │
│  ┌──────────────────────┐  ┌──────────────────────────┐              │
│  │ NSG inbound rules    │  │ Storage accounts          │              │
│  │ → outputs/           │  │ (HTTPS + public blob)     │              │
│  │   nsg_raw.json       │  │ → outputs/                │              │
│  └──────────────────────┘  │   storage_raw.json        │              │
│  ┌──────────────────────┐  └──────────────────────────┘              │
│  │ VM hardware profiles │  ┌──────────────────────────┐              │
│  │ → outputs/           │  │ IAM role assignments      │              │
│  │   scaling_raw.json   │  │ + activity log (24 h)     │              │
│  └──────────────────────┘  │ → outputs/iam_raw.json   │              │
│                             └──────────────────────────┘              │
│  Archives: outputs/*_raw.json                                        │
└──────────────────────────────────────┬───────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Stage 4: Execute Python Audit Engine (CIS Mapping)                  │
│                                                                      │
│  -- Scenario 1-4 drift detection --                                  │
│  python detect_nsg_drift.py                                          │
│    Reads: nsg_raw.json   CIS 6.1/6.2 (open SSH/RDP to internet)     │
│    Writes: outputs/nsg_drift.json + outputs/nsg_remediate.bat        │
│                                                                      │
│  python detect_storage_drift.py                                      │
│    Reads: storage_raw.json   CIS 3.15/3.5 (HTTPS-only, public blob) │
│    Writes: outputs/storage_drift.json + outputs/storage_remediate.bat│
│                                                                      │
│  python detect_scaling_drift.py                                      │
│    Reads: scaling_raw.json   Cost Governance (VM vs IaC baseline)    │
│    Writes: outputs/scaling_drift.json + outputs/scaling_remediate.bat│
│                                                                      │
│  python detect_iam_drift.py                                          │
│    Reads: iam_raw.json   CIS 1.1 (unauthorized high-priv roles)      │
│    Writes: outputs/iam_drift.json + outputs/iam_remediate.bat        │
│                                                                      │
│  -- CIS Azure Benchmark (IaC + live infra) --                        │
│  tfsec terraform --format json --include-passed                      │
│    > outputs/tfsec_scan.json                                         │
│  opa eval -i outputs/tfsec_scan.json -d policies/cis_azure.rego      │
│    "data.cis.azure.deny" → outputs/opa_cis_result.json               │
│  (build marked UNSTABLE if violations found)                         │
│                                                                      │
│  -- Pre-Remediation Compliance Dashboard --                          │
│  python scripts/generate_dashboard.py pre_remediation                │
│    → outputs/compliance_dashboard_pre_remediation.json               │
│    → outputs/compliance_dashboard_latest.json                        │
│                                                                      │
│  Console prints per-scenario DRIFTED / COMPLIANT summary             │
│  Archives: outputs/*_drift.json + compliance_dashboard_pre_*.json    │
└──────────────────────────────────────┬───────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Stage 5: Generate Remediation Scripts                               │
│                                                                      │
│  Prints preview of each .bat file to Jenkins console:                │
│    nsg_remediate.bat     — Scenario 1: set NSG rule to Deny          │
│    storage_remediate.bat — Scenario 2: HTTPS-only + public blob off  │
│    scaling_remediate.bat — Scenario 3: deallocate, resize, start     │
│    iam_remediate.bat     — Scenario 4: az role assignment delete     │
│                                                                      │
│  (Script printed only if drift was detected; otherwise logged as     │
│   "no drift detected, script not generated".)                        │
│  Archives: outputs/*.bat + outputs/*.json                            │
└──────────────────────────────────────┬───────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Stage 6: Trigger Self-Healing & Alerts                              │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │ SCENARIO 1 — NSG Open Ports (CIS 6.1/6.2)                    │    │
│  │ nsg_drift.json → drifted=true?                               │    │
│  │   YES → print nsg_remediate.bat preview                      │    │
│  │         call outputs\nsg_remediate.bat  (AUTO-FIX)           │    │
│  │         az network nsg rule update --access Deny             │    │
│  │   NO  → "NSG: COMPLIANT — no open ports found."              │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │ SCENARIO 2 — Storage HTTPS Drift (CIS 3.15/3.5)              │    │
│  │ storage_drift.json → drifted=true?                           │    │
│  │   YES → print storage_drift.json                             │    │
│  │         Jenkins input() — 30 min approval gate               │    │
│  │         APPROVED  → call outputs\storage_remediate.bat       │    │
│  │         TIMEOUT   → drift logged, persists until next run    │    │
│  │   NO  → "Storage: COMPLIANT — all accounts use HTTPS-only."  │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │ SCENARIO 3 — VM Scaling (Cost Governance)                    │    │
│  │ scaling_drift.json → drifted=true?                           │    │
│  │   YES → print scaling_drift.json                             │    │
│  │         unstable("Cost drift: DevOps review required")       │    │
│  │         Revert script at outputs/scaling_remediate.bat ready │    │
│  │   NO  → "Scaling: COMPLIANT — all VMs within approved sizes."│    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │ SCENARIO 4 — IAM Privilege Escalation (CIS 1.1)              │    │
│  │ iam_drift.json → drifted=true?                               │    │
│  │   YES → print iam_drift.json                                 │    │
│  │         unstable("IAM escalation: security team alerted")    │    │
│  │         Removal script at outputs/iam_remediate.bat ready    │    │
│  │   NO  → "IAM: COMPLIANT — no unauthorized assignments found."│    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  -- Post-Remediation Verification --                                 │
│  Re-run all 4 detect_*.py scripts against live Azure                 │
│  python generate_dashboard.py post_remediation                       │
│    → outputs/compliance_dashboard_post_remediation.json              │
│  Archives: compliance_dashboard_post_remediation.json                │
│                                                                      │
│  -- Teams Notification --                                            │
│  Builds MessageCard with all 4 scenario outcomes                     │
│  curl POST → TEAMS_WEBHOOK_URL                                       │
│  GREEN  (SUCCESS)  = all drift remediated                            │
│  ORANGE (UNSTABLE) = partial remediation, manual review required     │
│  RED    (FAILURE)  = pipeline error                                  │
└──────────────────────────────────────────────────────────────────────┘
```

### Remediation Decision Matrix

| Scenario | CIS Control | Drift Detected | Action | Build Result |
|----------|------------|---------------|--------|--------------|
| 1 — NSG open ports | 6.1 / 6.2 | Port 22/3389 open to internet | Auto-fix: set rule to Deny | SUCCESS |
| 2 — Storage HTTPS | 3.15 / 3.5 | HTTPS-only off or public blob on | Manual approval gate (30 min timeout) | SUCCESS if approved |
| 3 — VM scaling | Cost Gov. | VM size outside IaC baseline | Notify DevOps, revert script generated | UNSTABLE |
| 4 — IAM tampering | 1.1 | Unauthorized Owner/Contributor at sub scope | Alert security team, removal script generated | UNSTABLE |

### CIS Rule Evaluation (cis_azure.rego — Stage 4 of Remediative Pipeline)

Each tfsec result is evaluated against five rules in `policies/cis_azure.rego`:

| tfsec ID | CIS # | Violation Message Produced |
|----------|-------|---------------------------|
| AVD-AZU-0010 | 3.1 | "CIS 3.1 VIOLATION: Secure transfer (HTTPS) is disabled on '{resource}'" |
| AVD-AZU-0012 | 3.6 | "CIS 3.6 VIOLATION: Public blob access is enabled on '{resource}'" |
| AVD-AZU-0011 | 3.7 | "CIS 3.7 VIOLATION: Storage account '{resource}' does not deny network traffic by default" |
| AVD-AZU-0013 | 3.10 | "CIS 3.10 VIOLATION: TLS version is outdated on '{resource}'. Must be 1.2" |
| AVD-AZU-0014 | 3.2 | "CIS 3.2 VIOLATION: Infrastructure encryption is disabled on '{resource}'" |

### Data Flow (Remediative Pipeline)

```
Azure Resource Graph (4 parallel ARG queries)
        │
        │  raw JSON (resource snapshots)
        ▼
outputs/nsg_raw.json       outputs/storage_raw.json
outputs/scaling_raw.json   outputs/iam_raw.json
        │
        │  read by detect_*.py scripts
        ▼
outputs/nsg_drift.json      → outputs/nsg_remediate.bat
outputs/storage_drift.json  → outputs/storage_remediate.bat
outputs/scaling_drift.json  → outputs/scaling_remediate.bat
outputs/iam_drift.json      → outputs/iam_remediate.bat
        │
        │  aggregated by generate_dashboard.py
        ▼
outputs/compliance_dashboard_pre_remediation.json
        │
        │  scenario actions: auto-fix / approval gate / alert
        ▼
outputs/compliance_dashboard_post_remediation.json
        │
        │  Teams notification (before/after compliance scores)
        ▼
TEAMS_WEBHOOK_URL
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
                    │  tfsec + Checkov → scan artifacts         │
                    │  Terraform plan → OPA (cost, tags)        │
                    └──────┬─────────────────────┬─────────────┘
                    Passes │                     │ Fails (UNSTABLE)
                           │                     │
              ┌────────────▼──┐       ┌──────────▼─────────────┐
              │  Terraform    │       │  Deployment blocked     │
              │  Apply        │       │  OPA: VM size cost     │
              │               │       │  OPA: mandatory tags   │
              └────────┬──────┘       └────────────────────────┘
                       │
              ┌────────▼──────────────────────────────┐
              │  Live Azure Environment                │
              │                                       │
              │  (Manual changes / config drift        │
              │   may re-introduce violations)         │
              └────────┬──────────────────────────────┘
                       │
              ┌────────▼──────────────────────────────────────────────┐
              │  Remediative Pipeline (scheduled / manual)             │
              │                                                        │
              │  query_azure.py → 4 raw ARG snapshots                 │
              │  detect_*.py   → 4 drift reports + remediation scripts │
              │  tfsec + OPA   → CIS Benchmark check                  │
              │  generate_dashboard.py → pre-remediation compliance %  │
              │                                                        │
              │  Scenario 1 (NSG)     → AUTO-FIX applied              │
              │  Scenario 2 (Storage) → MANUAL APPROVAL GATE          │
              │  Scenario 3 (Scaling) → ALERT DEVOPS (UNSTABLE)       │
              │  Scenario 4 (IAM)     → ALERT SECURITY (UNSTABLE)     │
              │                                                        │
              │  generate_dashboard.py → post-remediation compliance % │
              │  Teams card with before/after compliance scores        │
              └────────────────────────────────────────────────────────┘
```

---

## Key Files Referenced by Each Stage

| Stage | Pipeline | Files Read | Files Written |
|-------|----------|------------|---------------|
| Layer A — Static Analysis | Preventive | `terraform/*.tf` | `tfsec_results.json`, `checkov_results.json` |
| Terraform Plan generation | Preventive | `terraform/*.tf` | `env_config.json`, `tfplan.json` |
| OPA — VM Size | Preventive | `tfplan.json`, `policies/vm_size.rego`, `env_config.json` | `opa_vm_result.json` |
| OPA — Tags | Preventive | `tfplan.json`, `policies/tags.rego` | `opa_tags_result.json` |
| Terraform Apply | Preventive | `terraform/tfplan` | Azure resources |
| Checkout Code | Remediative | — | `outputs/` directory (cleaned) |
| Environment Setup | Remediative | — | Azure auth session |
| Query ARG | Remediative | Azure live state | `outputs/*_raw.json` |
| Audit Engine | Remediative | `outputs/*_raw.json`, `terraform/*.tf` | `outputs/*_drift.json`, `outputs/*_remediate.bat`, `outputs/tfsec_scan.json`, `outputs/opa_cis_result.json`, `outputs/compliance_dashboard_pre_remediation.json` |
| Self-Healing & Alerts | Remediative | `outputs/*_drift.json`, `outputs/*_remediate.bat` | Azure resource properties, `outputs/compliance_dashboard_post_remediation.json`, `outputs/teams_payload.json` |
