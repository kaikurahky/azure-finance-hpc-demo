# Azure Deployment Plan

> **Status:** Deployed

Generated: 2026-08-19T17:10:12+09:00

---

## 1. Project Overview

**Goal:** Deploy the existing Always On Azure Batch implementation so the demo can select either the existing 0-to-10-node autoscale pool or a new fixed 10-node Low Priority pool.

**Path:** Add Components

**Workspace:** `/home/hikurais/azure-finance-hpc-demo`

---

## 2. Requirements

| Attribute | Value |
|-----------|-------|
| Classification | Development / Demo |
| Scale | Small |
| Budget | Performance-oriented for the Always On demo mode |
| Subscription | `ME-MngEnvMCAP037207-hikurais-1` (`02822f3b-51ae-46e7-b446-9d74b942e87c`) — confirmed by user |
| Location | Japan East (`japaneast`) — confirmed by user |
| Resource group | `rg-finhpc-dev-28e5` |
| Availability requirement | Keep 10 Low Priority `Standard_F8s_v2` nodes running in the Always On pool |
| Compatibility requirement | Preserve the existing autoscale pool with a 0-to-10-node range |
| Cost acknowledgement | Always On nodes continue to incur charges and consume quota while idle |

---

## 3. Components Detected

| Component | Type | Technology | Path |
|-----------|------|------------|------|
| Web UI | Frontend | React 19, TypeScript, Vite | `frontend/` |
| Simulation API | API | Python, FastAPI | `backend/` |
| Application image | Container | Multi-stage Docker build | `Dockerfile` |
| Azure infrastructure | Infrastructure | Subscription-scope Bicep | `infra/` |
| Autoscale compute | Azure Batch pool | `Standard_F8s_v2`, Low Priority, 0–10 nodes | Existing `pool-finhpc-dev-28e5` |
| Always On compute | Azure Batch pool | `Standard_F8s_v2`, Low Priority, fixed 10 nodes | New `pool-finhpc-alwayson-28e5` |

---

## 4. Recipe Selection

**Selected:** Targeted resource-group-scope Bicep with Azure CLI

**Rationale:** The project already uses Bicep, ACR Tasks for image builds, and direct Azure CLI deployments. The deployment uses `infra/always-on-update.bicep`, which reuses the existing Batch and Container App modules but limits the update to the Batch account, its two pools, and the Container App. This avoids reapplying unrelated services from the full subscription template.

---

## 5. Architecture

**Stack:** Azure Container Apps + Azure Container Registry + Azure Batch

### Service Mapping

| Component | Azure Service | SKU / Configuration |
|-----------|---------------|---------------------|
| Web UI and API | Azure Container Apps | Existing consumption environment, minimum replicas 0 |
| Container image | Azure Container Registry | Existing registry `crfinhpcdev28e5` |
| Autoscale simulations | Azure Batch | Existing Low Priority `Standard_F8s_v2`, 0–10 nodes |
| Always On simulations | Azure Batch | New Low Priority `Standard_F8s_v2`, fixed 10 nodes |

### Supporting Services

| Service | Purpose |
|---------|---------|
| Managed Identity | Container App authentication to ACR and Azure Batch |
| Application Insights | Application telemetry |
| Log Analytics | Centralized logs |
| Key Vault | Existing secret storage |
| Storage Account | Existing application storage |

The UI sends `pool_mode` with each Azure Batch request. The API maps `autoscale` to `pool-finhpc-dev-28e5` and `always-on` to `pool-finhpc-alwayson-28e5`. AI-generated second runs inherit the first run's pool mode.

---

## 6. Provisioning Limit Checklist

Quota data was queried on 2026-08-19 using Azure CLI against the live Batch account. The generic `az quota` provider returned `BadRequest` for `Microsoft.Batch`, so account-level Batch quota properties are used as the supported fallback.

| Resource / Limit | Number to Deploy | Total After Deployment | Current Limit / State | Notes |
|------------------|------------------|------------------------|-----------------------|-------|
| Azure Batch pools | 1 | 2 pools | Pool quota: 100; current: 1 | Within limit |
| Low Priority cores allocated by Always On | 80 cores | 80 currently allocated after deployment | Current quota: 150 cores | Within current limit while autoscale pool is at 0 |
| Maximum Low Priority cores across both pools | 80 additional potential autoscale cores | 160 cores | Current quota: 150 cores | Insufficient until quota is raised |
| Azure Container Apps | 0 new; update existing app | 1 existing app | Provisioning state: `Succeeded` | No new app quota required |
| Azure Container Registry | 0 new; add one image tag | 1 existing registry | Existing registry | No new registry quota required |

**Status:** ✅ Low Priority quota was increased to 200 cores and verified from the live Batch account.

**Required gate:** Completed. The account-level Low Priority core quota for `bthfinhpcdev28e5` is 200.

---

## 7. Execution Checklist

### Phase 1: Planning

- [x] Analyze workspace
- [x] Gather requirements
- [x] Confirm subscription and location with user
- [x] Prepare resource inventory
- [x] Fetch live Batch quotas and validate capacity
- [x] Scan codebase
- [x] Select Bicep recipe
- [x] Plan architecture
- [x] User approved this plan

### Phase 2: Preparation

- [x] Request a Low Priority core quota increase to 200 for `bthfinhpcdev28e5`
- [x] Wait for approval and verify `lowPriorityCoreQuota >= 160`
- [x] Run backend tests using the existing `backend/.venv`
- [x] Run the frontend production build and tests
- [x] Build the subscription-scope Bicep template
- [x] Validate the ARM deployment
- [x] Update this plan to `Ready for Validation`
- [x] Invoke the `azure-validate` workflow
- [x] All validation checks pass
  - [x] Core validation: Azure CLI, authentication, Bicep build, ARM validate, What-If
  - [x] Frontend production build and tests
  - [x] Backend unit tests
  - [x] Azure Policy validation
  - [x] Static RBAC role verification
  - [x] Exact deployment What-If contains no deletes or unrelated changes

### Phase 3: Deployment

- [x] Build a uniquely tagged application image with ACR Tasks
- [x] Run resource-group-scope What-If using `infra/always-on-update.bicep`
- [x] Confirm the What-If contains no deletes or unrelated changes
- [x] Deploy the Bicep update and new image
- [x] Verify deployment state is `Succeeded`

### Phase 4: Verification

- [x] Verify `pool-finhpc-alwayson-28e5` exists
- [x] Verify its allocation reaches `Steady` with 10 Low Priority nodes
- [x] Verify the existing autoscale pool remains configured for 0–10 nodes
- [x] Verify the Container App revision uses the newly built image
- [x] Verify `AZURE_BATCH_AUTOSCALE_POOL_ID` and `AZURE_BATCH_ALWAYS_ON_POOL_ID`
- [x] Verify `/healthz` and `/readyz`
- [x] Verify the UI displays Auto Scale and Always On choices
- [x] Submit and observe an Always On simulation job
- [x] Verify live RBAC assignments for ACR and Azure Batch

---

## 8. Rollback

If application verification fails, restore the previous Container App image tag `crfinhpcdev28e5.azurecr.io/finance-hpc-demo:ai-rerun-v2-20260818`. The existing autoscale pool remains separate and is not replaced by the Always On pool.

Deleting or scaling down the Always On pool is not part of this deployment and requires separate user approval.

---

## 9. Validation Proof

Validated: 2026-08-19

Revalidated: 2026-08-20T07:48:06Z

| Check | Result |
|-------|--------|
| Azure target | Passed: confirmed subscription `02822f3b-51ae-46e7-b446-9d74b942e87c`, resource group `rg-finhpc-dev-28e5`, Japan East |
| Frontend test and build | Passed: 1 Vitest test; TypeScript and Vite production build succeeded |
| Backend tests | Passed: 5 unit tests, including the 180-second delay for iterations 1 and 2 |
| Bicep compilation | Passed: targeted template had no diagnostics; main template retained only the pre-existing `BCP187` warning |
| ARM validation | Passed: targeted resource-group deployment returned `Succeeded` |
| What-If | Passed: 4 resources to redeploy, 0 deletes; no resources to create |
| Live capacity | Passed: Batch Low Priority quota 200 cores; both pools `Succeeded` and `Steady` |
| Live RBAC | Passed: `AcrPull` and `Azure Batch Data Contributor` remain assigned at resource scope |
| Diff integrity | Passed: `git diff --check` |

| Check | Command / Source | Result |
|-------|------------------|--------|
| Batch quota | `az batch account show` | Passed: Low Priority quota 200, pool quota 100 |
| Backend tests | `PYTHONPATH=. backend/.venv/bin/python -m unittest discover -s backend/tests -v` | Passed: 4 tests |
| Frontend build | `npm run build` | Passed |
| Frontend tests | `npm test` | Passed: 1 test |
| Main Bicep build | `az bicep build --file infra/main.bicep` | Passed; only the pre-existing Log Analytics `BCP187` type warning |
| Targeted Bicep build | Bicep build for `infra/always-on-update.bicep` | Passed without diagnostics |
| ARM validation | `az deployment group validate ... --template-file infra/always-on-update.bicep` | Passed: `Succeeded` |
| Exact What-If | `az deployment group what-if ... --template-file infra/always-on-update.bicep` | Passed: create Always On pool, modify Container App, no change to Batch account or autoscale pool, no deletes |
| Azure Policy | Azure Policy assignments plus ARM validation | Passed: effective assignments inspected; ARM validation accepted the deployment |
| Diff integrity | `git diff --check` | Passed |

### Role Assignment Verification

- **Status:** Verified
- **Identity:** Existing system-assigned identity of `ca-finhpc-dev-28e5`
- **ACR role:** `AcrPull` scoped to `crfinhpcdev28e5`
- **Batch role:** `Azure Batch Data Contributor` scoped to `bthfinhpcdev28e5`
- **Result:** The application operations match the two resource-scoped data-plane assignments. Live assignments will be rechecked after deployment.

---

## 10. Deployment Result

### 2026-08-20 Sleep and Brand Update

- **Deployment:** `finance-hpc-sleep180-brand-20260820075051`
- **State:** `Succeeded`
- **Image:** `crfinhpcdev28e5.azurecr.io/finance-hpc-demo:sleep180-brand-20260820075051`
- **Image digest:** `sha256:46329374156efa56438d7535e4749e0476c1791c65ca16be636a9b0567f2bc1a`
- **Container App revision:** `ca-finhpc-dev-28e5--0000005`, `Healthy`
- **Batch task delay:** `BATCH_TASK_DELAY_SECONDS=180`
- **UI:** Public JavaScript asset verified `MARKET SHOCK ANALYSES`
- **Health:** `/healthz` and `/readyz` passed
- **Batch pools:** Auto Scale `Steady` at 0 nodes; Always On `Steady` at 10 Low Priority nodes
- **RBAC:** Live `AcrPull` and `Azure Batch Data Contributor` assignments verified

- **Deployment:** `finance-hpc-alwayson-20260819084510`
- **State:** `Succeeded`
- **Image:** `crfinhpcdev28e5.azurecr.io/finance-hpc-demo:alwayson-20260819084510`
- **Container App revision:** `ca-finhpc-dev-28e5--0000004`
- **Always On pool:** `pool-finhpc-alwayson-28e5`, `Steady`, 10 Low Priority nodes
- **Autoscale pool:** `pool-finhpc-dev-28e5`, `Steady`, 0 current nodes, existing 0–10 formula unchanged
- **Health:** `/healthz` returned `{"status":"ok"}`; `/readyz` returned `{"status":"ready"}`
- **UI:** Auto Scale and Always On choices displayed; Always On showed `10台常時`
- **End-to-end job:** `finance-risk-c6ebbdfc` routed to `pool-finhpc-alwayson-28e5`; all 10 tasks completed with zero failures
- **RBAC:** Live `AcrPull` and `Azure Batch Data Contributor` assignments verified
