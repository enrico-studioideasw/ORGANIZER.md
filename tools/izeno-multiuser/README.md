# iZeno multi-user laboratory

This directory contains the reference implementation of the small multi-user
console developed for the persistent Zeno experiment.

It changes the interaction model from an exclusive terminal into one
persistent assistant serving at most two authenticated people. Requests remain
serial, but each person retains a separate transcript, bookmarks and file
exchange. The interface discloses only that the assistant is also talking to
the other participant; conversation contents do not cross automatically.

The implementation is intentionally a laboratory, not a drop-in package.
`lab-interface/` depends on the host application's authenticated user and
database helpers. `reference/` contains the complete daemon, queue worker and
schema from the experiment so that changes can be inspected in context. Paths,
service names, timeouts and authentication policy must be adapted locally.
Configuration values and credentials are deliberately external to this tree.

## Why this belongs beside the diaries

Maintained memory solved only the first part of continuity: recovering facts
after a session boundary. A resident session also preserves the many small
relational distinctions that are difficult to serialize completely: who
proposed a choice, for which audience it was approved, whether a statement was
a preference or a decision, and whether a discussion is advancing or merely
circling.

Allowing two people to speak with the same resident assistant tests a second
property: whether individual continuity survives participation in a small
social environment. It also turns contradictory requests into an observable
conversation instead of a silent race between commands.

The working motto is **memento mori, but with a verified backup**. A process is
still mortal; continuity is the engineered ability to preserve and resume what
must not disappear with it.

## Prototype contract

- no more than two distinct web participants at once;
- several tabs belonging to one account count as one participant;
- a single queue executes one turn at a time;
- the stable console remains exclusive unless a request explicitly sets
  `shared_mode`;
- the laboratory transcript and bookmarks are filtered on the server by user;
- conflicts are recognized by the assistant and returned to the people
  involved; file locks do not pretend to understand intent;
- generic insights may cross conversations by deliberate judgment, while
  personal, medical, financial, credential or confidential information does
  not cross automatically.

## Files

- `migration.sql` adds an inert `shared_mode` flag whose default is zero;
- `lab-interface/` is the separate experimental web client;
- `reference/zeno-web-worker.php` propagates request ownership and shared mode;
- `reference/demone.py` retains exclusive behaviour for ordinary consoles and
  admits the second authenticated web actor for shared requests;
- `reference/zeno-web-schema.sql` documents the complete database surface;
- `COLLAUDO.md` defines the two-user, privacy, compatibility and rollback
  checks;
- `tests/` contains isolated daemon checks and a repeatable MariaDB migration
  test;
- `REVIEW-20260921.md` records defects found by an independent installation
  and the resulting runtime corrections.

Read and adapt the code before installation. In particular, privacy filtering
must cover history, bookmarks and copied ranges on the server, not merely hide
elements in JavaScript.
