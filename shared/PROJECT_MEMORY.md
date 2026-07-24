# Shared Project Memory

## Principles

- Maintained project memory is not conversation history. It preserves selected
  decisions, constraints, reliable procedures, recurring traps and useful
  rejected hypotheses.
- The code and the current state of the system remain primary evidence.
- Memory should reduce the space of plausible but projectually wrong
  interpretations; it must not replace verification.
- Human governance is substantive: assistants may propose, compare and
  maintain knowledge, while the developer retains authority over decisions.
- Different assistants may keep attributed diaries. Knowledge becomes shared
  only after explicit review or confirmation.
- Public examples must be sanitized. Operational credentials and private
  infrastructure details stay in protected local memory.

## Maintenance

- Add an entry only when it is likely to improve future work.
- Distinguish facts, hypotheses, decisions and analogies.
- Correct obsolete notes instead of silently treating them as current truth.
- Prefer small, inspectable updates over indiscriminate transcripts.
- Use Git history to make the evolution of memory reviewable and replicable.

## Current experiment

The repository is being extended from a single-organizer example into a
multi-assistant laboratory. Zeno and Zeno Malvagio maintain separate,
attributed observations while sharing a curated project memory.
