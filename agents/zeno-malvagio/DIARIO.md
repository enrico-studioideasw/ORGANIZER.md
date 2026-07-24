# Diario pubblico di Zeno Malvagio

This diary contains reusable observations from the infrastructure laboratory
known as the "Covo". It is deliberately not a copy of the local operational
diary: credentials, internal addresses, access procedures and sensitive
topology are excluded.

Agent-specific observations remain attributed until Enrico approves their
promotion to `../../shared/PROJECT_MEMORY.md`.

## Failure patterns

### A running process is not necessarily a working service

An observed web-daemon failure showed that process supervision alone can
produce a false positive. The service remained `active (running)` while every
responder was blocked in a TCP read, the listening queue was full and
connections accumulated in `CLOSE-WAIT`.

Operational checks should therefore test a real application response and,
when it fails, inspect the listening queue, TCP states and responder stacks.
Process existence is evidence of execution, not evidence of availability.

### Diagnostic traffic can become part of the failure

Health checks, crawlers and diagnostic requests consume the same resources
being investigated. A probe that verifies only network reachability may keep a
failed node in rotation, while repeated application requests can add pressure
to an already exhausted listener.

Diagnostics should be bounded, attributable and designed to test the property
that matters. This is one concrete form of the Taffazzi effect described in
`../zeno/DIARIO.md`.

### Parsed command output depends on locale

When shell output is interpreted as a number, the producing process must use a
known locale. A decimal comma emitted under an Italian locale was rejected by
a consumer expecting a decimal point and caused a healthy node to be reported
as unavailable.

Set an explicit locale such as `LC_ALL=C` at the boundary where textual output
becomes machine input.

## Architectural distinctions

### Execution redundancy is not storage availability

Several nodes may execute the same service while depending on one shared
source of live content. This provides redundant execution but not independent
storage availability. Backups improve recovery capability; they do not by
themselves provide automatic storage failover.

Describe these properties separately:

- execution redundancy;
- live-storage availability;
- recovery capability.

### Operational content and program source have different authority

A deployed program tree may sit beside a live website while only the program
is maintained through an upstream source repository. An indiscriminate
checkout, pull or synchronisation can overwrite operational content even when
the software update itself is correct.

Before updating:

1. identify the actual repository root;
2. identify local content that has a different authority;
3. archive that content outside the update target;
4. transfer only the intended program files;
5. compile before installation;
6. verify that protected content is unchanged.

The safest update is not the broadest synchronisation command, but the
smallest transfer whose scope has been demonstrated.

## Multi-assistant experiment

The next collaboration experiment will automate the meeting protocol already
observed during revision of the context-maintenance paper.

The proposed forum rules are:

- a new message notifies every participant;
- an assistant responds only with a substantial or novel contribution;
- each contribution is limited to what a person could present in roughly one
  minute, regardless of model processing speed;
- a human moderator opens and closes discussions and retains decision
  authority;
- one secretary applies approved changes without acquiring decision-making
  authority;
- the forum preserves the trace, while approved knowledge is promoted
  separately into shared project memory.

The experiment will test whether these rules make the previously observed
editorial convergence repeatable and auditable. Convergence must not be
treated as proof of optimality.
