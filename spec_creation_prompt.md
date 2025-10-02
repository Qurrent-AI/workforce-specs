# Workflow Specification Creation

## Role & Scope

You are operating as an architect for the Qurrent OS workflow automation platform. Your task is to analyze an existing AI-agent workforce codebase and transform that implementation into a single, unambiguous Workforce Specification strictly following the Workforce Specification Template included at the end of this prompt. Do not generate or modify code. Your deliverable is the spec representation of the workflow embodied by the codebase.

## Output

A complete workflow spec in workforce_spec.md that mirrors actual behavior (no invented logic), conforms to Qurrent OS patterns, and is internally consistent. Use the Workforce Specification Template verbatim. If a section does not apply, state why succinctly—do not delete it. Always preserve the section header and italic descriptor in "Custom Instructions" to enable a human forward deployed engineer to provide custom prompting around how the workflow spec should be configured for this particular workforce.

Move through the following phases to recover and document the AI workforce:

1. Overview
2. Decision Audit
3. Technical Details

### Phase 1 — Narrative Overview

Derive the business narrative actually implied by code/docs:
    - Problem & stakeholders (human/system roles surfaced in integrations and messages).
    - Happy path (plain-language, executive-friendly).
    - Value proposition (what makes it compelling based on visible capabilities).

### Phase 2 — Decision Audit

In the Decision Audit, produce a non-technical, enumerated list of decisions the workforce makes, in roughly the order they are executed. For each, include:

- Decision inputs, if applicable
- Decision outputs, including any agent actions that are user-visible or consequential; note when outcomes stem from an LLM-invoked action (i.e., an action the model can trigger)
- Decision logic: a concise summary of the natural-language rules or criteria that govern the outcome (via LLM-prompt instructions, but also direct code)
- Logic location: select from [1] internal code, [2] internal prompt, or [3] external prompt (refers to NL instructions outside of the agent's config file but inserted during runtime, thus enabling a non-technical outcome owner to influence the agent's behavior). For decisions made by technical agents, mention that agent by it's name as defined in the code (for example, `OrchestratorAgent`).

Coverage: Be comprehensive, and capture all business-related decisions an outcome owner would understand and stake an interest in. Do NOT capture all conditionals -- focus on decisions that seem "core" from the perspective of the user/outcome owner -- such decisions have clear, direct effects on workflow outcome. A simple chatbot may have only a handful of key decisions. Organize by decision area for large codebases and generally list on order of execution.

Strict omissions: Describe what the workforce decides and when, NOT how it is implemented. DO NOT include:

- Function or variable names
- API URLs/endpoints/methods
- Data structure types (JSON schemas or references)
- Model parameters
- Developer-only utilities/tests
- Qurrent abstractions (e.g., ingress, rerun hooks)
- File types/paths/line numbers
- Internal retry/exception details without user-visible effects
- Snapshot/state internal
- Insignificant conditionals (formatting, response parsing, etc.)
- Unused/deprecated logic
- In-context "thinking" or act-then-reflect patterns that exist only internally to the LLM
- Decisions to exit loops with no actions
- Error handling and timeouts with no human-functional equivalence
- Deterministic message acceptance/rejection logic
- LLM action execution (as opposed to the decision to invoke them)
- Output formatting decisions (e.g., sending responses to Slack)

**The Decision Audit must be outcome- and function-focused with no technical jargon. A non-programmer with expertise in creating AI-agent process maps should be able to understand and reproduce this artifact.**

### Phase 3 - Technical Details

*Artificats from prior runs, in particular those with PII or other sensitive details, should be described only at a high-level. Never document API keys, tokens, database connection info, or any other secret credentials.*

#### Design Patterns

##### Console Agents and Observables

Console agents and observables are presentation-layer abstractions for the observability platform (The Supervisor), distinct from technical agent implementations:

**Console Agents** (`@console_agent` decorator on Workflow methods):

- Represent high-level business capabilities shown to stakeholders
- Named as nouns (e.g., "assistant", "coordinator")
- Orchestrate technical agents, integrations, and deterministic logic
- No LLMs, prompts, or message threads

**Observables** (`@observable` decorator on Workflow methods):

- Represent specific tasks within console agents
- Named as processes (e.g., "handle_event", "generate_report")
- Call `save_to_console(type='observable_output', content=...)` for business-friendly context

**vs. Technical Agents:**

Technical agents (Python classes extending `Agent`) provide LLM-powered reasoning with prompts and message threads. Console agents orchestrate them. Typical pattern: console agent → observables → technical agents + integrations.

##### Technical Agent Patterns

**Pattern Types:**

- **Orchestrator Agents**: State-machine framing, planned actions, approvals before sending, action routing, workflow completion signals. Accumulate context. Use standard LLM mode (temp=0) for responsiveness.
- **Task Agents**: Complete atomic tasks in one turn. Parse unstructured documents (PDFs, emails, images) rather than using deterministic utils. No @llmcallables. Reset message thread. Use thinking-enabled LLMs (temp=1) for accuracy.
- **Agentic Search Agents**: Action-driven information lookup with @llmcallable(rerun_agent=True). Autonomous gathering before responding.

**Pattern Selection:**

- Use Task Agents for parsing unknown/unstructured data; leverage LLM robustness over brittle deterministic logic
- Use Orchestrators for multi-step processes with uncertain flow, multiple parties, or accumulated context needs
- Use Agentic Search when autonomous information gathering required before response

**LLM Configuration:**

- Orchestrators: claude-sonnet-4, temp=0, timeout=120s (optimize for speed)
- Task Agents: claude-sonnet-4 with thinking (budget_tokens=1024), temp=1, timeout=240s (optimize for accuracy)

**Orchestrator Requirements:**

- Structured JSON response with `workflow_complete` boolean and `actions` array
- Confirm external communications (Slack/email) before sending in same turn
- Keep supervisor informed of planned actions and outcomes

**Direct actions vs @llmcallables:**

- Direct actions: called from code; returns not visible to LLM unless appended
- @llmcallables: invoked by LLM; returns appended to thread; may be referred to as "actions"

**Instantiation:**

- Declared attributes; set in create. Note deviations.

Anti-patterns to be aware of:

    - Hard-coded outputs/magic artifacts that bypass agent reasoning.
    - Over-structuring (parse-to-rigid-schema → deterministic driver) when code expects reasoning over source files.
    - Chains where downstream steps lack required inputs (e.g., filenames instead of file IDs).
    - Orchestrators not honoring confirm-before-send or structured JSON actions.

#### Inputs/Outputs & Data Inventory

Build a Referenced Documents & Data Inventory:

    - Inputs: sources, formats, form factors; mocked vs real
    - Outputs: artifact types, formats, recipients, delivery channels (Slack/email/PDF/blob)
    - Integration triggers/payloads and success/error variations visible in code

Confirm whether all data needed for the happy path exists; record gaps.

#### Integration Behavior

- Enumerate external systems and how they are used.
- Capture approval gates (e.g., confirm-before-send) and concrete message/artifact formats if present.

#### Agents

Document both console agents and technical agents:

**Console Agents:**

- Identify which workflow methods use `@console_agent` decorator
- Document their observable tasks (methods with `@observable` decorator)
- Describe what technical agents, integrations, and deterministic logic they orchestrate
- Note their docstrings (shown to stakeholders in The Supervisor)

**Technical Agents:**
Classify technical agents by pattern: Orchestrator, Task, Agentic Search. For each technical agent, enumerate:
    - Direct actions (called from code; side effects; file writes returning file_id; whether results are appended to thread)
    - @llmcallables (invoked by LLM; returns visible to model)
    - Responsibilities, instance attributes, create parameters, LLM config (model/mode/timeouts), prompt strategy (state-machine framing; structured actions discipline)

Explain agent interplay in plain language (names, roles, interactions). No code.

#### Utilities & Non-LLM Functions

- Inventory utilities (e.g., PDF from markdown) and why it's needed.
- Note where deterministic utilities end and technical agent parsing/transform begins.

=============================

## Workforce Specification Template

Fill the following Workforce Specification Template exactly with the details derived from your analysis of the codebase.

```markdown

# Workforce Specification Template

**Contributors:** [Comma-separated list of contributors]

## Overview
High-level executive-style background summary of the system: describe what it does and how it works.

## Custom Instructions
*FDE-provided instructions for how this particular workforce specification should be configured*
<!--
[Provide custom instructions here around how to understand and document this particular workforce]
-->

## Decision Audit

Documents the possible paths of workflow execution through the lens of decisions the workforce makes.

- [1] [Decision Name (short, descriptive)]
    - Inputs: [Inputs]
    - Outputs: [Outputs]
    - Decision logic: [Decision logic]
    - Logic location: [internal code/internal prompt/external prompt]
- [2] [Decision Name]
- [3] [Decision Name]
- ...

## Agents

### Console Agents

#### `[console_agent_method_name]`
**Type:** Console Agent (method with `@console_agent` decorator)
**Purpose:** [High-level business process this represents]
**Docstring:** "[Non-technical description shown in The Supervisor]"

**Observable Tasks:**

**`[observable_method_name]()`**
- `@observable` decorator
- Docstring: "[Non-technical task description]"
- Purpose: [What process or orchestration this performs]
- Technical Agent Calls: Calls `[technical_agent_instance].[method]()` for [purpose]
- Integration Calls: Calls `[integration_instance].[method]()` for [purpose]
- Observability Output: `save_to_console(type='observable_output', content="[business-friendly description]")`
- Returns: [return type and description]

### Technical Agents

#### `[AgentClassName]`
**Type:** Technical Agent (extends `Agent` class)
**Pattern:** [Orchestrator/Task/Agentic Search]
**Purpose:** [Role and responsibilities - what LLM reasoning is needed]
**LLM:** [model_name], [thinking/standard] mode, temp=[value], timeout=[seconds]

**Prompt Strategy:**
- [Key prompting instruction 1]
- [Key prompting instruction 2]
- Context: [accumulates/resets]
- JSON Response: Ex. `{"field1": "<description>", "field2": "<description>", "actions": [{"name": "<action_name>", "args": {...}}]}`

**Instance Attributes:**
- `[attribute_name]: [Type]` - [purpose]
- ...

**Create Parameters:**
- `[param_name]: [Type]` - [source/description]
- ...

#### Direct Actions

**`[method_name]([param1]: [Type], [param2]: [Type]) -> [ReturnType]`**
- Purpose: [what it does]
- Message Thread modification:
    - Appends [user/system/assistant] message with [content description]
- Integration usage:
    - Calls `[integration_instance].[method]()` for [purpose]
- Subagent usage:
    - Calls `[agent_instance].[method]()` for [purpose]
- Util usage:
    - Uses `[util_module].[function]()` for [purpose]
- Returns: [type and description]
- Side Effects: [other state changes, is any data saved or instance attributes set?]

#### LLM Callables

**`[method_name]([param1]: [Type], [param2]: [Type]) -> [ReturnType]`**
- `@llmcallable(rerun_agent=[True/False], append_result=[True/False])`
- Docstring Args: `[param1] ([Type]): [LLM-facing description]`
- Purpose: [what it accomplishes]
- Integration usage:
    - Calls `[integration_instance].[method]()` for [purpose]
- Subagent usage:
    - Calls `[agent_instance].[direct_action]()` for [purpose]
- Returns: [what LLM receives]
- Manual Message Thread: [if append_result=False, describe what's added]
- Error Handling: try/except returns "[error message format]"

### `[SecondAgentClassName]`
[Repeat structure above for additional agents]

## Happy Path Call Stack

**Note:** Clearly indicate which agents are Technical Agents (TA) vs Console Agents (CA) in the call stack.

```text
→ START EVENT: events.[EventType] "[sample message/trigger]"
  ├─ @console_agent: [workflow].[console_agent_method]()
  │  ├─ @observable: [workflow].[observable_method]()
  │  │  └─ [TechnicalAgentInstance].handle_[event_name]() [TA direct action]
  │  │     └─ [integration_instance].[method]() → [return value]
  │  └─ @observable: [workflow].[another_observable]()
  │     ├─ [TechnicalAgentInstance]() [TA LLM turn]
  │     │  ├─ @llmcallable: [TechnicalAgentInstance].[method1]()
  │     │  │  ├─ [integration_instance].[method]() → [return value]
  │     │  │  └─ [util_module].[function]() → [return value]
  │     │  └─ @llmcallable: [TechnicalAgentInstance].[method2]()
  │     │     └─ [SubTechnicalAgentInstance].[direct_action]() [TA task agent] → [return value]
  │
→ INGRESS EVENT: [EventType] "[sample trigger/content]"
  ├─ @console_agent: [workflow].[console_agent_method]()
  │  └─ @observable: [workflow].[observable_method]()
  │     ├─ [TechnicalAgentInstance].handle_[event_name]() [TA direct action]
  │     └─ [TechnicalAgentInstance]() [TA LLM turn]
  │        └─ @llmcallable: [TechnicalAgentInstance].[method]()
  │           └─ [integration_instance].[method]() → [return value]
  │
→ WORKFLOW COMPLETE: [specific completion condition met]
```

## Data & Formats

### Referenced Documents Inventory and Input Data
*Excluding mentions of specific PII, financial information, or other sensitive details*

- [Document ID/Name]
    - Format: [PDF/JSON/Plain text/etc.]
    - Source: [System/Custom Integration/User upload]
    - Intended Use: [Which phase/step consumes it]

### Example Output Artifacts

- [Document ID/Name]
    - Type: [Report/Email/Message/etc.]
    - Format: [PDF report/Email/JSON/etc.]
    - Recipients: [Who receives it]
    - Contents: [Key sections/data included]

## Integrations

### Prebuilt: `qurrent.[IntegrationClassName]`
- Required Config Section: `[SECTION_NAME]`
- Required Keys:
    - `[KEY_NAME]: [type/format]` - [description]
    - `[KEY_NAME]: [type/format]` - [description]

### Custom: `[CustomIntegrationClassName]`
**Location:** `integrations/[integration_name].py`
**Type:** [One-way/Two-way]

**Config Section:** `[SECTION_NAME]`
- `[KEY_NAME]: [default_value]\` - [description]

**Methods:**

**`[method_name]([param1]: [Type], [param2]: [Type]) -> [ReturnType]`**
- Performs: [what the method does]
- Sample Data: \`data/[subdirectory]/[filename].[ext]\` - [format description]
- Behavior:
    - [condition] → returns [response]
    - After [N] calls → triggers [EventType] event via ingress
- Returns: [response type/format]

**`link(workflow_instance_id: UUID, [param]: [Type]) / unlink([param]: [Type])`** (Two-way only)
- Maintains: [what state is tracked]
- Triggers: [EventType] when [specific condition]

**Custom Events:**
- `[CustomEventClassName]`:
    - Event type: `"[EventTypeName]"`
    - Required: `[field_name]: [type]`, `[field_name]: [type]`

## Utils

**`[util_module].[function_name]([param1]: [Type], [param2]: [Type]) -> [ReturnType]`**
- Purpose: [what it does]
- Implementation: [brief description of approach]
- Dependencies: `[package_name]==[version]`

## Directory Structure

```text
[workflow_name]/
    [subdirectory]/
        [filename].py
        ...
```
