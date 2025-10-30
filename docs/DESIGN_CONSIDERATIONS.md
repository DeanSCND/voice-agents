# Design Considerations

**Last Updated:** November 2, 2024  
**Author:** Architecture Review

This document captures outstanding design questions and risks raised during the architecture and implementation review. Each item references the source planning material and outlines recommended follow-up actions.

---

## 1. Timeline Alignment

- **Observation:** The implementation plan targets a 13-week delivery (docs/IMPLEMENTATION_PLAN.md:17, docs/IMPLEMENTATION_PLAN.md:31), while the Cartesia design document frames the same scope as a 6-week effort (DESIGN-CARTESIA-LINE-SYSTEM.md:2010, DESIGN-CARTESIA-LINE-SYSTEM.md:2019).  
- **Implication:** Conflicting timelines will distort resource planning, stakeholder expectations, and success metrics.  
- **Recommendation:** Establish a single authoritative schedule (milestones, staffing, buffers) and update all downstream artifacts to reflect it. Flag any scope that depends on accelerated delivery as “stretch” until resourced.

## 2. Data Protection & Compliance

- **Observation:** The PostgreSQL schema stores sensitive customer identifiers and full call transcripts/tool payloads (docs/PERSISTENCE_STRATEGY.md:146, docs/PERSISTENCE_STRATEGY.md:199), but the plan does not address encryption, retention, access controls, or tenant isolation.  
- **Implication:** Without defined controls, Archer risks non-compliance with privacy and collections regulations once production traffic is ingested.  
- **Recommendation:** Document and implement a security baseline (at-rest and in-transit encryption, row-level or tenant-scoped access policies, rotation/retention schedules, incident logging). Explicitly align with legal/compliance requirements before Phase 1 development locks in persistence choices.

## 3. Negotiation Guidance LLM Usage

- **Observation:** Negotiation tooling forwards customer balances, offers, and conversation context to an external LLM service (DESIGN-CARTESIA-LINE-SYSTEM.md:495, DESIGN-CARTESIA-LINE-SYSTEM.md:1525) without documented redaction or data-sharing policy.  
- **Implication:** Uncontrolled sharing of PII/PCI-adjacent data may violate privacy policy or debt-collection regulations.  
- **Recommendation:** Route the workload through a private Azure OpenAI (GPT-5) deployment to keep data inside the corporate tenant, and pair it with guardrails: explicit consent data flows, minimization/redaction of inputs, disabled prompt logging, and governance sign-off.

## 4. Assumed Cartesia Controls

- **Observation:** The proposed Line deployment assumes Cartesia exposes PCI/SOX compliance toggles and granular Twilio integration controls (DESIGN-CARTESIA-LINE-SYSTEM.md:1507, DESIGN-CARTESIA-LINE-SYSTEM.md:1543).  
- **Implication:** If these features are aspirational or require additional subscriptions, operational readiness, audit trails, and compliance posture will suffer.  
- **Recommendation:** Validate the availability and maturity of these controls with Cartesia before committing to them, and define compensating measures (custom logging, WAF, network segmentation) if gaps exist.

## 5. Phase 0 Latency Targets

- **Observation:** Phase 0 exit criteria expect <100 ms first-byte and <500 ms end-to-end latency (docs/IMPLEMENTATION_PLAN.md:111) even though the architecture still relies on PSTN → Twilio → Cartesia hops (DESIGN-CARTESIA-LINE-SYSTEM.md:42).  
- **Implication:** The latency bar may be unrealistic, risking a NO-GO decision for reasons outside engineering control.  
- **Recommendation:** Develop a concrete measurement plan (regions, call paths, tooling) and confirm vendor SLAs. Consider widening success thresholds or defining a target range with acceptable variance before Phase 0 starts.

---

### Next Review

Revisit this document once:  
- The unified execution schedule is published,  
- Data-protection requirements are signed off, and  
- Vendor capability confirmations are documented.  

Update status fields and retire mitigated items as the project progresses.

