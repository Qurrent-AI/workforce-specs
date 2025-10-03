# Roofstock Move-Out Workforce

**Contributors:** Alex Reents, Simon-Qurrent, VM, Stuti Shekhar, Alex McConville, augustfr, gyrolib, August Rosedale, alexmcconville2, eskild

## Overview
This workforce automates resident move-out workflows for Mynd/Roofstock. It consumes webhook events describing a workflow step, selects the appropriate console workflow, gathers case context from internal APIs or Otto (the case system), uses technical LLM agents to make step-specific decisions, maps those decisions into the exact API shape expected by Roofstock, optionally sends messages or notices to residents, and posts the result back to Roofstock. A separate browser-driven workflow autonomously operates within Otto to read/update case data and complete sub-tasks, with SLA-aware reassignment and human escalation.

## Custom Instructions
*FDE-provided instructions for how this particular workforce specification should be configured*
<!--
Preserve RXM business rules in agent prompts; do not alter decision criteria without stakeholder approval. If step inputs change upstream, update Flexible API mapping and expected input extraction. Browser actions must only target supported subtasks; expand action set via agents/actions when Otto UI changes.
-->

## Decision Audit

Documents the possible paths of workflow execution through the lens of decisions the workforce makes.

- [1] Select workflow for incoming step
    - Inputs: Webhook payload with workflow and step metadata (type, id)
    - Outputs: Chosen console workflow instance; run/close lifecycle
    - Decision logic: Map step type to a specific workflow; skip if unknown
    - Logic location: internal code (orchestrator)
- [2] Determine expected answers for the step
    - Inputs: Step configuration (userInputConfigs) from webhook payload
    - Outputs: Lists of questions, field names, options, and conditions
    - Decision logic: Extract structured expected inputs from step config
    - Logic location: internal code (console observable)
- [3] Gather required case context (API-based)
    - Inputs: Workflow/step ids
    - Outputs: Move-out details, communication details, housing assistance, property access
    - Decision logic: Call internal API endpoints with HMAC headers; return structured data
    - Logic location: internal code (console observables)
- [4] Make step-specific recommendation
    - Inputs: Step questions; fetched details; current date; days until move-out (when relevant)
    - Outputs: Structured answers and optional message content
    - Decision logic: Apply RXM rules contained in prompts to produce decisions; may include waiting guidance and reminders
    - Logic location: internal prompt (technical agent)
- [5] Map recommendation to API response contract
    - Inputs: Agent response; expected questions/fields/options/conditions
    - Outputs: API payload containing stepData and extracted reasoning
    - Decision logic: Transform agent response to exact field names and options; include reasoning
    - Logic location: internal code plus internal prompt (technical agent)
- [6] Send resident communication when indicated
    - Inputs: Agent response flags and message
    - Outputs: Case message sent or nonrenewal notice issued
    - Decision logic: If agent indicates communication is needed, perform the corresponding API call
    - Logic location: internal code (console observables)
- [7] Complete step with Roofstock
    - Inputs: API payload with decision
    - Outputs: HTTP status; failure raises error, 400 marks mapping issue
    - Decision logic: Consider 2xx as success; on 400, flag incorrect mapping; otherwise raise
    - Logic location: internal code (console observable)
- [8] Browser task orchestration and escalation
    - Inputs: Otto task assignments, tracked tasks, SLA rules, case/task context
    - Outputs: Completed/Waiting/Escalated status; metrics and identifiers
    - Decision logic: Run planned console steps; if SLA breached or case closed, escalate or complete; ensure one action at a time; re-run on agent directives
    - Logic location: internal code (console agent/observables) with internal prompts (technical agents)
- [9] LLM-invoked browser actions
    - Inputs: Action parameters (e.g., messages, Q&A key-values)
    - Outputs: UI side-effects in Otto; updated context
    - Decision logic: Technical agent decides which action to invoke and with what arguments
    - Logic location: internal prompt (technical agent with @llmcallable actions)

## Agent Design

### Console Agents

#### `review_move_out_agent`
**Type:** Console Agent (method with `@console_agent` decorator)
**Purpose:** Review a portal move-out for approval/type and respond to Roofstock
**Docstring:** "This agent reviews the move out and returns a decision based in the move out details and RXM instructions."

**Observable Tasks:**

**`get_expected_response_fields()`**
- `@observable` decorator
- Docstring: "Extracting questions, field names, options, and conditions from step expected inputs."
- Purpose: Parse expected step input spec for subsequent mapping
- Technical Agent Calls: Calls `api_agent.map_api_response()` for flexible mapping later
- Integration Calls: Calls none
- Observability Output: `save_to_console(type='observable_output', content="[OBSERVATION] ...")`
- Returns: Tuple of lists (questions, fields, options, conditions)

**`get_move_out_details()`**
- `@observable` decorator
- Docstring: "Requesting move out details from Roofstock API."
- Purpose: Fetch core move-out data
- Integration Calls: `RoofstockAPI.request_move_out_details()`
- Observability Output: Saves details
- Returns: Dict of details

**`make_decision()`**
- `@observable` decorator
- Docstring: "Making a decision based on the move out details and RXM instructions."
- Purpose: Invoke technical agent to decide
- Technical Agent Calls: `ReviewMoveOutAgent.review_move_out()`
- Returns: Dict decisions/message flags

**`flexible_response_mapping(...)`**
- `@observable` decorator
- Purpose: Map agent response to API schema
- Technical Agent Calls: `FlexibleApiAgent.map_api_response()`
- Returns: Dict API payload

**`send_case_message(message)`**
- `@observable` decorator
- Purpose: Send resident message when requested by agent
- Integration Calls: `RoofstockAPI.response_send_message()`
- Returns: bool

**`respond_to_roofstock(decision)`**
- `@observable` decorator
- Purpose: Complete the step with Roofstock
- Integration Calls: `RoofstockAPI.response_complete_step()`
- Returns: bool

### Technical Agents

#### `ReviewMoveOutAgent`
**Type:** Technical Agent (extends `Agent` class)
**Pattern:** Task
**Purpose:** Produce approval/type decision and resident messaging guidance
**LLM:** model from YAML (`gpt-4o-2024-08-06`), standard mode, temp=0

**Prompt Strategy:**
- Follow RXM rules for approval and move-out type
- Provide concise JSON with explanation and fields; message when needed
- Context: accumulates; move-out details and response questions appended as user messages
- JSON Response: includes explanation, typed fields, and optional message/send flag

**Instance Attributes:**
- `yaml_config_path`: str - prompt/config source
- `workflow_instance_id`: UUID - routing

**Create Parameters:**
- `yaml_config_path`: str - path to agent YAML
- `workflow_instance_id`: UUID - from workflow

#### `FlexibleApiAgent`
**Type:** Technical Agent (extends `Agent`)
**Pattern:** Task
**Purpose:** Transform agent outputs into API `stepData` plus reasoning
**LLM:** model from YAML, standard mode, temp=0

**Prompt Strategy:**
- Show input agent response and expected questions/fields/options/conditions
- Ask for mapped fields and reasoning
- Context: accumulates
- JSON Response: `{reasoning, <fields...>}` which is wrapped into `stepData`

#### Direct Actions

**`StepWorkflow.respond_to_roofstock(decision) -> bool`**
- Purpose: POST step completion payload
- Message Thread modification:
    - Observability output of decision, status, body
- Integration usage:
    - `RoofstockAPI.response_complete_step`
- Returns: True on success; raises on non-2xx; flags mapping issues

**`StepWorkflow.send_case_message(message: str) -> bool`**
- Purpose: POST a case message
- Observability output of message and status
- Integration usage: `RoofstockAPI.response_send_message`
- Returns: True

**`StepWorkflow.send_nonrenewal_notice() -> bool`**
- Purpose: Trigger nonrenewal notice
- Integration usage: `RoofstockAPI.response_send_nonrenewal_notice`
- Returns: True

#### LLM Callables

Representative calls in the browser workflow technical agent (`MoveOutAgent`):

**`get_all_case_messages() -> str`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Purpose: Fetch case messages for context
- Integration usage: Browser automation via `BrowserAgent`
- Returns: JSON string of messages

**`complete_review_move_out_subtask(questions_and_answers: dict) -> str`**
- `@llmcallable(rerun_agent=True)`
- Purpose: Fill and submit a subtask form in Otto
- Integration usage: Browser automation
- Returns: Confirmation string

Many additional callable actions exist for updating acknowledgement, forwarding address, deposit methods, approvals, and processing portal/non-portal move-outs; each invokes a browser action and returns a short status string.

### `PMOIReviewResponseAgent`, `CollectAdditionalInfoAgent`, `CollectSODAInfoAgent`, `ProcessRejectionAgent`, `SendResidentKeyInfoAgent`, `MoveOutCancellation...` Agents
- Type: Technical Agents (extend `Agent`)
- Pattern: Task
- Purpose: Produce step-specific decisions and messaging guidance per YAML rules
- LLM: Model per YAML; standard mode, temp=0

## Happy Path Call Stack

```text
→ START EVENT: events.GenericWebhookEvent "Roofstock step payload"
  ├─ @console_agent: orchestrator.handle_event() selects StepWorkflow subclass (CA)
  │  └─ @console_agent: [Workflow].<step_console_agent>() (CA)
  │     ├─ @observable: StepWorkflow.get_expected_response_fields()
  │     ├─ @observable: StepWorkflow.get_*_details()
  │     ├─ [TechnicalAgentInstance]() make_decision (TA LLM turn)
  │     ├─ @observable: StepWorkflow.flexible_response_mapping()
  │     ├─ @observable: StepWorkflow.send_case_message() [conditional]
  │     └─ @observable: StepWorkflow.respond_to_roofstock()
→ INGRESS EVENT: Otto task available/assigned "browser task"
  ├─ @console_agent: BaseBrowserWorkflow.mynd_ai() (CA)
  │  ├─ @observable: get_page_urls()/check_original_assignee()/check_task_due_date()
  │  ├─ @observable: check_case_status_closed() → early complete/escalate
  │  ├─ @observable: get_reassignment_datetime() via SLA agent (TA)
  │  ├─ @observable: get_task_context()/get_per_run_context()
  │  └─ @observable: complete_subtasks() → TA LLM turn with @llmcallables
→ WORKFLOW COMPLETE: Step POST succeeds or browser task completed/escalated
```

## Data & Formats

### Referenced Documents Inventory and Input Data
- Roofstock step payload
    - Format: JSON
    - Source: Webhook via GenericWebServerIntegration
    - Intended Use: Drive workflow selection and expected input extraction
- Move-out/communication/housing/access details
    - Format: JSON
    - Source: Internal API (HMAC headers)
    - Intended Use: Inputs to step decision agents
- Otto case pages and forms
    - Format: HTML/UI state via browser automation
    - Source: Otto application
    - Intended Use: Read/update case context; complete subtasks

### Example Output Artifacts
- Step completion response
    - Type: API call result
    - Format: JSON payload with `stepData` and `aiReasoning`
    - Recipients: Roofstock workflow API
    - Contents: Fielded answers mapped to expected schema
- Resident message/notice
    - Type: Case message or nonrenewal notice
    - Format: Text or system-triggered notice
    - Recipients: Resident via Otto/portal
    - Contents: Polite, professional message per agent guidance

## Integrations

### Prebuilt: `qurrent.Slack`
- Required Config Section: N/A (uses QurrentConfig)
- Required Keys:
    - `SLACK_CHANNEL_ID`: string - posting channel

### Prebuilt: `qurrent.WebServer` and `qurrent.Ingress`
- Required Config Section: N/A (from QurrentConfig)
- Required Keys:
    - Ingress wiring present; webhook route `/webhook`

### Custom: `RoofstockAPI`
**Location:** `roofstock/app/roofstock_api.py`
**Type:** One-way (reads details, posts results)

**Config Section:** QurrentConfig
- `ROOFSTOCK_API_KEY`: provided via config/env - HMAC secret
- `ROOFSTOCK_API_URL`: base URL override (optional)

**Methods:**

**`request_move_out_details(workflow_id: str) -> Dict`**
- Performs: GET details for a move-out
- Behavior: Retries with exponential backoff; validates response type
- Returns: Dict

**`response_complete_step(workflow_id: str, step_id: str, payload: Dict) -> (int, str)`**
- Performs: POST step decision
- Behavior: Returns status/text; 2xx treated as success by caller
- Returns: Status code and body

**`response_send_message(workflow_id: str, step_id: str, payload: Dict) -> (int, str)`**
- Performs: POST case message
- Returns: Status code and body

**`response_send_nonrenewal_notice(workflow_id: str) -> (int, str)`**
- Performs: POST nonrenewal notice action
- Returns: Status code and body

## Utils

**`DatePicker.pick_date(start_date: date, days: int, skip_holidays: bool=True) -> date`**
- Purpose: Compute reminder date excluding non-working days
- Implementation: Uses `workalendar` US calendar to count working days
- Dependencies: `workalendar`

## Directory Structure

```text
roofstock/
  app/
    date_picker.py
    roofstock_api.py
    roofstock_types.py
    slack_context.py
  workflows/
    agents/
      config/ (YAML prompts per step)
      *.py (technical agents)
    *workflow.py (console workflows)
    step_workflow.py (shared console observables and API mapping)
  browser_workflows/
    base_browser_workflow.py (console agent + observables)
    move_out/
      agent.py (technical agent with @llmcallables)
      actions/ (browser automation steps)
      helper_agents/ (SLA, image)
      workflow.py (OttoBrowser)
```
