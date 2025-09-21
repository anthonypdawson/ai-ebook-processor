# Unnamed First-Person Journal Guidance

Status: Lightweight Playbook (No Code Changes Required)
Last Updated: 2025-09-21

## Context
Some books (diaries, logs, confessional journals) are written entirely in first person with an unnamed narrator. Standard retrieval may struggle with queries that refer to “the narrator” while the text only contains “I”, “me”, “my”. This document provides a manual operational workaround without altering the core pipeline.

## Goals
- Avoid hallucinating a name for the narrator
- Improve retrieval recall for abstract or third-person queries about first-person content
- Keep system changes at zero (prompt + query hygiene only)

## Quick Checklist
| Task | Purpose |
|------|---------|
| Add context note to prompt | Prevent invented name |
| Dual phrasing in tricky queries | Boost recall |
| Use temporal anchors explicitly | Disambiguate evolving state |
| Avoid interpretive adjectives unless grounded | Reduce hallucination risk |
| Enforce citation to raw chunks (if answering) | Maintain grounding |

## Prompt Snippet (Reusable)
```
Instruction: The source material is an unnamed first-person journal. All first-person pronouns (I, me, my) refer to a single unnamed narrator. Do not invent or infer a name or identity beyond what is literally stated. Refer to them only as “the narrator” if needed.
```
Include this before user questions or inside your answer synthesis chain.

## Query Crafting Tips
| User Intent | Suggested Query Form |
|-------------|---------------------|
| Action recall | "What did the narrator (I) do after the storm?" |
| Emotional state | "How did the narrator (I) describe their feelings after the argument?" |
| Timeline comparison | "Earlier vs later: how does the narrator’s tone (I) change about isolation?" |

If a first attempt returns weak matches, retry with explicit first-person form or vice versa.

## Manual Query Expansion (Optional)
When forming a difficult question, append aliases in parentheses:
"narrator (I me my) reaction to night sounds"

## Avoiding Hallucinated Identity
Red flags to watch for:
- A proper name appears (discard answer)
- Stable traits asserted without textual support ("He is a former soldier")
- Over-interpretation of motives (“because he feared rejection”) when not explicit

Response correction phrase (use if drift detected):
"Correction: The narrator is unnamed; do not fabricate a name or unstated background."

## Temporal Anchoring
If entries show clear progression but use relative time words ("today", "yesterday"):
- Phrase query with a neutral index: "In earlier entries, how does the narrator describe shelter conditions?"
- If you know approximate phase: "In later part of the journal (after initial illness), how does the narrator describe energy levels?"

## Mini Evaluation Procedure
Create 5–10 canned queries:
1. Narrative action: "What does the narrator do right after hearing distant voices?"
2. Emotional shift: "How does the narrator’s tone change about solitude?"
3. Resource tracking: "What supplies does the narrator mention losing?"
4. Self-state: "How does the narrator describe physical condition mid-journal?"
5. Motivation: "What short-term goals does the narrator explicitly state?"

For each:
- Verify top retrieved chunks contain literal supporting sentences
- Check no invented names
- Note if adding dual phrasing improved retrieval

## When To Escalate to Code Changes
Consider a dedicated feature only if ALL are true:
- ≥10% of corpus fits this pattern
- Recall gap (phrased with vs without "narrator") > 15%
- Prompt guardrails fail to prevent fabricated names (>5% of answers)

## Optional Local Reference File
You may store a simple alias helper (not integrated):
```
{
  "unnamed_journal_book_id": {
    "narrator_aliases": ["the narrator", "the writer", "the diarist"]
  }
}
```
Use it manually when crafting queries.

## Summary
You can handle unnamed first-person journals today with prompt hygiene, dual phrasing in queries, and vigilant answer validation—no pipeline changes required. Revisit automation only if such texts become common or manual effort grows.

---
End of document.
