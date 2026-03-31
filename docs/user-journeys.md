# User Journeys

This document keeps the roadmap anchored to how Primer is meant to be used in practice.

## 1. Engineer Coaching Journey

Goal: help an individual engineer improve outcomes during and after AI-assisted work.

1. Open **My Profile** to see effectiveness, friction, quality, cost, and the personal impact
   review.
2. Open **Growth** to review workflow playbooks, exemplars, reusable assets, and learning paths.
3. Start a new task with the **MCP sidecar** and use session-start coaching before the first edit.
4. Use **live session signals** and **in-session nudges** when the work starts drifting or
   repeating failures.
5. Open **Sessions** afterward to inspect the transcript, recovery path, and delegation details.
6. Review **personal recaps** and turn a recommendation into an **Intervention** when there is a
   concrete change to try.

Success signal:
- higher effectiveness score
- lower repeated friction
- better quality outcomes
- reduced cost per successful outcome
- fewer post-merge issues from the engineer's work

## 2. Team Lead Coaching Journey

Goal: identify repeatable high-value patterns and standardize them across the team.

1. Start in **Growth**, **Compare**, or **Code Quality** to spot who or what needs attention.
2. Open **Growth** to see bright spots, exemplars, reusable assets, and team skill gaps.
3. Open a **Project** workspace to understand where readiness, workflow friction, or repo context
   is blocking the team.
4. Use **project playbook templates** and workflow playbooks to define the default path for the
   repo or work type.
5. Create a project- or team-scoped **Intervention** or **experiment**.
6. Return later to the **manager review pack**, **Compare**, and **Interventions** views to decide
   whether to standardize the change.

Success signal:
- better adoption of successful workflows
- fewer repeated bottlenecks on key projects
- improved team-level effectiveness, quality, and post-merge stability

## 3. Platform / Admin Enablement Journey

Goal: improve the environment around engineers, not just individual behavior.

1. Start in **Admin** at the activation and setup hub to verify GitHub, budgets, alerts,
   narratives, and data freshness.
2. Use **AI Maturity** and **Projects** to find the tool, customization, and repo-level blockers
   reducing effective AI usage.
3. Review **alert policy management** so the actual runtime detector behavior matches what the team
   expects.
4. Launch an **Intervention** for repo docs, toolchain fixes, permissions, templates, or workflow
   playbooks.
5. Measure whether the project or team became easier, safer, and cheaper to work in.

Success signal:
- higher repo readiness
- lower friction in repeated workflows
- more consistent outcomes across projects
- fewer activation or measurement gaps across the platform

## 4. Leadership Review Journey

Goal: decide where AI is compounding engineering output and where corrective action is needed.

1. Start in **Admin** performance views or **Compare** to review productivity, quality, cost, and
   adoption in one frame.
2. Open **Code Quality** to inspect workflow-based quality attribution and post-merge outcomes.
3. Open **FinOps** to inspect workflow economics, compare mode, and model-choice opportunities.
4. Review the **manager review pack** to understand what changed this week and what the top actions
   are.
5. Use **Interventions** to translate the highest-confidence opportunities into measurable rollout
   decisions.

Success signal:
- more spend allocated to workflows that hold up after merge
- fewer regressions, reverts, and hotfixes
- clearer evidence for where to standardize or retrain

## 5. Project Enablement Journey

Goal: help a repository become easier to use effectively with AI.

1. Open the **Project Workspace**.
2. Review readiness, repository context, workflow fingerprints, friction hotspots, quality, cost,
   and post-merge outcomes.
3. Inspect **enablement recommendations** and the new **playbook templates** for the repo type:
   greenfield, legacy, high-compliance, or test-poor.
4. Turn the strongest recommendation or template into an **Intervention**.
5. Revisit the project later to confirm that workflow quality, cost efficiency, and stability
   improved.

Success signal:
- higher project readiness
- lower workflow friction
- better cost and quality on project-linked sessions
- fewer stabilization PRs after merge

## 6. Interactive Tour Outline

Primer should eventually ship a short guided tour that follows the product loop:

1. **Profile**
   Show effectiveness, trajectory, friction, and the personal impact review.
2. **Growth**
   Explain bright spots, playbooks, exemplars, and reusable assets.
3. **Project Workspace**
   Show how repo readiness, templates, and bottlenecks shape outcomes.
4. **Code Quality / FinOps**
   Show workflow proof across quality, cost, and post-merge stability.
5. **Interventions**
   Show how recommendations turn into tracked changes and experiments.
6. **MCP Sidecar**
   Close with session-start coaching, live signals, nudges, and recaps.

## 7. How To Use This With The Roadmap

Before shipping a new roadmap item, answer:

- Which user does this primarily help?
- Which page or in-workflow moment should expose it?
- What decision becomes easier because of it?
- What metric should move if it works?
- How does it connect to the rest of the loop: insight -> action -> measurement?

If a feature cannot be placed in one of these journeys, it likely needs a clearer product role
before implementation.
