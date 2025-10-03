# Roofstock Move-Out Workforce

**Contributors:** Alex Reents, Simon-Qurrent, VM, Stuti Shekhar, Alex McConville, augustfr, gyrolib, August Rosedale, alexmcconville2, eskild

## Overview
High-level executive-style background summary of the system: describe what it does and how it works.

This workforce automates Mynd/Roofstock’s resident move-out workflows across two execution modes:
- API-driven step workflows that receive webhooks for specific workflow steps (e.g., review move out, collect additional info) and return structured decisions back to the Roofstock API.
- Browser-driven workflows that operate Otto (Mynd’s property management system) to gather context and complete subtasks via a headless browser with LLM fallback.

Console agents orchestrate business flows and record observable outputs for stakeholders. Technical agents (LLM-backed) make decisions, transform responses into API payloads, and execute browser actions. Slack is used for operational alerts; metrics and identifiers are saved for observability. SLA-based reassignment logic escalates unresolved tasks.

## Custom Instructions
*FDE-provided instructions for how this particular workforce specification should be configured*
<!--
[Provide custom instructions here around how to understand and document this particular workforce]
-->

## Decision Audit

Documents the possible paths of workflow execution through the lens of decisions the workforce makes.

- [1] Route inbound workflow step to the correct business workflow
    - Inputs: Webhook event payload containing workflowId, step metadata (type/name/title/description), and URL
    - Outputs: Selected workflow started; run status (completed/failed) recorded; Slack alert on failure
    - Decision logic: Determine step type from payload and map to corresponding workflow class; ignore unknown types
    - Logic location: internal code
- [2] Determine required questions and response schema for the step
    - Inputs: Step expected inputs from payload (titles, field names, options, conditions)
    - Outputs: Lists of response questions, fields, options, and conditions surfaced to agent and console
    - Decision logic: Extract from step config and present as observable context for downstream decisions
    - Logic location: internal code
- [3] Gather reference details from Roofstock systems when needed
    - Inputs: workflowId for API queries
    - Outputs: Move-out details, communication history, housing assistance details, property access details
    - Decision logic: Fetch supporting data via authenticated API calls with retries; surface observations for the agent
    - Logic location: internal code
- [4] Make a step-specific decision using an agent
    - Inputs: Step questions, fetched details (move-out, communications, housing, access), date context
    - Outputs: Agent response containing explanation and step answers; optional resident message; optional wait/reminder options
    - Decision logic: Technical agent interprets details and instructions to produce compliant answers; some steps add scheduling logic (e.g., business-day reminders)
    - Logic location: internal prompt
- [5] Map agent response to Roofstock API response specification
    - Inputs: Agent response, questions, fields, options, conditions
    - Outputs: Structured payload with stepData and AI reasoning
    - Decision logic: Transform free-form agent answers into the API’s field/value schema honoring conditional enablement rules
    - Logic location: internal prompt
- [6] Decide whether to send a resident message within the step
    - Inputs: Agent response flags and message content
    - Outputs: Message posted via Roofstock API when requested
    - Decision logic: If agent sets send_message to Yes, send message using API and confirm status
    - Logic location: internal code
- [7] Complete the step in Roofstock API
    - Inputs: Mapped decision payload
    - Outputs: API acknowledgement (success or error) and console output; mark mapping errors
    - Decision logic: Submit decision; treat 2xx as success, otherwise surface errors and halt
    - Logic location: internal code
- [8] Determine rescheduling/reminder dates for time-shifted actions
    - Inputs: Agent-provided days_to_wait and current date
    - Outputs: Calculated reminder_date (business days when applicable) or None
    - Decision logic: Convert working days to future dates using business-day calendar; remove raw day-count field
    - Logic location: internal code
- [9] Assess whether the browser task should wait or escalate based on SLA
    - Inputs: Task reassignment deadline, waiting-for-resident flag, current time
    - Outputs: Planned or unplanned escalation to human; task monitoring start/stop; metrics and identifiers
    - Decision logic: If SLA breached, escalate; if waiting on resident within SLA, keep monitoring with snapshotting
    - Logic location: internal code
- [10] Decide which browser action to invoke next
    - Inputs: Page URLs, task context, per-run context, case messages, subtask status
    - Outputs: Single action invocation result or rerun responses; console logs
    - Decision logic: Enforce single-action-per-turn; recover from action errors by restarting browser session or reattempting; proceed until no actions remain
    - Logic location: internal code and internal prompt
- [11] Choose escalation reason when handing off to a human
    - Inputs: Agent-provided or system-derived reason constrained to allowed list
    - Outputs: Escalation recorded; task reassigned to original assignee
    - Decision logic: Validate reason against allowed values; reassign task; record metrics
    - Logic location: internal code
- [12] Send operational alerts to Slack
    - Inputs: Failures in browser actions, monitoring errors, webhook processing errors
    - Outputs: Slack messages to configured channel
    - Decision logic: On error events, send human-readable alerts and continue or stop as appropriate
    - Logic location: internal code

## Agent Design

### Console Agents

#### `review_move_out_agent`
**Type:** Console Agent (method with `@console_agent` decorator)
**Purpose:** Review move-out details and produce a decision; optionally message resident; respond to Roofstock
**Docstring:** "This agent reviews the move out and returns a decision based in the move out details and RXM instructions."

**Observable Tasks:**

**`make_decision()`**
- `@observable` decorator
- Docstring: "Making a decision based on the move out details and RXM instructions."
- Purpose: Invoke technical agent to produce answers
- Technical Agent Calls: Calls `ReviewMoveOutAgent.review_move_out()` for decision
- Integration Calls: Calls `FlexibleApiAgent.map_api_response()` to map; `RoofstockAPI.response_complete_step()` to complete; `RoofstockAPI.response_send_message()` if needed
- Observability Output: `save_to_console(type='observable_output', content="[REASONING] Response: ...")`
- Returns: Decision dict used for API

#### `send_resident_key_info_agent`
**Type:** Console Agent (method with `@console_agent` decorator)
**Purpose:** Determine whether to send key info now or reschedule; optionally compose and send message; respond to API
**Docstring:** "This agent sends the resident key information to the resident."

**Observable Tasks:**

**`make_decision()`**
- `@observable` decorator
- Docstring: Decision using communication, access, and move-out details with date logic
- Purpose: Generate answers and optional waiting period
- Technical Agent Calls: `SendResidentKeyInfoAgent.send_resident_key_info()`; `FlexibleApiAgent.map_api_response()`
- Integration Calls: `RoofstockAPI.response_send_message()`; `RoofstockAPI.response_complete_step()`
- Observability Output: Decision reasoning and formatted outputs
- Returns: Decision dict

#### `collect_additional_info_agent`
**Type:** Console Agent (method with `@console_agent` decorator)
**Purpose:** Request missing SODA-related info and schedule reminders when appropriate
**Docstring:** "This agent collects additional information from the resident."

**Observable Tasks:**

**`make_decision()`**
- `@observable` decorator
- Docstring: Decision using communications and move-out details; working day scheduling
- Purpose: Produce answers and message content
- Technical Agent Calls: `CollectAdditionalInfoAgent.collect_additional_info()`; `FlexibleApiAgent.map_api_response()`
- Integration Calls: `RoofstockAPI.response_send_message()`; `RoofstockAPI.response_complete_step()`
- Observability Output: Decision reasoning
- Returns: Decision dict

#### `pmoi_review_response_agent`
**Type:** Console Agent (method with `@console_agent` decorator)
**Purpose:** Determine PMOI waiting and reminder behavior; complete step
**Docstring:** "This agent collects additional information from the resident."

**Observable Tasks:**

**`make_decision()`**
- `@observable` decorator
- Docstring: PMOI decision with current date and days-left context
- Purpose: Produce answers and optional reminder
- Technical Agent Calls: `PMOIReviewResponseAgent.pmoi_review_response()`; `FlexibleApiAgent.map_api_response()`
- Integration Calls: `RoofstockAPI.response_complete_step()`
- Observability Output: Decision reasoning
- Returns: Decision dict

#### `process_rejection_agent`
**Type:** Console Agent (method with `@console_agent` decorator)
**Purpose:** Process rejection cases based on communications; optionally message resident; complete step
**Docstring:** "This agent processes the rejection."

**Observable Tasks:**

**`make_decision()`**
- `@observable` decorator
- Docstring: Decision using communication details
- Purpose: Produce answers and optional message
- Technical Agent Calls: `ProcessRejectionAgent.process_rejection()`; `FlexibleApiAgent.map_api_response()`
- Integration Calls: `RoofstockAPI.response_send_message()`; `RoofstockAPI.response_complete_step()`
- Observability Output: Decision reasoning
- Returns: Decision dict

#### `move_out_cancellation_process_rejection_agent`
**Type:** Console Agent (method with `@console_agent` decorator)
**Purpose:** Process rejection for cancellation flow; message and complete step
**Docstring:** "This agent processes the rejection."

**Observable Tasks:**

**`make_decision()`**
- `@observable` decorator
- Docstring: Decision using communications
- Purpose: Produce answers
- Technical Agent Calls: `MoveOutCancellationProcessRejectionAgent.move_out_cancellation_process_rejection()`; `FlexibleApiAgent.map_api_response()`
- Integration Calls: `RoofstockAPI.response_send_message()`; `RoofstockAPI.response_complete_step()`
- Observability Output: Decision reasoning
- Returns: Decision dict

#### `move_out_cancellation_cancel_in_otto_agent`
**Type:** Console Agent (method with `@console_agent` decorator)
**Purpose:** Decide if cancellation should be executed in Otto and complete API step
**Docstring:** "This agent processes the rejection."

**Observable Tasks:**

**`make_decision()`**
- `@observable` decorator
- Docstring: Decision using communications
- Purpose: Produce answers; optionally trigger cancellation action
- Technical Agent Calls: `MoveOutCancellationCancelInOttoAgent.move_out_cancellation_cancel_in_otto()`; `FlexibleApiAgent.map_api_response()`
- Integration Calls: `RoofstockAPI.response_cancel_move_out()` when applicable; `RoofstockAPI.response_complete_step()`
- Observability Output: Decision reasoning
- Returns: Decision dict

#### `collect_soda_info_agent`
**Type:** Console Agent (method with `@console_agent` decorator)
**Purpose:** Collect SODA info; optionally message resident; complete step
**Docstring:** "This agent collects SODA information from the resident."

**Observable Tasks:**

**`make_decision()`**
- `@observable` decorator
- Docstring: Decision using communications
- Purpose: Produce answers
- Technical Agent Calls: `CollectSODAInfoAgent.collect_soda_info()`; `FlexibleApiAgent.map_api_response()`
- Integration Calls: `RoofstockAPI.response_send_message()`; `RoofstockAPI.response_complete_step()`
- Observability Output: Decision reasoning
- Returns: Decision dict

### Technical Agents

#### `ReviewMoveOutAgent`
**Type:** Technical Agent (extends `Agent` class)
**Pattern:** Task
**Purpose:** Produce answers for move-out review given details and response questions
**LLM:** defined in YAML; standard mode; deterministic temperature

**Prompt Strategy:**
- Receives move-out details and response questions as user messages
- Generates structured answers required by the step
- Context: Resets for call; response appended to thread
- JSON Response: As per step YAML examples (explanation and answer fields)

**Instance Attributes:**
- Standard agent attributes from framework

**Create Parameters:**
- `yaml_config_path`: Config path for prompts
- `workflow_instance_id`: Instance identifier

#### `SendResidentKeyInfoAgent`
**Type:** Technical Agent (extends `Agent` class)
**Pattern:** Task
**Purpose:** Decide if key instructions should be sent now; compose message; waiting days if needed
**LLM:** defined in YAML; standard mode

**Prompt Strategy:**
- Inputs include communications, access details, move-out details, dates/days
- Ensures outputs include close_to_move_out_date, key_information_sent, days_to_wait, send_message, message
- Context: Resets per call; response appended
- JSON Response: As defined in YAML

**Instance Attributes:** Standard

**Create Parameters:** `yaml_config_path`, `workflow_instance_id`

#### `CollectAdditionalInfoAgent`
**Type:** Technical Agent (extends `Agent` class)
**Pattern:** Task
**Purpose:** Identify missing information and perform follow-ups with wait scheduling
**LLM:** defined in YAML; standard mode

**Prompt Strategy:**
- Inputs include communications, move-out details, dates/days
- Outputs include missing_information, contacted_resident, keep_waiting, days_to_wait, send_message, message
- Context: Resets; response appended

#### `PMOIReviewResponseAgent`
**Type:** Technical Agent (extends `Agent` class)
**Pattern:** Task
**Purpose:** Decide PMOI waiting and reminders
**LLM:** defined in YAML; standard mode

**Prompt Strategy:** Receives move-out details and time context; returns structured answers per YAML

#### `ProcessRejectionAgent`, `MoveOutCancellationProcessRejectionAgent`, `MoveOutCancellationCancelInOttoAgent`, `CollectSODAInfoAgent`
**Type:** Technical Agents (extend `Agent`)
**Pattern:** Task
**Purpose:** Each produces structured decisions for respective steps based on communications and step questions
**LLM:** defined in YAML; standard mode

#### `FlexibleApiAgent`
**Type:** Technical Agent (extends `Agent` class)
**Pattern:** Task
**Purpose:** Map agent-produced answers to the API field/value schema with conditions
**LLM:** defined in YAML; standard mode

**Prompt Strategy:**
- Input: agent response and API spec (questions/fields/options/conditions)
- Output: `{"reasoning": "...", <field>: <mapped value>, ...}` then wrapped into `{stepData, aiReasoning}`

#### Direct Actions

- Not applicable for API step workflows. Browser workflows use separate technical agents and actions; see below.

#### LLM Callables

- Not applicable in these step workflows. Browser workflows expose many `@llmcallable` methods on their technical agent for action execution.

### `OttoBrowser` (Browser Workflow)
- Console Agent: `mynd_ai` orchestrates browser task completion with observables for context gathering and escalation
- Technical Agent: `MoveOutAgent` (Task/Agentic Search hybrid) with many `@llmcallable` actions to drive Otto via a `BrowserAgent`
- Purpose: Collect context, perform single-action steps, monitor SLA, escalate or complete
- LLM: YAML-driven; message thread maintained across turns; rerun flows supported

#### Direct Actions (selected examples)

- `escalate_to_human(escalation_type, escalation_reason) -> None`
  - Purpose: Reassign to original assignee, record metrics and identifiers, console output
  - Message Thread modification: Adds system outputs via console; resets snapshots
  - Integration usage: None external; uses internal browser session management
  - Returns: None
  - Side Effects: Task monitoring stops; metrics saved

- `complete_subtasks() -> str`
  - Purpose: Loop agent turns, enforce one action per turn, collect outputs, handle reruns, persist logs, manage waiting/escalation
  - Integration usage: BrowserAgent to execute actions; Slack alerts on failures
  - Returns: "completed" or "waiting"

#### LLM Callables (selected examples from `MoveOutAgent`)

- `check_task_due_date() -> str`
  - `@llmcallable(rerun_agent=True)`
  - Purpose: Read task due date from Otto
  - Integration usage: Executes a browser action through `BrowserAgent`
  - Returns: Due date string

- `get_all_case_messages() -> str`
  - `@llmcallable(rerun_agent=True)`
  - Purpose: Retrieve case messaging history
  - Integration usage: Browser action; returns JSON string
  - Returns: JSON of messages

- `complete_review_move_out_subtask(questions_and_answers: dict) -> str`
  - `@llmcallable(rerun_agent=True)`
  - Purpose: Complete a specific subtask form
  - Integration usage: Browser action
  - Returns: Confirmation text

- Many additional callables exist (e.g., approve_move_out, update_end_date, send_external_reply, smart lock updates) following the same pattern.

## Happy Path Call Stack

**Note:** Clearly indicate which agents are Technical Agents (TA) vs Console Agents (CA) in the call stack.

```text
→ START EVENT: events.GenericWebhookEvent "Roofstock step payload received"
  ├─ @console_agent: [workflow].review_move_out_agent() / send_resident_key_info_agent() / ... (CA)
  │  ├─ @observable: get_expected_response_fields() (CA observable)
  │  ├─ @observable: get_move_out_details() / get_communication_details() / get_housing_assistance_details() / get_property_access_details() (CA observable)
  │  ├─ @observable: make_decision() → [ReviewMoveOutAgent | SendResidentKeyInfoAgent | ...]() (TA turn)
  │  │  └─ [FlexibleApiAgent].map_api_response() (TA) → mapped payload
  │  ├─ @observable: send_case_message() when requested → API → status
  │  └─ @observable: respond_to_roofstock() → API → success

→ INGRESS EVENT: Tracked/assigned Otto task
  ├─ @console_agent: OttoBrowser.mynd_ai() (CA)
  │  ├─ @observable: get_page_urls(), check_original_assignee(), check_task_due_date(), check_case_status_closed() (CA observables)
  │  ├─ @observable: get_reassignment_datetime() using SLA_agent (TA)
  │  ├─ @observable: get_task_context() → seed agent thread with instructions and context
  │  ├─ @observable: get_per_run_context() → refresh context each run
  │  └─ @observable: complete_subtasks()
  │     └─ MoveOutAgent() [TA LLM turns + @llmcallable actions]
  │        └─ BrowserAgent.browser_agent(action) → playwright/api/fallback

→ WORKFLOW COMPLETE: API step acknowledged OR browser task completed/escalated
```

## Data & Formats

### Referenced Documents Inventory and Input Data
*Excluding mentions of specific PII, financial information, or other sensitive details*

- Roofstock Step Payload
    - Format: JSON
    - Source: Webhook via Generic Web Server integration
    - Intended Use: Determines workflow type, expected inputs, and case URL
- Move-Out Details
    - Format: JSON
    - Source: Roofstock API
    - Intended Use: Agent decision inputs for review, key info, PMOI, etc.
- Communication Details
    - Format: JSON (list)
    - Source: Roofstock API
    - Intended Use: Determine prior contact, compose resident messages
- Housing Assistance Details
    - Format: JSON
    - Source: Roofstock API
    - Intended Use: Section 8 checks and related decisions
- Property Access Details
    - Format: JSON
    - Source: Roofstock API
    - Intended Use: Key-return instructions and access modality decisions
- Browser Session Cookies and Task Data
    - Format: JSON
    - Source: GCP Secret Manager or local storage fallback
    - Intended Use: Browser workflow session management and task monitoring

### Example Output Artifacts

- Step Completion Decision
    - Type: API Request/Response
    - Format: JSON
    - Recipients: Roofstock Workflow API
    - Contents: `stepData`, reasoning, and status code/text
- Resident Message
    - Type: API Request/Response
    - Format: JSON
    - Recipients: Roofstock Workflow API (sends message to resident)
    - Contents: message string; API response status
- Console Observability Entries
    - Type: Dashboard entries
    - Format: strings/JSON fragments
    - Recipients: Qurrent Supervisor console
    - Contents: Observations, identifiers, errors, outputs

## Integrations

### Prebuilt: `qurrent.WebServer`, `qurrent.Ingress`, `qurrent.Slack`
- Required Config Section: `QurrentConfig`
- Required Keys:
    - `INGRESS`: handle to workflow ingress bus
    - `SLACK_CHANNEL_ID`: string - Slack alerts channel

### Custom: `GenericWebServerIntegration`
**Location:** `roofstock/orchestrator.py`
**Type:** One-way

**Config Section:** `QurrentConfig`
- `ROOFSTOCK_API_KEY`: provided at runtime via config

**Methods:**

**`start(config: QurrentConfig, host: str, port: int, webhook_endpoint: str, api_secrets: Dict[str,str]) -> GenericWebServerIntegration`**
- Performs: Starts web server, validates HMAC-signed webhooks, enqueues events to ingress
- Behavior:
    - Missing/invalid headers → 401
    - Valid signature → event enqueued
- Returns: Instance with ingress handle

**`process_webhook(data: Dict) -> None`**
- Performs: Wraps payload into `events.GenericWebhookEvent` and adds to ingress
- Returns: None

**Custom Events:**
- `events.GenericWebhookEvent`:
    - Event type: "GenericWebhookEvent"
    - Required: `data: Dict`

### Custom: `RoofstockAPI`
**Location:** `roofstock/app/roofstock_api.py`
**Type:** One-way

**Config Section:** `QurrentConfig`
- `ROOFSTOCK_API_KEY`: string - HMAC secret for signing
- `ROOFSTOCK_API_URL`: string - Base URL

**Methods:**

**`request_move_out_details(workflow_id: str) -> Dict`**
- Performs: GET details with HMAC headers; retries with exponential backoff
- Returns: dict

**`request_communication_details(workflow_id: str) -> List[Dict]`**
- Performs: GET communications with HMAC headers; retries
- Returns: list

**`request_housing_assistance_details(workflow_id: str) -> Dict`**
- Performs: GET housing assistance details
- Returns: dict

**`request_property_access_details(workflow_id: str) -> Dict`**
- Performs: GET property access details
- Returns: dict

**`response_complete_step(workflow_id: str, step_id: str, payload: Dict) -> Tuple[int, str]`**
- Performs: POST decision to complete step
- Returns: status code and text

**`response_send_message(workflow_id: str, step_id: str, payload: Dict) -> Tuple[int, str]`**
- Performs: POST resident message for step
- Returns: status code and text

**`response_send_nonrenewal_notice(workflow_id: str) -> Tuple[int, str]`**
- Performs: POST to send notice
- Returns: status code and text

**`response_cancel_move_out(workflow_id: str) -> Tuple[int, str]`**
- Performs: POST cancel move out
- Returns: status code and text

## Utils

**`roofstock.app.date_picker.DatePicker.pick_date(start_date: date, days: int, skip_holidays: bool=True) -> date`**
- Purpose: Compute future date in working days for reminders
- Implementation: Uses `workalendar.usa.UnitedStates` to skip weekends/holidays
- Dependencies: `workalendar`

**`roofstock.app.storage_utils.read_from_gcp(file_name: str, default: Any) -> Any`**
- Purpose: Read JSON from GCP bucket with fallback to local storage
- Implementation: Error-handled GCP client; local file fallback; initializes default
- Dependencies: `google-cloud-storage`, `google-cloud-secret-manager` (optional), `requests`

**`roofstock.app.storage_utils.save_cookies_to_secret_manager(cookies_data: list) -> bool`**
- Purpose: Persist browser cookies in GCP Secret Manager or local fallback

## Directory Structure

```text
roofstock/
  app/
    date_picker.py
    roofstock_api.py
    roofstock_types.py
    slack_context.py
    storage_utils.py
  workflows/
    agents/
      *.py (technical agents)
      config/*.yaml (agent prompts/specs)
    step_workflow.py (shared console observables for API steps)
    *_workflow.py (per-step console agents)
  browser_workflows/
    base_browser_workflow.py (console agent + observables)
    move_out/
      agent.py (technical agent with @llmcallables)
      actions/*.py (browser actions)
      helper_agents/*.py|*.yaml (SLA, image analysis)
      workflow.py (OttoBrowser config/metrics)

orchestrator.py (GenericWebServerIntegration, Slack, ingress, main loop)
```
