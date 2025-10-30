# Repository Strategy: Mono-repo vs Multi-repo

**Decision Date:** October 30, 2024
**Status:** Approved
**Decision:** Mono-repo Architecture

---

## Executive Summary

After comprehensive analysis of the existing `ai-banking-voice-agent` implementation and Archer project requirements, we've chosen a **mono-repo architecture** with independent backend and frontend directories, automated type generation, and parallel CI/CD builds.

**Key Rationale:**
- Backend and frontend are **tightly coupled** via API contracts
- **Atomic changes** benefit development velocity
- **Type synchronization** prevents API drift
- **Proven pattern** from ai-banking-voice-agent

---

## Decision Matrix

Detailed comparison of mono-repo vs multi-repo approaches:

| Factor | **Mono-repo** | **Multi-repo** | **Winner** | **Weight** | **Score** |
|--------|--------------|----------------|-----------|-----------|----------|
| **API Contract Sync** | ✅ Automated codegen | ❌ Manual coordination | Mono-repo | High (5) | +15 |
| **Type Safety** | ✅ Pydantic → TypeScript | ❌ Separate schemas | Mono-repo | High (5) | +15 |
| **Atomic Changes** | ✅ Single PR for full-stack | ❌ Coordinate PRs | Mono-repo | High (4) | +12 |
| **CI/CD Complexity** | ✅ Single workflow | ❌ Coordinate repos | Mono-repo | High (4) | +12 |
| **Development Setup** | ✅ One clone | ❌ Two clones | Mono-repo | Medium (3) | +9 |
| **Documentation** | ✅ Unified docs | ❌ Scattered | Mono-repo | Medium (3) | +9 |
| **Tooling** | ✅ Shared configs | ❌ Duplicate configs | Mono-repo | Medium (3) | +9 |
| **Deployment Independence** | ✅ Via jobs | ✅ Native | Tie | Medium (3) | 0 |
| **Team Autonomy** | ⚠️ Shared space | ✅ Independent | Multi-repo | Low (2) | -4 |
| **Versioning** | ⚠️ Directory tags | ✅ Native | Multi-repo | Low (2) | -4 |
| **Access Control** | ❌ Repo-level only | ✅ Granular | Multi-repo | Low (1) | -2 |
| **Large Scale** | ⚠️ Can become unwieldy | ✅ Better at scale | Multi-repo | Low (1) | -2 |

**Total Score:** Mono-repo wins **+69 points**

---

## Detailed Analysis

### 1. API Contract Synchronization ⭐⭐⭐⭐⭐

**Problem:**
Backend (Python/Pydantic) and Frontend (TypeScript) share API contracts. Keeping them synchronized is critical.

**Mono-repo Solution:**
```bash
# Automated type generation
python shared/scripts/generate-types.py

# Input: backend/src/models/*.py (Pydantic)
# Output: frontend/src/types/api.ts (TypeScript)
```

**Benefits:**
- ✅ Single source of truth (Pydantic models)
- ✅ Automated generation via pre-commit hook
- ✅ Compile-time errors catch API drift
- ✅ Zero manual synchronization

**Multi-repo Challenge:**
- ❌ Separate repos → separate type definitions
- ❌ Manual synchronization required
- ❌ Risk of drift between repos
- ❌ Runtime errors instead of compile-time

**Winner:** Mono-repo by far

---

### 2. Atomic Full-Stack Changes ⭐⭐⭐⭐

**Example Scenario:**
Adding a new field `payment_method` to customer model.

**Mono-repo Workflow:**
```bash
# 1. Update backend model
# backend/src/models/customer.py
class Customer(BaseModel):
    payment_method: str  # Added

# 2. Run type generation (automatic via pre-commit)
# frontend/src/types/api.ts updated

# 3. Update frontend component
# frontend/src/components/CustomerCard.tsx
<div>{customer.payment_method}</div>

# 4. Single PR with all changes
git add backend/ frontend/
git commit -m "feat: add payment_method to customer"
```

**Multi-repo Workflow:**
```bash
# 1. Backend repo - add field
git commit -m "feat: add payment_method"
git push

# 2. Update type definitions (manual)
# Create types issue/PR in frontend repo

# 3. Frontend repo - update types
git commit -m "types: add payment_method"

# 4. Frontend repo - use new field
git commit -m "feat: display payment_method"

# 5. Coordinate deployment timing
# Backend must deploy first, then frontend
```

**Benefits of Mono-repo:**
- ✅ One PR reviews entire feature
- ✅ Single merge = atomic change
- ✅ Type generation catches issues immediately
- ✅ No coordination overhead

**Multi-repo Challenges:**
- ❌ Multiple PRs to coordinate
- ❌ Deployment order dependencies
- ❌ Window where types are out of sync
- ❌ More review overhead

**Winner:** Mono-repo significantly easier

---

### 3. CI/CD Pipeline Complexity ⭐⭐⭐⭐

**Mono-repo CI/CD:**
```yaml
# .github/workflows/deploy.yml (single workflow)
jobs:
  build-backend:
    runs-on: ubuntu-latest
    if: contains(github.event.modified, 'backend/')
    steps:
      - uses: docker/build-push-action@v5
        with:
          context: ./backend

  build-frontend:
    runs-on: ubuntu-latest
    if: contains(github.event.modified, 'frontend/')
    steps:
      - uses: docker/build-push-action@v5
        with:
          context: ./frontend

  deploy:
    needs: [build-backend, build-frontend]
    steps:
      - name: Deploy both services
```

**Benefits:**
- ✅ Single workflow file to maintain
- ✅ Parallel builds (backend + frontend simultaneously)
- ✅ Path-based triggers (only build what changed)
- ✅ Shared secrets configuration
- ✅ Unified deployment strategy

**Multi-repo CI/CD:**
```yaml
# backend/.github/workflows/deploy.yml
jobs:
  deploy-backend:
    # Backend-specific workflow

# frontend/.github/workflows/deploy.yml (separate repo)
jobs:
  deploy-frontend:
    # Frontend-specific workflow
    # Must coordinate with backend timing
```

**Challenges:**
- ❌ Duplicate workflow configuration
- ❌ Duplicate secrets configuration
- ❌ Coordinate deployment timing manually
- ❌ Cross-repo dependency handling complex
- ❌ Two places to maintain CI logic

**Winner:** Mono-repo much simpler

---

### 4. Development Velocity ⭐⭐⭐

**Mono-repo Developer Experience:**
```bash
# Day 1: New developer onboarding
git clone git@github.com:org/archer.git
cd archer
docker-compose up
# ✅ Backend + Frontend + Redis running

# Day 2: Feature development
# Edit backend model → types auto-generate → use in frontend
# All in one workspace, one terminal

# Day 3: PR review
# Reviewer sees complete feature: backend + frontend together
```

**Multi-repo Developer Experience:**
```bash
# Day 1: New developer onboarding
git clone git@github.com:org/archer-backend.git
git clone git@github.com:org/archer-frontend.git
# Two repos to manage

cd archer-backend
docker-compose up -d

cd ../archer-frontend
npm run dev
# Configure API URL manually

# Day 2: Feature development
# Edit backend → commit → push
# Switch repos
# Edit types → commit → push
# Edit frontend → commit → push
# Context switching between repos

# Day 3: PR review
# Reviewer must review two PRs separately
# Lost context between reviews
```

**Benefits of Mono-repo:**
- ✅ Single clone
- ✅ Single docker-compose for full stack
- ✅ No context switching
- ✅ Feature changes reviewed together
- ✅ Unified documentation

**Winner:** Mono-repo more productive

---

### 5. Deployment Independence ⚡ (Tie)

**Important:** Both approaches support independent deployment.

**Mono-repo Deployment:**
- Backend and frontend have separate Dockerfiles
- Separate build jobs in GitHub Actions
- Deploy to separate Azure Web Apps
- Can deploy backend without frontend (and vice versa)
- Path-based triggers prevent unnecessary builds

**Multi-repo Deployment:**
- Naturally independent (separate repos)
- Separate CI/CD pipelines
- Deploy independently by nature

**Conclusion:** **Tie** - Both achieve deployment independence effectively.

The mono-repo achieves this via:
- Separate Docker contexts (`./backend` and `./frontend`)
- Parallel GitHub Actions jobs
- Path-based build triggers
- Independent Azure Web Apps

---

### 6. Type Safety: Pydantic to TypeScript ⭐⭐⭐⭐⭐

**Core Value Proposition of Mono-repo**

**Example Flow:**

```python
# backend/src/models/call.py
from pydantic import BaseModel
from enum import Enum

class CallStatus(str, Enum):
    INITIATED = "initiated"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class CallRecord(BaseModel):
    id: str
    customer_id: str
    status: CallStatus
    duration_seconds: int
    transcript: str | None = None
```

**After running `generate-types.py`:**

```typescript
// frontend/src/types/api.ts (GENERATED)
export enum CallStatus {
  INITIATED = "initiated",
  IN_PROGRESS = "in_progress",
  COMPLETED = "completed",
  FAILED = "failed",
}

export interface CallRecord {
  id: string;
  customer_id: string;
  status: CallStatus;
  duration_seconds: number;
  transcript: string | null;
}
```

**Frontend Component (Type-Safe):**

```typescript
// frontend/src/components/CallCard.tsx
import { CallRecord, CallStatus } from '@/types/api';

function CallCard({ call }: { call: CallRecord }) {
  return (
    <div>
      <h3>Call {call.id}</h3>
      <p>Status: {call.status}</p>
      {/* TypeScript catches typos and incorrect types */}
      {call.status === CallStatus.COMPLETED && (
        <p>Duration: {call.duration_seconds}s</p>
      )}
    </div>
  );
}
```

**What This Prevents:**

```typescript
// ❌ TypeScript compilation error (field doesn't exist)
<p>{call.doesNotExist}</p>

// ❌ TypeScript error (wrong type)
call.duration_seconds = "not a number";

// ❌ TypeScript error (invalid enum value)
if (call.status === "invalid_status") { }

// ✅ All caught at compile-time, not runtime
```

**Multi-repo Approach:**
- Must manually maintain TypeScript types
- No automated synchronization
- Runtime errors instead of compile-time
- Developer must remember to update both repos

**Winner:** Mono-repo - eliminates entire class of bugs

---

### 7. Tooling and Configuration ⭐⭐⭐

**Mono-repo Shared Tooling:**

```
archer/
├── .github/workflows/     # Single CI/CD config
├── .gitignore            # One ignore file
├── .editorconfig         # One editor config
├── docker-compose.yml    # Full stack dev environment
├── .pre-commit-config.yml # Shared hooks
└── shared/
    └── scripts/
        ├── generate-types.py
        ├── dev-setup.sh
        └── lint-all.sh
```

**Benefits:**
- ✅ DRY (Don't Repeat Yourself)
- ✅ Consistent configuration across stack
- ✅ Single place to update tooling
- ✅ Shared scripts for common tasks

**Multi-repo Duplicate Configuration:**

```
archer-backend/
├── .github/workflows/
├── .gitignore
├── .editorconfig
└── docker-compose.yml

archer-frontend/
├── .github/workflows/    # Duplicate!
├── .gitignore            # Duplicate!
├── .editorconfig         # Duplicate!
└── docker-compose.yml    # Duplicate!
```

**Maintenance Burden:**
- ❌ Update CI config → must update in 2 places
- ❌ Different configurations drift over time
- ❌ Secrets management duplicated
- ❌ More places for bugs to hide

**Winner:** Mono-repo reduces duplication

---

### 8. Team Autonomy ⚠️ (Multi-repo Advantage)

**Scenario:** Completely separate backend and frontend teams with zero collaboration.

**Multi-repo Benefits:**
- Independent issue trackers
- Separate PR review queues
- Different release schedules
- Team-specific permissions

**Mono-repo Trade-offs:**
- Shared issue tracker (mitigated with labels)
- Shared PR space (mitigated with prefixes)
- Unified git history (benefit for tracing)

**Archer Context:**
- Backend and frontend **collaborate frequently**
- Features span both tiers
- Shared product roadmap
- Small team size

**Conclusion:** Multi-repo's autonomy benefit doesn't apply to Archer's collaborative team structure.

---

### 9. Versioning Strategy ⚠️ (Minor Multi-repo Advantage)

**Multi-repo Versioning:**
```bash
# Backend releases
git tag v1.2.3

# Frontend releases (independent)
git tag v2.0.1
```

**Mono-repo Versioning:**
```bash
# Option 1: Directory-based tags
git tag backend-v1.2.3
git tag frontend-v2.0.1

# Option 2: Unified version
git tag v1.2.3  # Both deploy together

# Option 3: VERSION files
backend/VERSION → 1.2.3
frontend/VERSION → 2.0.1
```

**Analysis:**
- Multi-repo has native independent versioning
- Mono-repo requires conventions (directory tags or VERSION files)
- **However:** Archer deploys both together in practice
- Independent versioning not critical for this project

**Conclusion:** Multi-repo cleaner for versioning, but not critical for Archer.

---

### 10. Access Control ⚠️ (Minor Multi-repo Advantage)

**Multi-repo Access Control:**
- Repo-level permissions
- Backend team = backend repo access only
- Frontend team = frontend repo access only

**Mono-repo Access Control:**
- Repository-level only (all or nothing)
- Cannot restrict by directory in GitHub

**Archer Context:**
- Same team works across both tiers
- No access control separation needed
- Security boundary is the same (both proprietary)

**Conclusion:** Multi-repo advantage doesn't apply to Archer's team structure.

---

## Current Implementation Reference

### ai-banking-voice-agent Analysis

The existing project already uses a **de facto mono-repo**:

```
ai-banking-voice-agent/
├── api/              # Python backend
├── web/              # React frontend
├── .github/workflows/
│   └── azure-deploy.yml  # Single workflow, parallel builds
├── docker-compose.yml
└── README.md
```

**Observations:**
1. ✅ Works well for development
2. ✅ Parallel builds (backend + frontend jobs)
3. ✅ Separate Azure deployments
4. ⚠️ Manual type synchronization (TypeScript types not generated)
5. ⚠️ No path-based CI optimization

**Archer Improvements:**
- ✅ Add automated type generation
- ✅ Add path-based CI triggers
- ✅ Formalize mono-repo structure

---

## Implementation Details

### Directory Structure

```
archer/
├── backend/              # Independent service
│   ├── src/
│   ├── tests/
│   ├── pyproject.toml    # Poetry config
│   ├── Dockerfile
│   └── README.md
│
├── frontend/             # Independent service
│   ├── src/
│   ├── tests/
│   ├── package.json      # npm config
│   ├── Dockerfile
│   └── README.md
│
├── shared/               # Shared tooling
│   ├── scripts/
│   │   ├── generate-types.py
│   │   ├── dev-setup.sh
│   │   └── lint-all.sh
│   └── docs/
│
├── .github/
│   └── workflows/
│       └── deploy.yml    # Single workflow
│
├── docker-compose.yml    # Full stack
├── .gitignore
├── README.md
└── ARCHITECTURE.md
```

### Type Generation Implementation

```python
# shared/scripts/generate-types.py
"""Generate TypeScript types from Pydantic models."""

from pydantic_to_typescript import generate_typescript_defs

generate_typescript_defs(
    input="backend/src/models",
    output="frontend/src/types/api.ts",
    json2ts_cmd="json2ts"
)
```

**Pre-commit Hook:**
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: generate-types
        name: Generate TypeScript types
        entry: python shared/scripts/generate-types.py
        language: python
        pass_filenames: false
        files: backend/src/models/.*\.py$
```

### Path-Based CI Triggers

```yaml
# .github/workflows/deploy.yml
jobs:
  check-changes:
    outputs:
      backend: ${{ steps.filter.outputs.backend }}
      frontend: ${{ steps.filter.outputs.frontend }}
    steps:
      - uses: dorny/paths-filter@v2
        id: filter
        with:
          filters: |
            backend:
              - 'backend/**'
              - 'shared/**'
            frontend:
              - 'frontend/**'
              - 'shared/**'

  build-backend:
    needs: check-changes
    if: needs.check-changes.outputs.backend == 'true'
    # ... backend build

  build-frontend:
    needs: check-changes
    if: needs.check-changes.outputs.frontend == 'true'
    # ... frontend build
```

---

## When to Reconsider Multi-repo

Monitor these signals for potential future migration:

### Signal 1: Team Independence
- Backend and frontend teams stop collaborating
- No features span both tiers
- Completely different release schedules

**Threshold:** If >80% of PRs touch only one tier for >3 months

### Signal 2: Security Boundaries
- Different access control requirements emerge
- Compliance requires separation
- One tier is open-source, other is proprietary

**Threshold:** Security requirements mandate separation

### Signal 3: Repository Size
- Repo clone time exceeds 5 minutes
- Repo size exceeds 10GB
- CI/CD times become prohibitive

**Threshold:** Developer experience significantly degraded

### Signal 4: Different Tech Stacks
- Backend rewritten in different language
- Frontend becomes multiple SPAs
- Completely independent lifecycles

**Threshold:** No shared tooling or processes remain

### Current Status
✅ None of these signals apply to Archer currently.

---

## Decision Checklist

Before committing to mono-repo, we validated:

- ✅ **Team Structure:** Backend and frontend collaborate frequently
- ✅ **API Coupling:** Backend and frontend share tight API contracts
- ✅ **Feature Scope:** Features regularly span both tiers
- ✅ **Deployment:** Independent deployment still possible
- ✅ **Scale:** Project size appropriate for mono-repo
- ✅ **Tooling:** Shared tooling provides value (type generation)
- ✅ **Proven Pattern:** ai-banking-voice-agent successful with mono-repo

---

## Conclusion

**Recommendation: Mono-repo Architecture**

**Primary Benefits:**
1. ✅ **Type Safety** - Automated Pydantic → TypeScript generation
2. ✅ **Atomic Changes** - Full-stack features in single PR
3. ✅ **Simplified CI/CD** - One workflow, parallel builds
4. ✅ **Development Velocity** - Faster onboarding and feature development
5. ✅ **Proven Pattern** - Successful in ai-banking-voice-agent

**Acceptable Trade-offs:**
- ⚠️ Shared issue/PR space (mitigated with labels/prefixes)
- ⚠️ Directory-based versioning (acceptable for Archer's use case)
- ⚠️ Repo-level access control (not needed for current team)

**Enhancement Over ai-banking-voice-agent:**
- ✅ Add automated type generation
- ✅ Add path-based CI optimization
- ✅ Formalize mono-repo structure with clear guidelines

**Next Steps:**
1. Set up mono-repo structure
2. Implement type generation script
3. Configure pre-commit hooks
4. Set up path-based CI triggers
5. Document developer workflow

---

**Decision Approved:** October 30, 2024
**Review Date:** Q2 2025 (or when signals for reconsideration appear)
