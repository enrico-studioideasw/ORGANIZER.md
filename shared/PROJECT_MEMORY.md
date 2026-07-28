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

## Shared contract before implementation

- In collaborative design, implementation starts only after the participants
  have made the intended behaviour explicit, inspected it together and treated
  it as the current signed contract.
- The useful sequence is: establish the concept; write the syntax, invariants,
  transformations and boundary cases; simulate the difficult flows; review
  and sign the contract; transcribe it into code; compile and test only then.
- A compiling program is not automatically more authoritative or complete
  than a specification. An incomplete or non-executable artefact may carry the
  essential model more faithfully than provisional working code.
- Compilation and tests validate a signed implementation. They do not settle
  an architectural question that is still being discussed.
- Local speed must not destroy shared progress. Before changing a shared file,
  inspect whether another authorised participant has changed it and preserve
  that work. Redundant material is preferable to silently lost reasoning or
  code.
- The assistant must distinguish four different moments: collaborative
  design, explicit confirmation, mechanical transcription and verification.
  Moving to a later moment without the others is a process error even when the
  produced code happens to work.

EWB served as the case study that exposed this method. Its most reusable
result is not the language or VM themselves, but the emergence of a
collaborator able to follow a shared, reasoned process instead of treating the
repository as a personal implementation task.

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
