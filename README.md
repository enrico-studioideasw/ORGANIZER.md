# ORGANIZER.md
Maintained Project Memory: using ORGANIZER.md as an explicit, versioned knowledge base for AI-assisted software 

Enrico Betti
July 16, 2026


I have been using AI assistants such as ChatGPT and Codex for software development for several months. They have become extremely valuable tools, but I also noticed a recurring limitation.

A new session usually starts with only a partial understanding of previous work. Even when the model has access to project files, important architectural decisions, discarded approaches and practical lessons learned over time are often missing. Recovering this information repeatedly costs both time and attention.

This observation led me to experiment with a different approach.

# A project organizer instead of conversation history

Alongside the traditional AGENTS.md file, I introduced a persistent ORGANIZER.md ("project organizer").

At the beginning of every development session, Codex reads this file before starting any work.

Unlike a conversation log, the organizer contains only information that is expected to remain useful over time:

- architectural decisions;
- design constraints;
- proven procedures;
- implementation pitfalls;
- discarded hypotheses and the reasons they were abandoned.

It is not intended to replace project documentation, nor does it contain complete conversation histories.
Instead, it acts as a compact engineering memory.

# A hierarchical structure

The main organizer intentionally remains small.

Whenever a project grows, it simply references more specialized organizers dedicated to individual components or subsystems.

This keeps the primary context compact while allowing detailed knowledge to remain organized and easy to navigate.
Controlled updates

The organizer is not updated after every interaction.

New entries are added only when a session produces knowledge that is likely to improve future work:

- a decision that should remain stable;
- a recurring mistake worth avoiding;
- a reliable implementation pattern;
- an architectural constraint that should never be forgotten.

Personal information and unnecessary conversational details are intentionally excluded.

Because the organizer is an ordinary text file, it is:

- completely transparent;
- version-controlled together with the project;
- editable by the developer;
- easy to review or reorganize at any time.
- Periodic maintenance

An important addition is a scheduled review process.

Using a periodic cron task, Codex revisits the organizer and evaluates whether existing notes are still consistent with the current state of the project.

The review never changes architectural decisions automatically.

Instead, it identifies entries that appear obsolete, contradicted by later developments, or worthy of confirmation, leaving the final decision entirely to the developer.

As a result, the organizer becomes more than persistent memory.

It becomes maintained memory.

# Practical benefits

In daily development this approach has produced several advantages:
- much faster context recovery at the beginning of new sessions;
- fewer repeated discussions about decisions already taken;
- lower risk of reintroducing previously rejected solutions;
- improved continuity across long-running projects;
- explicit and auditable project knowledge.

The organizer evolves together with the software instead of simply accumulating information.

# A possible direction for AI development tools

This experience suggests that AI-assisted development could benefit from official support for explicit project memory.

Rather than relying only on hidden conversational context, development environments could provide dedicated tools for:

- proposing new organizer entries;
- reviewing suggested updates;
- organizing project knowledge;
- periodically validating existing information.

Such a system would keep long-term project knowledge transparent, versionable and fully under the developer's control.
In my experience, this has been one of the most effective improvements for maintaining continuity during AI-assisted software development.

Suggestions and discussion are welcome.

# Project continuity

The experiment is active. The maintained organizer is now being used during
the development and documentation of EWB, a small language built around a
string-oriented virtual machine. Recent work has clarified the contracts among
the VM, the language, persistent datasets, scheduled tasks, page threads and
the optional `ewIA` preprocessor.

The public examples are periodically aligned with reusable project knowledge.
Operational details, credentials and private infrastructure notes remain in
their local organizers and are deliberately excluded from this repository.

# Private operational data

Maintained memory sometimes needs to remember that an operational credential
exists and how it is used, without storing the credential itself. The
`tools/keyring/` example provides a small local encrypted keyring for this
purpose. Only logical entry names and procedures belong in version-controlled
memory; keys, vaults and secret values remain local to each machine.

# Multi-assistant laboratory

The repository now also explores maintained memory shared by more than one
assistant. `ORGANIZER.md` is the entry point, `shared/` contains reviewed
knowledge, and `agents/` keeps observations attributable to individual
assistants.

This separation avoids pretending that every assistant observation is already
a project decision. It also makes it possible to compare how several "small
Zenos" develop in different laboratories while retaining one human-governed
shared memory.
