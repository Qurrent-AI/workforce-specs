# Workforce Specification Template

**Contributors:** Alex Reents, Alex McConville, Andrey Tretyak

## Overview
High-level executive-style background summary of the system: describe what it does and how it works.

This workforce automates event-driven B2B prospecting and outreach for sales teams. It continuously pulls market signals (news and webset items), selects relevant events based on campaign logic, researches target personas for those events, updates the CRM with structured company/contact records, drafts and sends personalized outreach emails, and tracks engagement metrics. Stakeholders interact through Slack to configure campaign logic (stored in Google Drive) and to receive transparent status updates and reasoning. The workflow blends deterministic orchestration (scheduling, filtering, CRM updates, and metric logging) with technical agents that make targeted, auditable decisions (event selection, CRM update planning, and email drafting) using structured JSON responses.

## Custom Instructions
*FDE-provided instructions for how this particular workforce specification should be configured*
<!--
[Provide custom instructions here around how to understand and document this particular workforce]
-->

## Decision Audit

Documents the possible paths of workflow execution through the lens of decisions the workforce makes.

- [1] Identify qualified events for outreach
    - Inputs: Recent items from a configured webset; campaign’s event and target-company logic
    - Outputs: A deduplicated list of short event summaries; rationale delivered to Slack and console
    - Decision logic: Select recent events that match the “compelling event” definition for companies that match the “target company” definition, avoiding previously selected items
    - Logic location: internal prompt (technical agent)
- [2] Proceed when no qualified events are found
    - Inputs: Qualified event list
    - Outputs: Business notification that no events were selected
    - Decision logic: If the qualified list is empty, notify stakeholders and stop the daily outreach branch
    - Logic location: internal code
- [3] Research target personas for each event
    - Inputs: Event summaries; campaign’s target-persona logic
    - Outputs: For each event, a list of likely personas (names, titles, companies, links, and optional emails)
    - Decision logic: Use an external research service to extract people who match the target-persona rules, normalizing into a standard persona structure
    - Logic location: internal code
- [4] Decide CRM updates for companies and contacts
    - Inputs: Event+persona tuples; existing CRM data
    - Outputs: Created or updated company records; created or updated contacts with company associations; per-prospect CRM identifiers
    - Decision logic: Search for likely matching records; create or update records as needed; add parent/portfolio relationships when inferred from the event; work iteratively and parallelize safe steps
    - Logic location: internal prompt (technical agent)
- [5] Determine who to receive initial outreach
    - Inputs: Event+persona tuples after CRM updates; past email activity for contacts
    - Outputs: A set of personalized email drafts per event; Slack previews and console outputs
    - Decision logic: Only include individuals with valid CRM contact IDs; personalize drafts using the event and contact’s recent email history; optionally run limited web searches when helpful
    - Logic location: internal prompt (technical agent)
- [6] Send initial outreach and set next follow-up date
    - Inputs: Approved email drafts; demo/non-demo contact status
    - Outputs: Emails sent; CRM updated with message content, outreach phase, and next follow-up date; metrics initialized for recipients
    - Decision logic: Send emails, substituting a safe recipient when running against demo data; set next outreach date deterministically; record emails for engagement tracking
    - Logic location: internal code
- [7] Schedule and run daily processes
    - Inputs: Current date/time; campaign roster
    - Outputs: Daily event-based outreach at a fixed time; daily follow-ups in a deterministic time window per campaign; periodic campaign reconfiguration
    - Decision logic: Run daily outreach at a fixed morning time; schedule follow-ups within a deterministic window; refresh campaign definitions daily; optionally start immediately when configured
    - Logic location: internal code
- [8] Identify contacts requiring follow-up today
    - Inputs: CRM contact properties including next outreach date and phase
    - Outputs: A list of contacts due for follow-up, with necessary context for drafting
    - Decision logic: Select contacts whose next outreach date falls within today’s window
    - Logic location: internal code
- [9] Skip follow-up when a contact has replied
    - Inputs: Recent email exchanges for the contact
    - Outputs: Removal from follow-up; CRM cleared for phase/next date; reply counted as a metric
    - Decision logic: If inbound replies are detected, stop follow-ups for that contact and record success
    - Logic location: internal code
- [10] Draft and send follow-up emails
    - Inputs: Contacts due for follow-up; prior outreach messages; campaign email-writing guidelines
    - Outputs: A single concise follow-up draft per contact; Slack previews; CRM updates with new phase and next date
    - Decision logic: Keep subject the same as the last email; incorporate prior content; generate one distinct follow-up per phase; compute next date based on a phase schedule
    - Logic location: internal prompt (technical agent) for drafting; internal code for scheduling
- [11] Record engagement metrics from email provider webhooks
    - Inputs: Webhook payloads (delivered, open, bounce)
    - Outputs: Metrics posted to the observability service and stored locally to prevent duplicates
    - Decision logic: Map event types to metric IDs; locate the correct workflow by recipient email; log each event at most once per category
    - Logic location: internal code
- [12] Configure or update campaign logic definitions from Google Drive
    - Inputs: A folder of campaign documents; prior stored definitions
    - Outputs: For each new or modified document, a structured logic definition; Slack notifications; local storage updated
    - Decision logic: For new or modified documents, parse into structured sections (event, company, personas, outreach selection, email guidelines, and webset ID); request clarifications when content is incomplete; otherwise persist without invention
    - Logic location: internal prompt (technical agent) and internal code

## Data & Formats

### Referenced Documents Inventory and Input Data
*Excluding mentions of specific PII, financial information, or other sensitive details*

- Campaign Logic Documents (Google Drive)
    - Format: Google Docs (plain text export)
    - Source: Google Drive folder managed by marketing/sales (service account)
    - Intended Use: Parsed into structured logic definitions during campaign configuration
- Webset Items (Event Feed)
    - Format: JSON objects with enrichments (via research platform websets)
    - Source: External research platform
    - Intended Use: Seed events for prospecting; filtered to “compelling events” for target companies
- Research Results (Personas per Event)
    - Format: JSON array of person-like objects
    - Source: External research service
    - Intended Use: Downstream CRM updates and message drafting
- CRM Records (Companies/Contacts)
    - Format: JSON via CRM API
    - Source: CRM system
    - Intended Use: Create/update companies and contacts; store outreach metadata and next outreach dates
- Email Provider Webhooks
    - Format: JSON events (delivered, open, bounce)
    - Source: Email provider
    - Intended Use: Engagement metrics, deduplicated per recipient and event type
- Local Metrics Store
    - Format: JSON per-workflow files
    - Source: Workforce runtime
    - Intended Use: Track which recipients belong to which workflow and prevent duplicate metric logging

### Example Output Artifacts

- Event Selection Reasoning
    - Type: Slack message and console note
    - Format: Plain text explanation with the selected events list
    - Recipients: Sales channel
    - Contents: Brief justification of event choices and enumerated selections
- Outreach Drafts
    - Type: Email drafts and Slack previews
    - Format: Subject + HTML body (signature appended at send-time)
    - Recipients: Prospects (or safe recipient for demo runs); Slack for previews
    - Contents: Personalized copy referencing event, role, and company context
- CRM Update Summary
    - Type: Console note
    - Format: Plain text summary
    - Recipients: Console (observability)
    - Contents: Companies/contacts added or updated; relationship updates
- Engagement Metrics
    - Type: Metric posts to observability service and local JSON update
    - Format: JSON payloads
    - Recipients: Observability backend
    - Contents: Metric ID, workflow instance, measurement value

## Integration Summary

**Integrations:**
[List integrations that connect to actual services:]
- **Slack**: Channel notifications, file synchronization (upload/delete), command linking for configuration
- **Research Platform (Websets/Tasks)**: Fetch recent items and structured persona research results
- **CRM (HubSpot)**: Company/contact search, create/update, associations, contact activity summaries, follow-up queues
- **Email Provider (SendGrid)**: Sends initial and follow-up emails; webhook events consumed for metrics
- **Web Search (Tavily)**: Optional enrichment search used during drafting
- **Email Enrichment (Hunter.io)**: Optional email discovery by name/domain
- **Google Drive**: Lists and downloads campaign documents for parsing
- **GCP Storage**: Reads/writes small JSON files for runtime data
- **Supervisor Metrics API**: Receives engagement metrics for centralized observability

## Directory Structure

prospecting/

- agents/
  - campaign_manager.py, crm_manager.py, event_selector.py, outreach.py
  - config/
    - campaign_manager.yaml, crm_manager.yaml, event_selector.yaml, outreach.yaml
- api/
  - hubspot.py, sengrid.py, tavily.py, hunterio.py, gdrive_utils.py, gcp_storage.py, slack_utils.py, rss.py
- configuration_workflow.py
- workflow.py
- models.py
- metrics.py

## Agents

### Console Agents

#### `researcher`
**Type:** Console Agent (method with `@console_agent` decorator)
**Purpose:** Identify qualified events and fan-out prospect research
**Docstring:** "Research agent responsible for analzing articles to find compelling events to seed targeted email outreach"

**Observable Tasks:**

**`get_webset_events()`**
- `@observable` decorator
- Docstring: "Fetch recent webset items and return event summaries built from enrichments. Uses the webset's 'Summary' enrichment when available; falls back to the item's description."
- Purpose: Retrieve recent items, delegate event selection to a technical agent, and broadcast reasoning
- Technical Agent Calls: Calls `EventSelector.select_events()` for event selection reasoning and a deduplicated list
- Integration Calls: Requests recent items from the research platform; posts reasoning and selections to Slack
- Observability Output: `save_to_console(type='observable_output', content="Webset '<id>' returned N recent items ...")`
- Returns: List of event summaries

**`research_prospects()`**
- `@observable` decorator
- Docstring: "Research prospects for qualified events in parallel with error handling"
- Purpose: For each selected event, run structured persona research and normalize results
- Technical Agent Calls: None (uses external research tasks service directly)
- Integration Calls: Research task service via the research client
- Observability Output: `save_to_console(type='observable_output', content="Research completed for ... events")`
- Returns: List of (event summary, personas[]) tuples

#### `record_manager`
**Type:** Console Agent (method with `@console_agent` decorator)
**Purpose:** Orchestrate CRM updates for companies and contacts
**Docstring:** "Agent responsible for managing the CRM"

**Observable Tasks:**

**`update_crm()`**
- `@observable` decorator
- Docstring: "Updating the CRM with the prospect research"
- Purpose: In parallel per event, delegate to a technical agent to search/create/update records and relationships
- Technical Agent Calls: Calls `CRMManager()` for iterative actions and summary; then processes final updated prospect list
- Integration Calls: CRM API for company/contact operations
- Observability Output: `save_to_console(type='observable_output', content="Event processed ... Summary of updates ...")`
- Returns: Updated (event summary, personas[]) tuples with CRM contact IDs populated where available

#### `outreach_manager`
**Type:** Console Agent (method with `@console_agent` decorator)
**Purpose:** Draft and deliver initial and follow-up outreach
**Docstring:** "Agent responsible for drafting outreach emails"

**Observable Tasks:**

**`draft_outreach()`**
- `@observable` decorator
- Docstring: "Draft initial outreach for all events"
- Purpose: Coordinate drafting per event, preview drafts in Slack, send emails, and record metrics
- Technical Agent Calls: Calls `Outreach.draft_message()` per event
- Integration Calls: Slack (previews); Email provider (send); CRM (post-send updates and next dates)
- Observability Output: `save_to_console(type='observable_output', content="Outreach drafted for ... events")`
- Returns: None

**`draft_followups()`**
- `@observable` decorator
- Docstring: "Send follow-up emails to prospects"
- Purpose: Identify due contacts, draft one follow-up per contact, and send
- Technical Agent Calls: Calls `Outreach.draft_follow_up()` per contact
- Integration Calls: CRM (eligibility and updates); Slack (previews); Email provider (send)
- Observability Output: `save_to_console(type='observable_output', content="Sent follow-up to ..." or "No follow-ups sent")`
- Returns: None

### Technical Agents

#### `EventSelector`
**Type:** Technical Agent (extends `Agent` class)
**Pattern:** Task
**Purpose:** Explain selections and return a deduplicated list of qualified events from recent items
**LLM:** gpt-5 (fallback: claude-sonnet-4-20250514), standard mode, timeout=300s

**Prompt Strategy:**
- Select events that match “compelling event” and “target company” definitions
- Return structured JSON with `reasoning` and `selections` (indices)
- Context: Accumulates event summaries and past selections; injects campaign logic as variables
- JSON Response: {"reasoning": "...", "selections": [<indices>]}

**Instance Attributes:**
- `exa_webset: Dict` - recent items and enrichments to consider
- `today_date: str` - used for past selection tracking

**Create Parameters:**
- `yaml_config_path: str` - agent configuration file
- `workflow_instance_id: UUID` - runtime context
- `compelling_event: str` - campaign logic
- `target_company: str` - campaign logic
- `exa_webset: Dict` - recent items

#### Direct Actions

**`select_events() -> Tuple[str, List[str]]`**
- Purpose: Produce selection reasoning and the chosen event summaries
- Message Thread modification:
    - Appends user messages with event list and recent past selections
- Returns: Reasoning string and selected events
- Side Effects: Saves merged daily selections to a local JSON file

#### LLM Callables

- None

---

#### `CRMManager`
**Type:** Technical Agent (extends `Agent` class)
**Pattern:** Orchestrator
**Purpose:** Plan and execute CRM updates: search, create, update, and associate companies/contacts, then summarize changes
**LLM:** gpt-5 (fallback: claude-sonnet-4-20250514), standard mode, timeout=300s

**Prompt Strategy:**
- Work iteratively with actions, parallelizing safe steps
- Use searches before updates, respect rate limits, and summarize final state
- Context: Accumulates user-provided event+persona details
- JSON Response: {"reasoning": "...", "actions": [...], "summary": "..."}

**Instance Attributes:**
- `hubspot: HubSpot` - CRM client
- `prospects: List[TargetPersona]` - normalized personas for updates

**Create Parameters:**
- `yaml_config_path: str` - agent configuration file
- `workflow_instance_id: UUID` - runtime context
- `hubspot: HubSpot` - CRM client
- `prospects: List[TargetPersona]` - input personas

#### Direct Actions

- None (the agent’s primary call returns a structured summary; CRM I/O occurs via callables)

#### LLM Callables

**`keyword_search_companies(keyword: str) -> str`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Purpose: Search companies by token across name/domain
- Integration usage:
    - Calls CRM search to return potential matches
- Returns: JSON string of search results

**`add_company_record(company_name: str, company_description: str, parent_company_id?: str) -> str`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Purpose: Create company, optionally associate a parent
- Integration usage: CRM create and association APIs
- Returns: Confirmation string with new company ID or error message

**`update_company_record(company_id: str, company_description?: str, parent_company_id?: str) -> str`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Purpose: Update company description and parent association
- Integration usage: CRM update and association APIs
- Returns: Confirmation string

**`add_contact_record(first_name: str, last_name: str, company_id: str, job_title: str, email?: str, linkedin_url?: str) -> str`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Purpose: Create or update a contact and ensure company association; propagate contact IDs back to the working persona list
- Integration usage: CRM contact create/update and association APIs
- Returns: Confirmation string with contact ID or error

---

#### `Outreach`
**Type:** Technical Agent (extends `Agent` class)
**Pattern:** Task
**Purpose:** Draft personalized initial and follow-up emails, optionally enriching with limited searches and past activity
**LLM:** gpt-5 (fallback: claude-sonnet-4-20250514), standard mode, timeout=300s

**Prompt Strategy:**
- Decide whom to email based on campaign targeting and available contact IDs
- Use up to a limited number of web searches when helpful; otherwise rely on given context
- Return structured JSON with `explanation`, optional `actions`, and `outreach` (email drafts)
- Context: Includes event description, per-contact email activity, and campaign guidelines
- JSON Response: {"explanation": "...", "actions": [...], "outreach": [{...}]}

**Instance Attributes:**
- `slack_bot: Slack`, `channel_id: str` - for notifications
- `tavily: Tavily` - web search client
- `hubspot: HubSpot` - for pulling email activity
- `hunter_io: HunterIO` - optional email enrichment
- `targeting_criteria: str`, `email_guidelines_definition: str` - campaign logic

**Create Parameters:**
- `yaml_config_path: str`, `workflow_instance_id: UUID`
- `slack_bot: Slack`, `channel_id: str`
- `tavily: Tavily`, `hubspot: HubSpot`, `hunter_io: HunterIO`
- `targeting_criteria: str`, `email_guidelines_definition: str`

#### Direct Actions

**`draft_message(event_summary: str, target_personas: List[TargetPersona]) -> List[OutreachMessage]`**
- Purpose: Draft initial outreach for all valid contacts (must have CRM IDs)
- Message Thread modification:
    - Appends user message with event summary and normalized contact data including recent activity
- Integration usage:
    - Queries CRM for activity summaries per contact
- Returns: List of structured email drafts; empty list if none
- Side Effects: May trigger reruns internally to complete actions before drafting

**`draft_follow_up(hubspot_contact: Dict) -> Optional[OutreachMessage]`**
- Purpose: Draft a single follow-up referencing the last email and event trigger
- Message Thread modification:
    - Appends a user message tailored by current follow-up phase
- Returns: One draft or none (with Slack notification)

#### LLM Callables

**`search_web(query: str) -> str | List[dict]`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Purpose: Perform limited web searches for context
- Integration usage: Calls web search API
- Returns: Raw results or a guardrail message if search limits exceeded

**`get_past_email_activity(hubspot_contact_id: str) -> str`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Purpose: Retrieve recent email exchanges for personalization
- Integration usage: CRM API for email engagement summaries
- Returns: JSON string with recent messages

**`search_for_contact_info(first_name: str, last_name: str, company_domain_name: str) -> str`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Purpose: Discover likely email addresses when needed
- Integration usage: Email enrichment API
- Returns: JSON string including confidence score or a guidance message in demo mode

---

#### `CampaignManager`
**Type:** Technical Agent (extends `Agent` class)
**Pattern:** Task
**Purpose:** Parse Google Doc-based campaign definitions into structured logic sections without inventing content
**LLM:** claude-sonnet-4-20250514 (fallback: gpt-5), standard mode, timeout=300s

**Prompt Strategy:**
- Sort provided document into five logic sections and webset ID
- If a section is missing or unclear, ask for clarification and defer returning a definition
- Context: Receives raw document content and, when updating, may receive the previous definition
- JSON Response: {"actions": [...], "logic_definition": { ... }}

**Instance Attributes:**
- `slack_bot: Slack`, `channel_id: str` - for coordinator notifications
- `google_drive_client: GoogleDriveClient` - document access
- `file_id: str` - target document id to parse

**Create Parameters:**
- `yaml_config_path: str`, `workflow_instance_id: UUID`
- `slack_bot: Slack`, `channel_id: str`
- `google_drive_client: GoogleDriveClient`

#### Direct Actions

- None (parsing occurs through the agent’s primary call; the workflow manages clarification loops)

#### LLM Callables

**`fetch_campaign_logic() -> str`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Purpose: Retrieve the latest document content from Google Drive
- Integration usage: Drive API
- Returns: Document text content

**`send_slack_message(message: str) -> str`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Purpose: Notify stakeholders about parsing status or requests for clarification
- Integration usage: Slack
- Returns: Confirmation message

## Happy Path Call Stack

**Note:** Clearly indicate which agents are Technical Agents (TA) vs Console Agents (CA) in the call stack.

```text
→ START EVENT: scheduler "Daily 8am Pacific outreach"
  ├─ @console_agent: ProspectResearch.researcher() [CA]
  │  ├─ @observable: ProspectResearch.get_webset_events()
  │  │  └─ EventSelector.select_events() [TA LLM turn] → (reasoning, selections)
  │  └─ @observable: ProspectResearch.research_prospects()
  │     └─ External Research Tasks → (event, personas[])
  ├─ @console_agent: ProspectResearch.record_manager() [CA]
  │  └─ @observable: ProspectResearch.update_crm()
  │     └─ CRMManager() [TA LLM turn]
  │        └─ @llmcallable actions: keyword_search_companies(), add_company_record(), update_company_record(), add_contact_record()
  └─ @console_agent: ProspectResearch.outreach_manager() [CA]
     └─ @observable: ProspectResearch.draft_outreach()
        ├─ Outreach.draft_message() [TA direct action]
        │  ├─ @llmcallable: Outreach.get_past_email_activity()
        │  └─ @llmcallable: Outreach.search_web() (optional)
        └─ Email Provider send() → (status)

→ INGRESS EVENT: scheduler "Daily follow-ups window"
  └─ @console_agent: ProspectResearch.outreach_manager() [CA]
     └─ @observable: ProspectResearch.draft_followups()
        ├─ Outreach.draft_follow_up() [TA direct action]
        └─ Email Provider send() → (status)

→ INGRESS EVENT: Slack command "/configure-campaigns"
  └─ Workflow: CampaignConfiguration
     ├─ Link Slack channel
     ├─ List Drive campaigns → download content
     ├─ CampaignManager() [TA LLM turn]
     │  ├─ @llmcallable: fetch_campaign_logic()
     │  └─ @llmcallable: send_slack_message() (optional)
     └─ Persist structured definitions; notify Slack; unlink channel

→ INGRESS EVENT: SendGridWebhook "delivered/open/bounce payload"
  └─ Workflow: Metrics handler
     ├─ Map event → metric id
     ├─ Find workflow by recipient email
     └─ Post metric to Supervisor; record locally

→ WORKFLOW COMPLETE: Outreach and follow-up cycles finish for the day; metrics logged
```

## Utils

**`prospecting/api/slack_utils.fetch_canvas_content(slack_bot: Slack, channel_id: str, canvas_name: str, clean_content: bool) -> str`**
- Purpose: Retrieve and optionally clean a Slack Canvas document’s content
- Implementation: Uses Slack file APIs and HTTP download; converts HTML to readable markdown-like text
- Dependencies: `aiohttp`, `loguru`

**`prospecting/api/slack_utils.sync_storage(slack_bot: Slack, channel_id: str, file_name: str) -> None`**
- Purpose: Upload or replace a JSON file in Slack with content mirrored from GCP storage
- Implementation: Reads GCP object, uploads via Slack’s external upload API, completes and shares to channel
- Dependencies: `aiohttp`, `google-cloud-storage`

**`prospecting/api/slack_utils.delete_all_messages(slack_bot: Slack, channel_id: str, delay_seconds: float) -> int`**
- Purpose: Best-effort bulk delete of all messages (and replies) from a Slack channel
- Implementation: Paginates channel history and deletes main + thread messages
- Dependencies: Slack client

**`prospecting/api/gcp_storage.read_from_gcp(file_name: str, default?: Dict) -> Dict`**
- Purpose: Read JSON from GCP bucket (with local file fallback)
- Implementation: Uses environment-specific bucket; ensures files/directories exist; JSON load
- Dependencies: `google-cloud-storage`

**`prospecting/api/gcp_storage.write_to_gcp(file_name: str, content: Dict) -> bool`**
- Purpose: Write JSON to GCP bucket (with local file fallback)
- Implementation: Uploads object as JSON; ensures directory structure
- Dependencies: `google-cloud-storage`

**`prospecting/metrics.MetricsTracker.initialize_metrics(workflow_instance_id, recipient_emails) -> None`**
- Purpose: Initialize per-workflow recipient metrics files
- Implementation: Atomic writes to JSON with best-effort permissions controls
- Dependencies: standard library

**`prospecting/metrics.MetricsTracker.should_log_event(workflow_instance_id, email, event_type) -> bool`**
- Purpose: Prevent duplicate metric logs for a given recipient and event type
- Implementation: Reads JSON, checks event arrays, returns True only when new
- Dependencies: standard library

**`prospecting/metrics.MetricsTracker.record_event(workflow_instance_id, email, event_type) -> bool`**
- Purpose: Persist an engagement event and increment counters
- Implementation: JSON read/modify/write with atomic swap
- Dependencies: standard library

## Integrations

### Prebuilt: `qurrent.Slack`
- Required Config Section: `[SLACK]`
- Required Keys:
    - `[SLACK_CHANNEL_ID]: string` - Target channel for notifications

### Custom: `HubSpot`
**Location:** `prospecting/api/hubspot.py`
**Type:** One-way

**Config Section:** `[HUBSPOT]`
- `HUBSPOT_API_KEY: <env/secret>` - API authentication

**Methods:**

**`keyword_search_companies(keyword: str, limit?: int) -> List[dict]`**
- Performs: Search companies by token across name and domain
- Behavior:
    - Returns normalized results including IDs and descriptions
- Returns: List of company dicts

**`create_company(company_name: str, company_description: str) -> dict`**
- Performs: Create a company (demo-safe properties applied in non-production)
- Behavior:
    - If already exists, returns existing
- Returns: Company object

**`update_company(company_id: str, properties: Dict[str, str]) -> dict`**
- Performs: Update selected company properties (demo checks applied)
- Returns: Company object

**`associate_parent_company(parent_company_id: str, child_company_id: str) -> dict`**
- Performs: Parent/child association via associations API
- Behavior:
    - If already exists, returns status
- Returns: Response dict

**`create_or_update_contact(first_name: str, last_name: str, company_id: str, job_title: str, email?: str, linkedin_url?: str) -> dict`**
- Performs: Create or update by name; ensure association
- Behavior:
    - Deduplicates and avoids conflicting email updates
- Returns: Contact object

**`update_contact(contact_id: str, properties: Dict[str, Any]) -> dict`**
- Performs: Safely update a contact; pre-checks for email conflicts
- Returns: Contact object

**`get_recent_contact_emails(contact_id: str, limit?: int, ...) -> List[Dict]`**
- Performs: Provide a cleaned, recent-email summary for personalization
- Returns: List of normalized email objects

**`get_contacts_requiring_follow_up() -> List[dict]`**
- Performs: Query contacts due for follow-up today (Pacific window)
- Returns: List of contact dicts with outreach metadata

### Custom: `SendGrid`
**Location:** `prospecting/api/sengrid.py`
**Type:** One-way

**Config Section:** `[SENDGRID]`
- `SENDGRID_API_KEY: <env/secret>` - API authentication

**Methods:**

**`send_email(outreach_message: OutreachMessage, from_email?: str, from_name?: str, bcc_emails?: List[str], is_demo_record?: bool) -> bool`**
- Performs: Send a single email; appends signature; optional BCC list
- Behavior:
    - In demo, directs to a safe recipient
- Returns: Success boolean

### Custom: `Tavily`
**Location:** `prospecting/api/tavily.py`
**Type:** One-way

**Config Section:** `[TAVILY]`
- `TAVILY_API_KEY: <env/secret>` - API key

**Methods:**

**`search(query: str, ...) -> List[dict]`**
- Performs: Web search with backoff
- Returns: List of results

### Custom: `HunterIO`
**Location:** `prospecting/api/hunterio.py`
**Type:** One-way

**Config Section:** `[HUNTER]`
- `HUNTER_IO_API_KEY: <env/secret>` - API key

**Methods:**

**`email_finder(domain: str, first_name: str, last_name: str) -> dict`**
- Performs: Find likely email address with confidence score
- Returns: JSON dict

### Custom: `GoogleDriveClient`
**Location:** `prospecting/api/gdrive_utils.py`
**Type:** One-way

**Config Section:** `[GOOGLE]`
- `AE_SERVICE_ACCOUNT_JSON: <json env blob>` - service account content

**Methods:**

**`list_files_in_folder(folder_id: str) -> List[Dict]`**
- Performs: List Google Docs within a folder
- Returns: File metadata entries

**`download_file_content(file_id: str) -> str`**
- Performs: Export Google Doc as plain text
- Returns: Document content

### Custom: `GCP Storage`
**Location:** `prospecting/api/gcp_storage.py`
**Type:** One-way

**Config Section:** `[GCP]`
- `ENVIRONMENT: development|production` - bucket naming

**Methods:**

**`read_from_gcp(file_name: str, default?: Dict) -> Dict`**
- Performs: Read or initialize JSON content
- Returns: JSON dict

**`write_to_gcp(file_name: str, content: Dict) -> bool`**
- Performs: Write JSON content
- Returns: Success boolean

### Custom Events:
- `SendGridWebhookEvent`:
    - Event type: "SendGridWebhook"
    - Required: `workflow_instance_id: UUID|int`, `data: dict|list`
