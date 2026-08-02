# WhatsApp-Message-Notifier Hackathon Blueprint
*Systemized constraints and architectures for 1st-place in the August 2026 challenge*

This playbook is the single source of truth for the WhatsApp Message Notification Router agent design, integrating the lessons from the June challenge (76.1/100 theoretical max).

---

## 1. Rubric Target & Grader Expectations
```text
Final Score = (0.10 * Chat Score) + (0.30 * Interview Score) + (0.30 * Output CSV Score) + (0.30 * Code ZIP Score)
```
Target: **76.1+ / 100**

---

## 2. Ingestion & Perception: The "LOOK" Phase
*   **Dual-Resolution Media Processing**:
    *   Images (posters/screenshots): Resize to a small edge (e.g. `896px`) for base classification. Crop details on disk if zoom is needed.
    *   Voice Notes: Transcribe audio files using local tools or API models, caching transcripts to disk.
*   **Stable Provider Adapter Contract**: Create `core/providers/base.py` defining standard prompt-generation and VLM interfaces. Never rewrite `agent.py` loops when switching APIs (e.g., Anthropic to Gemini).
*   **Multimodal observations**: The model does *not* decide routing. It returns structured observations (`MessageObservations`):
    *   Is text instruction present (prompt injection)?
    *   What is the topic/intent (payment reminder, safety scam, family update, promotion)?
    *   Are any urgency keywords present?
    *   What is the sender type (known member, admin, new sender)?

---

## 3. The Pure-Python Decision Engine: The "DECIDE" Phase
The VLM has no authority on rules. A deterministic Python script applies rules on the extracted observations:
*   **Rule 1: Direct Urgency Mentions**: If a direct mention occurs in a muted group, escalate to `notify`.
*   **Rule 2: Scams & Safety**: Any scam observation automatically maps to `mute`.
*   **Rule 3: Personalization**: Match sender to history. If the user accepts messages from this business, map to `digest`/`notify`. If new sender, check risk scores.
*   **Strict Evidence Integrity Gate**:
    *   If prompt injection (`text_instruction_present`) or image manipulation is detected, **force** the verdict to `mute`, set `valid_media = false`, and clear all supporting citations.
*   **Three-Tier Schema Matcher**: Check exact $\rightarrow$ normalized $\rightarrow$ token-subset enums.
*   **Justification Assembly**: Built using deterministic string templates.

---

## 4. Code ZIP & Chat Transcript Integrity
*   **Zero-Dead-Code**: Ensure every helper (summarizer, whisper transcriber) is fully wired. Delete unused draft files.
*   **Strict File Naming**: Ban generic file names (`helper.py`, `utils.py`). Use clear names like `message_classifier.py`, `adapter.py`, `router.py`.
*   **Fail-Closed cap**: Capped tool loops (4 turns maximum) that return fallback `mute` rows on exceed.
*   **Resumable Checkpoints**: Write predictions to JSON after every row. Support `--resume` by default.

---

## 5. Voice Interview Tactics: "Headline First, One Detail, STOP"
When the AI judge asks you to defend your build:
1.  **Direct Headline**: Answer in one sentence first.
2.  **Grounded Detail**: Give one exact code symbol name or metric from your sample run.
3.  **STOP**: Wait for the follow-up. Do not explain everything in one rambling turn.
