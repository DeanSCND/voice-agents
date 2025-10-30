# Latency Analysis & Measurement Strategy

## Executive Summary

**Issue**: Phase 0 exit criteria expect "<100ms first-byte latency" but this target is ambiguous and potentially unattainable when considering the full PSTN→Twilio→Cartesia→Twilio→PSTN chain.

**Root Cause**: The 40-90ms Cartesia Line SDK latency refers to **TTS generation time only**, not end-to-end conversational latency experienced by phone callers.

**Impact**: Without clarification and realistic targets, Phase 0 could fail its GO/NO-GO decision despite Cartesia performing exactly as advertised.

**Recommendation**: Revise Phase 0 exit criteria with component-specific latency targets and structured measurement methodology.

---

## 1. Latency Chain Analysis

### Full Conversational AI Latency Chain

```
┌─────────────────────────────────────────────────────────────────┐
│  End-to-End Conversational Latency (User Speaks → User Hears)   │
└─────────────────────────────────────────────────────────────────┘

1. [User speaks] → PSTN/Cellular encoding and transmission
   ├─ Encoding: 5-10ms
   ├─ Network: 20-50ms (local) to 50-100ms (long-distance)
   └─ Twilio ingress processing: 10-30ms
   ⏱️ SUBTOTAL: 35-140ms

2. [Twilio] → Media stream to Cartesia Line SDK
   ├─ Network routing: 5-20ms (same region)
   ├─ WebSocket overhead: 5-15ms (established connection)
   └─ Line SDK ingress: 5-10ms
   ⏱️ SUBTOTAL: 15-45ms

3. [Cartesia Line SDK] → Speech-to-Text (STT)
   ├─ Audio buffering: 10-30ms
   ├─ STT processing: 50-150ms (streaming)
   └─ Transcription finalization: 10-30ms
   ⏱️ SUBTOTAL: 70-210ms

4. [Cartesia Line SDK] → LLM Inference
   ├─ Context retrieval: 10-50ms
   ├─ GPT-4 inference (first token): 200-800ms
   ├─ Streaming response: 50-200ms (for full sentence)
   └─ Tool calls (if needed): +500-2000ms
   ⏱️ SUBTOTAL: 260-1050ms (simple) or 760-2850ms (with tools)

5. [Cartesia Line SDK] → Text-to-Speech (TTS) ⭐ THIS IS THE "40-90ms"
   ├─ TTS model initialization: 5-15ms
   ├─ First audio chunk generation: 40-90ms ← CARTESIA'S ADVERTISED METRIC
   ├─ Streaming synthesis: 20-50ms (continuation)
   └─ Audio encoding: 5-15ms
   ⏱️ SUBTOTAL: 70-170ms

6. [Cartesia] → Twilio egress
   ├─ Line SDK egress: 5-10ms
   ├─ Network routing: 5-20ms
   └─ Twilio media gateway: 10-30ms
   ⏱️ SUBTOTAL: 20-60ms

7. [Twilio] → PSTN transmission to user
   ├─ Twilio egress processing: 10-30ms
   ├─ PSTN routing: 20-50ms (local) to 50-100ms (long-distance)
   └─ Decoding/playback: 5-10ms
   ⏱️ SUBTOTAL: 35-140ms

┌─────────────────────────────────────────────────────────────────┐
│  TOTAL END-TO-END LATENCY (without tool calls)                   │
│  Best case: ~505ms                                               │
│  Typical case: ~875ms                                            │
│  Worst case: ~1815ms                                             │
│                                                                   │
│  TOTAL WITH TOOL CALLS (verification, payment, etc.)             │
│  Typical: 1375ms - 2915ms                                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Benchmark Comparison

### Cartesia Line SDK vs ElevenLabs Conversational AI

| Component | ElevenLabs (Previous) | Cartesia Line SDK (New) | Improvement |
|-----------|----------------------|------------------------|-------------|
| **STT Processing** | 100-200ms (external) | 70-210ms (integrated) | Similar/worse |
| **LLM Inference** | 200-800ms (external) | 200-800ms (external) | Same |
| **TTS Generation** | 135-300ms (Flash/Turbo) | 40-90ms (Sonic) | **62% faster** ✅ |
| **Infrastructure Hops** | Many (custom WebSocket) | Fewer (managed) | **Simpler** ✅ |
| **First Audio Byte** | 150-200ms (TTS only) | 40-90ms (TTS only) | **62% faster** ✅ |
| **End-to-End (simple)** | ~950ms typical | ~875ms typical | **8% faster** |
| **End-to-End (with tools)** | ~1600ms typical | ~1375ms typical | **14% faster** |

**Key Insight**: Cartesia's 62% TTS improvement translates to only ~8-14% end-to-end improvement because TTS is just one component of the full latency chain.

---

## 3. Industry Standards & User Perception

### ITU-T G.114 Recommendations (Telephony Quality)

| One-Way Latency | User Experience | Call Quality Rating |
|-----------------|-----------------|---------------------|
| **0-150ms** | Imperceptible | Excellent - No impact on conversation |
| **150-250ms** | Acceptable | Good - Slight delay noticeable |
| **250-400ms** | Noticeable | Fair - Users adapt but quality suffers |
| **400ms+** | Annoying | Poor - Conversation breaks down |

**Target for conversational AI**: <400ms one-way (best effort), <250ms (ideal), <150ms (exceptional)

### Real-World Conversational AI Benchmarks (2024)

| Platform | Advertised Latency | What It Measures | End-to-End Reality |
|----------|-------------------|------------------|-------------------|
| **Cartesia Sonic** | 40-90ms | TTS generation only | 500-1800ms full conversation |
| **ElevenLabs Flash** | 135ms | TTS generation only | 600-2000ms full conversation |
| **OpenAI Realtime API** | 320ms avg | STT + LLM + TTS | 500-1500ms (optimized stack) |
| **GPT-4 Turbo Voice** | 2500-5000ms | Full conversation | Same (includes thinking time) |

**Industry Reality**: Most conversational AI systems achieve 500-1500ms for simple responses, 1500-3000ms with tool calls.

---

## 4. Geographic & Network Factors

### Regional Latency Variations

**US East Coast → Cartesia (US-East)**:
- PSTN hops: 35-70ms
- Internet routing: 10-30ms
- **Total regional overhead**: ~45-100ms

**US West Coast → Cartesia (US-East)**:
- PSTN hops: 50-100ms
- Cross-country routing: 30-80ms
- **Total regional overhead**: ~80-180ms

**International (Canada/Mexico) → Cartesia (US)**:
- International PSTN: 100-200ms
- Border routing: 20-50ms
- **Total regional overhead**: ~120-250ms

**Recommendation**: Measure latency from multiple geographic locations during Phase 0.

---

## 5. Revised Phase 0 Exit Criteria

### ❌ PROBLEMATIC (Current)

From `docs/IMPLEMENTATION_PLAN.md:111`:
```markdown
Quality Checklist:
- [ ] First-byte latency <100ms (measured)
- [ ] End-to-end latency <500ms
```

**Problems**:
1. "First-byte latency" is ambiguous (TTS-only? Full chain?)
2. <100ms is unattainable for end-to-end (conflicts with <500ms)
3. No measurement methodology specified
4. No component isolation strategy
5. Will likely fail despite Cartesia performing well

---

### ✅ RECOMMENDED (Revised)

#### Component-Specific Latency Targets

**Success criteria organized by measurable components:**

##### A. Cartesia TTS Generation (Isolated)
- [ ] **TTS first-byte latency <100ms** (measured via Line SDK events)
  - Target: 40-90ms (per Cartesia spec)
  - Measurement: Line SDK `tts_start` → `audio_chunk_received` events
  - Validation: 20+ test calls, 90th percentile <100ms

##### B. End-to-End Conversational Latency (User Experience)
- [ ] **Simple greeting response <600ms** (user speaks → hears first word)
  - Target: 500-600ms (competitive with industry)
  - Measurement: Manual stopwatch + call recordings with timestamps
  - Validation: 10+ test calls from different locations, median <600ms

- [ ] **Multi-turn responses <800ms** (follow-up questions)
  - Target: 600-800ms (context already loaded)
  - Measurement: Time between user finishes speaking → agent starts responding
  - Validation: 10+ multi-turn conversations, median <800ms

- [ ] **Tool-based responses <2000ms** (verification, payment lookups)
  - Target: 1500-2000ms (includes database queries)
  - Measurement: User request → agent provides verification result
  - Validation: 5+ tool-call scenarios, median <2000ms

##### C. Subjective Quality (User Perception)
- [ ] **Latency feels natural** (7+/10 rating from 3+ testers)
  - Does the conversation flow feel natural?
  - Do delays disrupt the conversation?
  - Is it comparable to calling a business support line?

---

## 6. Measurement Methodology

### Instrumentation Strategy

#### Level 1: Line SDK Internal Metrics (Cartesia-only latency)

```python
# backend/src/poc/latency_tracker.py
from line import Agent, Context
import time

class LatencyTrackingAgent(Agent):
    """POC agent with comprehensive latency tracking"""

    def __init__(self):
        super().__init__()
        self.latency_log = []

    async def on_stt_start(self, context: Context):
        context.metrics['stt_start'] = time.time()

    async def on_stt_complete(self, context: Context, transcript: str):
        stt_latency = time.time() - context.metrics['stt_start']
        context.metrics['stt_latency'] = stt_latency

    async def on_llm_start(self, context: Context):
        context.metrics['llm_start'] = time.time()

    async def on_llm_first_token(self, context: Context):
        llm_ttft = time.time() - context.metrics['llm_start']
        context.metrics['llm_ttft'] = llm_ttft

    async def on_tts_start(self, context: Context):
        context.metrics['tts_start'] = time.time()

    async def on_first_audio_chunk(self, context: Context):
        tts_latency = time.time() - context.metrics['tts_start']
        context.metrics['tts_latency'] = tts_latency

        # This is the "<100ms" target
        self.latency_log.append({
            'type': 'tts_first_byte',
            'value_ms': tts_latency * 1000,
            'timestamp': time.time()
        })

    async def on_call_complete(self, context: Context):
        # Export latency log for analysis
        save_metrics(context.call_sid, self.latency_log, context.metrics)
```

**Cartesia Line SDK Events to Track**:
- `stt_start` → `stt_complete`: STT latency
- `llm_start` → `llm_first_token`: LLM time-to-first-token (TTFT)
- `tts_start` → `first_audio_chunk`: **TTS first-byte latency ⭐**
- `user_stop_speaking` → `agent_start_speaking`: Perceived response time

---

#### Level 2: End-to-End User Experience (Full chain latency)

**Manual Measurement Protocol**:

```markdown
### Test Call Procedure

**Objective**: Measure user-perceived latency (what callers actually experience)

**Equipment**:
- Two phones (or phone + SIP client)
- Call recording enabled (Twilio + local recording)
- Stopwatch app or video recording with timestamps

**Test Script**:
1. Place call to Archer POC agent
2. Wait for agent greeting
3. User says: "Hello, can you hear me?" ⏱️ START
4. Agent responds: "Yes, I can hear you clearly..." ⏱️ STOP
5. Record latency: Time from user finishing sentence → agent first word
6. Repeat with 5 different prompts per call
7. Make 10 calls total from different locations (home, office, mobile network)

**Metrics to Record**:
- Location/network type (home WiFi, office, LTE, 5G)
- Time of day
- Geographic region
- Measured latency for each exchange
- Subjective quality rating (1-10)
- Audio quality issues (dropouts, robotic voice, etc.)
```

**Automated Timestamp Analysis** (from call recordings):

```python
# scripts/analyze_call_latency.py
import wave
import numpy as np
from pydub import AudioSegment
from pydub.silence import detect_nonsilent

def measure_response_latency(call_recording_path: str) -> dict:
    """
    Analyze call recording to measure response latency.

    Detects:
    1. User speech segments (when user is talking)
    2. Silence gaps (when neither is talking)
    3. Agent speech segments (when agent responds)

    Returns latency = silence duration between user stop and agent start
    """
    audio = AudioSegment.from_wav(call_recording_path)

    # Detect non-silent chunks (speech segments)
    # min_silence_len=500ms catches gaps between speakers
    nonsilent_ranges = detect_nonsilent(
        audio,
        min_silence_len=500,
        silence_thresh=-40
    )

    latencies = []
    for i in range(len(nonsilent_ranges) - 1):
        user_speech_end = nonsilent_ranges[i][1]  # milliseconds
        agent_speech_start = nonsilent_ranges[i + 1][0]

        latency_ms = agent_speech_start - user_speech_end

        # Filter out unrealistic values (user interrupted agent)
        if 100 < latency_ms < 5000:
            latencies.append(latency_ms)

    return {
        'latencies_ms': latencies,
        'median_ms': np.median(latencies),
        'p90_ms': np.percentile(latencies, 90),
        'p95_ms': np.percentile(latencies, 95),
        'exchanges': len(latencies)
    }

# Usage during Phase 0:
# python scripts/analyze_call_latency.py recordings/poc_call_001.wav
```

---

#### Level 3: Component Isolation (Debugging high latency)

**When end-to-end latency exceeds targets, isolate the problem:**

```python
# backend/src/poc/diagnostic_agent.py

class DiagnosticAgent(Agent):
    """Agent that logs every latency component for debugging"""

    async def process_user_speech(self, audio_stream):
        # 1. STT latency
        t0 = time.time()
        transcript = await self.stt_engine.transcribe(audio_stream)
        stt_ms = (time.time() - t0) * 1000

        # 2. LLM latency
        t1 = time.time()
        response_text = await self.llm_engine.generate(transcript)
        llm_ms = (time.time() - t1) * 1000

        # 3. TTS latency
        t2 = time.time()
        audio_response = await self.tts_engine.synthesize(response_text)
        tts_ms = (time.time() - t2) * 1000

        # Log component breakdown
        logger.info(
            f"Latency breakdown: "
            f"STT={stt_ms:.0f}ms, "
            f"LLM={llm_ms:.0f}ms, "
            f"TTS={tts_ms:.0f}ms, "
            f"TOTAL={stt_ms + llm_ms + tts_ms:.0f}ms"
        )

        # If total exceeds budget, identify culprit
        if stt_ms + llm_ms + tts_ms > 1000:
            if llm_ms > 500:
                logger.warning("LLM inference is the bottleneck")
            elif stt_ms > 300:
                logger.warning("STT processing is slow")
            elif tts_ms > 200:
                logger.warning("TTS generation is slow")
```

**Diagnostic Commands**:
```bash
# Run POC agent with full diagnostics
poetry run python src/poc/diagnostic_agent.py --log-level=DEBUG

# Extract latency breakdown from logs
grep "Latency breakdown" logs/poc_*.log | awk '{print $4, $5, $6}' > latency_report.csv

# Generate statistical report
python scripts/latency_stats.py latency_report.csv
# Output:
# STT: median=120ms, p90=180ms, p95=210ms
# LLM: median=450ms, p90=800ms, p95=1200ms
# TTS: median=65ms, p90=95ms, p95=110ms ← Should meet <100ms target
```

---

## 7. Regional Strategy

### Multi-Region Testing Plan

**Phase 0 should test from multiple locations to identify geographic latency variance.**

#### Test Locations (Recommended)

| Location | Network Type | Expected Overhead | Priority |
|----------|--------------|-------------------|----------|
| **US East Coast** | Home broadband | +45-100ms | High (baseline) |
| **US West Coast** | Home broadband | +80-180ms | High (worst US case) |
| **US Central** | Mobile LTE/5G | +60-140ms | Medium |
| **Canada (Toronto)** | International PSTN | +120-250ms | Low (nice to have) |

**If latency is unacceptable from West Coast**:
- Consider deploying Cartesia agents in multiple regions (US-West + US-East)
- Use Twilio Edge Locations to route calls to nearest Cartesia instance
- Document geographic limitations in Phase 0 report

---

## 8. Comparison to ElevenLabs Baseline

### Establishing Baseline (Important!)

**Phase 0 should compare Cartesia to previous ElevenLabs implementation:**

```markdown
### Test Procedure: Side-by-Side Comparison

**Goal**: Validate that Cartesia is actually faster than ElevenLabs in practice

**Steps**:
1. Make 5 test calls to existing ai-banking-voice-agent (ElevenLabs)
2. Make 5 test calls to new Archer POC (Cartesia)
3. Use identical test scripts: "Hello" → "Can you verify my account?"
4. Measure end-to-end latency for both
5. Compare results

**Expected Outcome** (based on TTS improvement):
- ElevenLabs: ~950ms average simple responses
- Cartesia: ~875ms average simple responses (8% faster)
- Cartesia should be noticeable but not dramatic improvement

**If Cartesia is NOT faster than ElevenLabs**:
- Investigate Line SDK integration issues
- Check network routing (are calls going through extra hops?)
- Verify Cartesia region selection (use US-East for US customers)
```

---

## 9. Updated Phase 0 Deliverables

### Quality Report Structure

```markdown
# Phase 0 Cartesia Validation Report

## 1. Executive Summary
- GO or NO-GO recommendation
- Key findings
- Latency comparison to ElevenLabs baseline

## 2. Latency Measurements

### 2.1 Component Latency (Cartesia Internal)
| Metric | Target | Median | P90 | P95 | Status |
|--------|--------|--------|-----|-----|--------|
| TTS first-byte | <100ms | 68ms | 92ms | 98ms | ✅ PASS |
| STT processing | <200ms | 145ms | 190ms | 215ms | ⚠️ MARGINAL |
| LLM first-token | <300ms | 280ms | 450ms | 680ms | ⚠️ VARIABLE |

### 2.2 End-to-End Latency (User Experience)
| Scenario | Target | Median | P90 | P95 | Status |
|----------|--------|--------|-----|-----|--------|
| Simple greeting | <600ms | 520ms | 680ms | 750ms | ✅ PASS |
| Follow-up question | <800ms | 650ms | 820ms | 900ms | ⚠️ MARGINAL |
| Verification lookup | <2000ms | 1450ms | 1890ms | 2100ms | ⚠️ MARGINAL |

### 2.3 Geographic Variance
| Location | Network | Avg Latency | vs Baseline |
|----------|---------|-------------|-------------|
| US East (home) | Broadband | 520ms | +0ms (baseline) |
| US West (home) | Broadband | 680ms | +160ms |
| US Central (mobile) | LTE | 750ms | +230ms |

### 2.4 Comparison to ElevenLabs
| Metric | ElevenLabs | Cartesia | Improvement |
|--------|-----------|----------|-------------|
| TTS latency | 180ms | 68ms | 62% faster ✅ |
| End-to-end simple | 950ms | 520ms | 45% faster ✅ |
| End-to-end with tools | 1850ms | 1450ms | 22% faster ✅ |

## 3. Subjective Quality
| Tester | Latency Rating (1-10) | Voice Naturalness | Overall |
|--------|----------------------|-------------------|---------|
| Dean | 8/10 | 9/10 | Approve |
| Tester 2 | 7/10 | 8/10 | Approve |
| Tester 3 | 9/10 | 9/10 | Approve |

Average: 8/10 latency, 8.7/10 voice quality

## 4. Issues Discovered
- LLM inference is variable (280-680ms range) - needs prompt optimization
- West Coast adds +160ms overhead - may need regional deployment later
- Verification tool calls exceed 2000ms in 5% of cases - database query optimization needed

## 5. Recommendation
**GO: Proceed to Phase 1**

Rationale:
- Cartesia TTS is 62% faster than ElevenLabs (as advertised)
- End-to-end latency is 45% better for simple responses (520ms vs 950ms)
- Subjective quality ratings exceed 7/10 target (average 8/10)
- Issues identified are optimization opportunities, not blockers
- Strong confidence in Cartesia choice (9/10)
```

---

## 10. Recommendations Summary

### Immediate Actions (Before Phase 0 Starts)

1. **Update IMPLEMENTATION_PLAN.md** with revised exit criteria:
   - Replace ambiguous "<100ms first-byte latency" with component-specific targets
   - Add TTS-only target: <100ms (Cartesia internal)
   - Add end-to-end targets: <600ms simple, <800ms multi-turn, <2000ms tools
   - Add measurement methodology section

2. **Create latency tracking instrumentation**:
   - Line SDK event hooks for component latency
   - Call recording analysis scripts for end-to-end measurement
   - Diagnostic mode for troubleshooting high latency

3. **Establish ElevenLabs baseline**:
   - Measure current ai-banking-voice-agent latency (5-10 calls)
   - Document for comparison during Phase 0

4. **Prepare multi-location testing**:
   - Test from US East, US West, mobile networks
   - Document geographic latency variance

### During Phase 0 Execution

1. **Run comprehensive latency tests** (20+ calls):
   - Measure Cartesia TTS latency (should hit <100ms)
   - Measure end-to-end user experience (target <600ms simple responses)
   - Compare to ElevenLabs baseline (should be 8-45% faster)

2. **Collect subjective ratings** (3+ testers):
   - Does latency feel natural? (target 7+/10)
   - Is it better than ElevenLabs? (should be "yes")

3. **Generate Phase 0 Quality Report**:
   - Component latency breakdown
   - End-to-end measurements with percentiles
   - Geographic variance analysis
   - Comparison to ElevenLabs
   - GO/NO-GO recommendation

### GO Decision Criteria (Revised)

**Proceed to Phase 1 if**:
- ✅ Cartesia TTS latency <100ms (P90)
- ✅ End-to-end latency <600ms for simple responses (median)
- ✅ Subjective latency rating 7+/10 from 3+ testers
- ✅ Measurably faster than ElevenLabs baseline (any improvement)
- ✅ No critical technical blockers discovered

**NO-GO (pivot back to ElevenLabs) if**:
- ❌ Cartesia TTS latency >150ms (P90) - not as advertised
- ❌ End-to-end latency >800ms simple responses - worse than ElevenLabs
- ❌ Subjective rating <6/10 - users find it frustrating
- ❌ Critical bugs in Line SDK that block progress

---

## 11. Conclusion

**The original Phase 0 criterion "<100ms first-byte latency" was ambiguous and unattainable for end-to-end conversational latency.**

**Revised approach**:
1. Measure **TTS-only latency** (Cartesia internal): target <100ms ✅ achievable
2. Measure **end-to-end latency** (user experience): target <600ms ✅ realistic
3. Compare to **ElevenLabs baseline**: expect 8-45% improvement ✅ meaningful
4. Focus on **subjective perception**: does it feel fast enough? ✅ practical

**This structured measurement approach will enable confident GO/NO-GO decision based on realistic, achievable targets.**

---

**Related Documents**:
- `docs/IMPLEMENTATION_PLAN.md` - Phased implementation strategy (needs update)
- `DESIGN-CARTESIA-LINE-SYSTEM.md` - Technical design and latency claims
- `docs/MIGRATION_FROM_ELEVENLABS.md` - Comparison to previous system
