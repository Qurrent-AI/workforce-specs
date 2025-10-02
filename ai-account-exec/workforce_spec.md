# Workforce Specification: AI Account Executive

## Overview

The AI Account Executive is an automated sales prospecting and outreach system that monitors news events, identifies qualified prospects, manages CRM records, and executes personalized email campaigns with multi-stage follow-ups. The system operates continuously, refreshing campaign definitions daily from Google Drive, monitoring news via Exa websets, conducting deep research to identify decision-makers, enriching CRM data, drafting personalized outreach emails, and tracking engagement metrics through SendGrid webhooks.

The workflow supports multiple concurrent campaigns, each with custom AI logic definitions stored as Google Docs. It runs on scheduled basis: initial event-based outreach at 8am PT daily, and follow-ups at deterministic random times between 10am-2pm PT to avoid detection patterns. The system integrates with HubSpot CRM, Hunter.io for email enrichment, Tavily and Exa for research, SendGrid for email delivery, and Slack for human oversight.

## Custom Instructions
*FDE-provided instructions for how this particular workforce specification should be configured*
<!--
[Provide custom instructions here around how to understand and document this particular workforce]
-->

## Path Audit

### Architecture Overview

**High Level Architecture Components:**
- **Phases**:
  - Phase 1: Campaign Configuration (7am PT daily) - Parse Google Drive documents to extract AI logic definitions using CampaignManager agent
  - Phase 2: Event Selection (8am PT per campaign) - Evaluate webset items against campaign criteria to identify qualified events using EventSelector agent
  - Phase 3: Prospect Research (per event) - Identify target individuals associated with each event using Exa Research API with structured output schemas
  - Phase 4: CRM Management (per event, parallel) - Create/update company and contact records in HubSpot with event context using CRMManager agent
  - Phase 5: Initial Outreach (per event, parallel) - Select targets, enrich emails, draft personalized messages, send and track using Outreach agent
  - Phase 6: Follow-up Management (deterministic time 10am-2pm PT per campaign) - Monitor due dates, check for replies, draft and send follow-ups with phase-based delays using Outreach agent

- **User Touchpoints**:
  - Campaign definition editing in Google Drive (human edits trigger re-parsing via CampaignManager)
  - Slack notifications for campaign updates, event selections, errors, and reply detections
  - Slack command `/configure-campaigns` to force campaign refresh
  - Human can provide clarifications when CampaignManager agent requests via Slack (agent instructs human to edit document directly)

### Decision Ledger

1. **Campaign Configuration Refresh (Daily at 7am PT)**
   - Inputs: Google Drive folder containing campaign definition documents
   - Outputs: List of Campaign objects with parsed AI logic definitions
   - Decision logic: For each Google Doc in the folder, check last modified timestamp against stored version. If new or modified, parse the document using CampaignManager agent to extract structured logic definitions (exa_webset_id, compelling_event_logic, target_company_logic, target_personas_logic, outreach_selection_logic, email_guidelines_logic). If human clarification is needed, CampaignManager sends Slack message instructing human to update document, waits for confirmation, then fetches updated document and provides final structured logic. Agent loops until definition is complete or workflow times out (15 minutes), at which point final attempt is made to extract logic from latest document state.
   - Logic location: Orchestration code in `server.py::configure_campaigns()` and `configuration_workflow.py::get_campaigns()`, with parsing logic in `CampaignManager` agent prompt (internal prompt)

2. **Event Selection from Webset (Daily at 8am PT per campaign)**
   - Inputs: Exa webset ID (from campaign logic), webset items with enrichment summaries, past selection history (last 30 days)
   - Outputs: List of event summary strings selected for prospecting with reasoning
   - Decision logic: EventSelector agent evaluates webset enrichment summaries against compelling event criteria and target company criteria (both from campaign AI logic), deduplicates against past 30 days of selections stored in `data/selected_events.json`, and returns qualified event summaries with qualitative reasoning that describes events without referencing indices
   - Logic location: External prompt in campaign definition document, injected into EventSelector agent's system prompt via variable substitution (`compelling_event_logic` and `target_company_logic`)

3. **Prospect Research per Event**
   - Inputs: Event summary string, target personas logic from campaign
   - Outputs: List of TargetPersona objects (first_name, last_name, job_title, company_name, company_domain_name, location, email if found, linkedin_url, relevance_explanation)
   - Decision logic: Use Exa Research API with structured output schema. Instructions combine event summary and target personas logic to identify individuals matching persona criteria associated with the event. Retry up to 3 times on failure with 2 second delay between attempts. If all retries fail, skip event and notify Slack. Poll task status until completed.
   - Logic location: External prompt (target personas logic) from campaign document, combined with event summary in workflow code and passed to Exa Research API (`workflow.py::research_event()`)

4. **CRM Record Management per Event**
   - Inputs: Event summary, list of TargetPersona objects from research
   - Outputs: Updated TargetPersona list with HubSpot contact IDs populated
   - Decision logic: CRMManager agent receives prospects and event summary via user message. Agent searches for matching company records by keyword (fuzzy match on name/domain), creates/updates company records with event mention in description, infers parent-portfolio relationships if detectable from event context, creates/updates contact records with name match (using locks to prevent race conditions), and associates contacts with companies. Agent works iteratively with multiple action rounds: search first, observe results, then create/update based on findings. Updates prospects list by mutating `self.prospects` to populate HubSpot contact IDs. Actions can run in parallel when efficient. System errors should be retried at least once.
   - Logic location: Internal prompt in CRMManager agent config (`crm_manager.yaml`)

5. **Outreach Target Selection and Email Drafting per Event**
   - Inputs: Event summary, list of TargetPersona objects with HubSpot IDs and past email activity stats from HubSpot, targeting criteria from campaign, email guidelines from campaign
   - Outputs: List of OutreachMessage objects (hubspot_contact_id, to, subject, body) or empty list
   - Decision logic: Outreach agent receives event summary and target individuals (JSON) via user message. Agent evaluates prospects against targeting criteria (external logic from campaign), filters out individuals already contacted (check account_exec_outreach_phase in past_email_activity from HubSpot), searches web up to 3 times for additional context if helpful, enriches missing email addresses using Hunter.io (only if confidence >50%, expensive operation done after selecting targets), and drafts personalized emails per email guidelines (external logic from campaign). Agent uses rerun pattern: when researching (web search or email enrichment), respond with actions only; when drafting, respond with outreach only (no actions). Filters out prospects without valid hubspot_contact_id before drafting. If no valid prospects, notifies Slack and returns empty list.
   - Logic location: External prompts (targeting_criteria and writing_guidelines) from campaign document, injected into Outreach agent's system prompt via variable substitution

6. **Email Delivery and CRM Update**
   - Inputs: OutreachMessage object, demo record flag from HubSpot
   - Outputs: Email sent status, HubSpot contact updated with email content and next outreach date
   - Decision logic: Check if contact is demo record via `hubspot.is_contact_demo_record()`. If demo (or in development mode with ENVIRONMENT=development), send to test address (alex@qurrent.ai) instead of actual recipient. If SLACK_CHANNEL_OVERRIDE env var set, also use test mode. Send via SendGrid with BCC to HubSpot (48618838@bcc.hubspot.com), include cole_email_signature.html appended to body. If send succeeds (status 200/201/202), update HubSpot contact with account_exec_email_subject, account_exec_email_body, account_exec_outreach_trigger (event summary), account_exec_outreach_phase (set to "1"), and account_exec_next_outreach_date (3 days from today at midnight PT as epoch ms in UTC). Initialize metrics tracking for recipient email via MetricsTracker.
   - Logic location: Internal code in `workflow.py::send_initial_outreach()` and `sengrid.py::send_email()`

7. **Follow-up Qualification Check (Daily at deterministic time 10am-2pm PT per campaign)**
   - Inputs: HubSpot contacts with account_exec_next_outreach_date within today's PT window (00:00-24:00 as UTC epoch ms)
   - Outputs: List of contacts requiring follow-up, or contact removed from queue if replied
   - Decision logic: Query HubSpot for contacts where next outreach date falls within today's PT window using `hubspot.get_contacts_requiring_follow_up()`. For each contact, check recent email history for incoming emails via `hubspot.get_recent_contact_emails()`. If incoming email exists (direction == "INCOMING_EMAIL"), log reply metric to Supervisor API (metric_id: 019916d4-0c76-7c25-84a5-6e35d2429953), clear account_exec_outreach_phase and account_exec_next_outreach_date in HubSpot, notify Slack, and skip follow-up. Otherwise, proceed to draft follow-up.
   - Logic location: Internal code in `workflow.py::send_followup()` and `hubspot.py::get_contacts_requiring_follow_up()`

8. **Follow-up Email Drafting**
   - Inputs: HubSpot contact details (hubspot_contact_id, first_name, last_name, email, company_name, account_exec_email_subject, account_exec_email_body, account_exec_outreach_trigger, account_exec_outreach_phase)
   - Outputs: OutreachMessage for follow-up or None if no outreach drafted
   - Decision logic: Outreach agent receives contact details string via user message with phase-specific instructions: "Draft a single, short follow-up email to the following contact. This is follow-up number {phase}. Be sure to reference the last email, but make this one distinct. You MUST use the exact same subject line and email address as the last email. Do not add Re: or any other modifications to the subject line." Agent can search web for additional context (up to 3 attempts). If drafting fails or agent returns no outreach, notify Slack and return None.
   - Logic location: External prompts (targeting_criteria and writing_guidelines) from campaign document apply via substituted variables in Outreach agent, with follow-up-specific instructions in workflow code passed in user message (`workflow.py::send_followup()` calls `outreach.draft_follow_up()`)

9. **Follow-up Delivery and Next Phase Scheduling**
   - Inputs: OutreachMessage, contact details including current phase
   - Outputs: Email sent, HubSpot updated with next phase and date
   - Decision logic: Send follow-up via SendGrid (with demo record check same as initial outreach). Calculate next outreach date based on current phase using FOLLOW_UP_DELAY_DAYS mapping: phase 0→0 days (initial), phase 1→3 days, phase 2→5 days, phase 3→7 days, phase 4+→no further follow-ups (clear date to empty string). Next date is calculated as midnight PT on target date, converted to UTC epoch ms. Update HubSpot contact with account_exec_email_subject, account_exec_email_body, incremented account_exec_outreach_phase (phase + 1), and account_exec_next_outreach_date.
   - Logic location: Internal code in `workflow.py::send_followup()` with follow-up delay mapping constant (FOLLOW_UP_DELAY_DAYS = {0: 0, 1: 3, 2: 5, 3: 7})

10. **Engagement Metrics Tracking (Continuous via webhook)**
    - Inputs: SendGrid webhook events (open, delivered, bounce) with recipient email and event type
    - Outputs: Metric logged to Qurrent Supervisor API, local tracking updated in JSON files
    - Decision logic: Parse webhook payload for event type and recipient email. Payload may be single dict or list of dicts. Find workflow instance ID by searching metrics files for email via `MetricsTracker.find_workflow_for_email()`. Check if event should be logged via `MetricsTracker.should_log_event()`: delivered/bounce logged only once per email per workflow; open logged unlimited times. If yes, post metric to Supervisor API at `https://external.qurrent.ai/dev/metrics_data` with metric_id (mappings: open→01990cd2-cc11-7902-82c0-d3d9d6f783ca, bounce→01990cd3-894d-705a-8295-049f6acd7fff, delivered→01990cd3-e918-7ae5-824e-33637e68a892), workflow_instance_id, and measure=1.0. Then record event locally via `MetricsTracker.record_event()` which increments counter and appends timestamp to events array, saved atomically to `data/email_metrics/email_metrics_{workflow_id}.json`.
    - Logic location: Internal code in `server.py::handle_sendgrid_event()` with deduplication logic in `metrics.py::MetricsTracker`

## Data & Formats

### Referenced Documents Inventory and Input Data

- **Google Drive Campaign Definitions**
  - Format: Google Docs (exported as plain text)
  - Source: Google Drive folder (ID: 1GZoagbXw4sMYPLQ0cz7s2Q88lTwrbxZV) using service account authentication
  - Intended Use: CampaignManager agent parses to extract structured AI logic definitions (exa_webset_id, compelling_event_logic, target_company_logic, target_personas_logic, outreach_selection_logic, email_guidelines_logic)

- **Exa Webset Items**
  - Format: JSON objects from Exa API with items array containing enrichments array with summary strings
  - Source: Exa API webset endpoint with expand=items parameter
  - Intended Use: EventSelector agent evaluates summaries (first enrichment result) to select qualified events

- **HubSpot Contact/Company Records**
  - Format: JSON responses from HubSpot CRM v3 API
  - Source: HubSpot API queries (search, get, batch read, associations)
  - Intended Use: CRMManager reads/writes records with custom properties (account_exec_email_subject, account_exec_email_body, account_exec_outreach_trigger, account_exec_outreach_phase, account_exec_next_outreach_date, is_demo_record); Outreach agent reads past email activity; follow-up logic reads due dates and phases

- **SendGrid Webhook Events**
  - Format: JSON array or single object with event type, email, timestamp fields
  - Source: SendGrid webhook POST to /sendgrid-event
  - Intended Use: Metrics tracking for engagement (open, delivered, bounce)

- **Past Event Selections Storage**
  - Format: JSON file mapping dates to lists of selected event summary strings
  - Source: Local file `data/selected_events.json` maintained by EventSelector
  - Intended Use: Deduplication of event selections over 30-day rolling window

- **Campaign Definitions Storage**
  - Format: JSON file with array of campaign objects (id, name, last_modified_time, ai_logic)
  - Source: Local file `data/campaign_definitions.json` maintained by CampaignConfiguration workflow
  - Intended Use: Version tracking for campaigns to detect Google Drive modifications

### Example Output Artifacts

- **Event Selection Reasoning**
  - Type: Slack message
  - Format: Plain text with qualitative reasoning and bulleted event summaries
  - Recipients: Configured Slack channel (SLACK_CHANNEL_ID)
  - Contents: EventSelector agent's reasoning for selections (no indices, detailed enough for reader without access to descriptions) and list of chosen event summaries as bullets

- **Initial Outreach Email**
  - Type: Email via SendGrid
  - Format: HTML with plain text fallback, includes email signature from cole_email_signature.html
  - Recipients: Target prospects (or alex@qurrent.ai for demo records in development mode)
  - Contents: Personalized subject and body referencing event and prospect's role/relevance, sender signature, BCC to HubSpot logging address (48618838@bcc.hubspot.com)

- **Follow-up Email**
  - Type: Email via SendGrid
  - Format: HTML with plain text fallback, includes email signature
  - Recipients: Prospects in follow-up queue
  - Contents: Short follow-up referencing prior email with exact same subject line (no "Re:" prefix), sender signature, BCC to HubSpot

- **CRM Update Summary**
  - Type: Slack message and Qurrent console output
  - Format: Plain text summary
  - Recipients: Slack channel and Qurrent console (observable_output)
  - Contents: CRMManager agent's summary of which companies/contacts were created/updated, parent relationships established, from response JSON

- **Metrics Data Files**
  - Type: Local JSON files per workflow
  - Format: Nested JSON with workflow_id → email → counters (open_count, delivered_count, bounce_count) and events arrays with timestamps
  - Recipients: Internal storage (`data/email_metrics/email_metrics_{workflow_id}.json`)
  - Contents: Tracking for email engagement per workflow instance, used for webhook lookups and deduplication

- **Campaign Configuration Notifications**
  - Type: Slack messages
  - Format: Plain text
  - Recipients: Configured Slack channel
  - Contents: Campaign parsing status ("Successfully constructed logic for campaign: {name}", "Successfully updated logic for campaign: {name}"), clarification requests from CampaignManager, timeout notifications

## Integration Summary

**Integrations:**
- **Exa (exa-py==1.14.16)**: Fetches webset items via raw request API and conducts deep prospect research via Research API with structured output schemas, polling for task completion
- **HubSpot CRM**: Creates/updates companies and contacts with custom account exec properties, associates records (parent/child companies, contacts to companies), queries follow-up dates, retrieves email history with direction filtering
- **Hunter.io**: Finds and verifies email addresses for prospects by name and company domain, returns confidence scores
- **Tavily**: Web search for additional context during outreach drafting with exponential backoff retry (up to 5 retries, up to 3 searches per agent invocation)
- **SendGrid**: Sends outreach and follow-up emails with HTML formatting and signature, tracks engagement via webhooks posted to /sendgrid-event
- **Google Drive**: Reads campaign definition documents from shared folder using service account authentication, exports as plain text
- **Slack**: Sends notifications for campaign updates, event selections, errors, reply detections; receives `/configure-campaigns` command for manual refresh
- **Qurrent Supervisor API**: Logs engagement metrics (open, delivered, bounce) to external dashboard at https://external.qurrent.ai/dev/metrics_data

## Directory Structure

```
ai-account-exec/
├── prospecting/
│   ├── agents/
│   │   ├── campaign_manager.py
│   │   ├── crm_manager.py
│   │   ├── event_selector.py
│   │   ├── outreach.py
│   │   └── config/
│   │       ├── campaign_manager.yaml
│   │       ├── crm_manager.yaml
│   │       ├── event_selector.yaml
│   │       └── outreach.yaml
│   ├── api/
│   │   ├── gcp_storage.py
│   │   ├── gdrive_utils.py
│   │   ├── hubspot.py
│   │   ├── hunterio.py
│   │   ├── rss.py
│   │   ├── sengrid.py
│   │   ├── slack_utils.py
│   │   └── tavily.py
│   ├── cole_email_signature.html
│   ├── configuration_workflow.py
│   ├── metrics.py
│   ├── models.py
│   ├── tests.py
│   └── workflow.py
├── server.py
├── requirements.txt
├── pyproject.toml
├── load_secrets.py
├── startup.sh
├── Dockerfile
├── docker-compose.yaml
├── config.yaml (runtime generated)
└── data/ (runtime created)
    ├── email_metrics/
    ├── selected_events.json
    └── campaign_definitions.json
```

## Agents

### `CampaignManager`
**Pattern:** Task Agent  
**Purpose:** Parse unstructured campaign definition documents from Google Drive into structured AI logic definitions for use by downstream agents  
**LLM:** claude-sonnet-4-20250514, standard mode, temp=default, timeout=300s

**Prompt Strategy:**
- Receives raw campaign document text and existing logic (if updating)
- Tasked with sorting content into 6 structured sections: exa_webset_id, compelling_event_logic, target_company_logic, target_personas_logic, outreach_selection_logic, email_guidelines_logic
- Instructed to preserve content as-is (no additions/removals) unless obvious optimization opportunities or human omissions
- Primary responsibility is merely sorting unstructured content into structured sections
- If uncertain, uses llmcallables to fetch updated document or send Slack message requesting human clarification, instructing human to edit document directly and inform when done
- Loops until definition is complete: if taking clarification actions, must respond with empty logic_definition and no actions until user responds; once done clarifying, respond with complete logic_definition and no actions
- Must respond with JSON containing either (1) empty logic_definition + actions, or (2) complete logic_definition + no actions
- Context: Accumulates over multiple turns when clarification needed
- JSON Response: `{"actions": [] or [...], "logic_definition": {} or {...}}`

**Instance Attributes:**
- `slack_bot: Slack` - For sending clarification requests to human
- `channel_id: str` - Slack channel for notifications
- `google_drive_client: GoogleDriveClient` - For fetching latest document content
- `file_id: str` - Google Drive file ID of current campaign document being parsed (set by workflow before invocation)

**Create Parameters:**
- `yaml_config_path: str` - Path to campaign_manager.yaml config
- `workflow_instance_id: UUID` - Workflow instance for tracking
- `slack_bot: Slack` - Initialized Slack integration
- `channel_id: str` - Target Slack channel ID
- `google_drive_client: GoogleDriveClient` - Initialized Google Drive client

#### LLM Callables

**`fetch_campaign_logic() -> str`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Docstring Args: None
- Purpose: Retrieve latest content of campaign document from Google Drive
- Integration usage:
  - Calls `google_drive_client.download_file_content(self.file_id)` to fetch plain text export
- Returns: Document content as string (appended to thread)
- Error Handling: Raises ValueError if file_id not set

**`send_slack_message(message: str) -> str`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Docstring Args: `message (str): The message to send`
- Purpose: Send notification or request for clarification to human via Slack
- Integration usage:
  - Calls `slack_bot.send_message(channel_id=self.channel_id, message=message)`
- Returns: "The message was sent successfully"
- Error Handling: None specified (async errors propagate)

### `EventSelector`
**Pattern:** Task Agent  
**Purpose:** Evaluate webset news items against campaign criteria to select qualified events for prospecting, deduplicating against past selections  
**LLM:** gpt-5, standard mode, temp=default, timeout=300s

**Prompt Strategy:**
- System prompt contains campaign-specific compelling_event_logic and target_company_logic via variable substitution
- Receives numbered list of event summaries (formatted with separators) and past 30 days of selection indices
- Must respond with reasoning (qualitative, no indices, detailed enough for reader without access to descriptions, refer to "events" not "items") and array of selected indices
- Single-turn evaluation (no actions, no rerun)
- Context: Single-turn evaluation
- JSON Response: `{"reasoning": "<explanation>", "selections": [0, 3, 7]}`

**Instance Attributes:**
- `exa_webset: Dict` - Webset object from Exa API containing items with enrichments
- `today_date: str` - Current date in YYYY-MM-DD format (America/Los_Angeles)

**Create Parameters:**
- `yaml_config_path: str` - Path to event_selector.yaml config
- `workflow_instance_id: UUID` - Workflow instance for tracking
- `compelling_event: str` - Campaign's compelling event criteria (injected into prompt via substitute_variables)
- `target_company: str` - Campaign's target company criteria (injected into prompt via substitute_variables)
- `exa_webset: Dict` - Webset data from Exa API with items array

#### Direct Actions

**`select_events() -> Tuple[str, List[str]]`**
- Purpose: Parse webset enrichments, append to thread with past selections, invoke agent, extract selected summaries, persist selections to disk
- Message Thread modification:
  - Appends user message with formatted event summaries (numbered with separator lines: `--------------------\n[{i}] {summary}\n--------------------`)
  - Appends user message with recent past selections (list of indices from last 30 days loaded from `data/selected_events.json`)
- Util usage:
  - Reads/writes `data/selected_events.json` for persistence (date → list of selected summary strings, not indices despite prompt wording)
  - Merges today's selections with existing data
- Returns: Tuple of (reasoning string, list of selected event summary strings)
- Side Effects: Updates selected_events.json with today's selections merged with existing data

### `CRMManager`
**Pattern:** Task Agent  
**Purpose:** Create/update HubSpot company and contact records based on prospect research results, inferring parent-child relationships from event context  
**LLM:** gpt-5, standard mode, temp=default, timeout=300s

**Prompt Strategy:**
- Receives event summary and prospect list (JSON via `[p.model_dump() for p in prospects]`) via user message appended by workflow
- Instructed to keyword search companies first (substring match on name/domain), then create/update records, add event mention to descriptions, infer parent-portfolio relationships from event context
- Explicitly told to run actions in parallel when efficient, work iteratively (search first, observe results, then act on findings)
- Actions run in parallel by default (unless wait_for_all or sequential specified), so must run search first, then updates after seeing results
- System errors should be re-attempted at least once
- Must return JSON with reasoning, actions array, and summary of actions taken after completion
- Context: Accumulates over multiple rerun turns
- JSON Response: `{"reasoning": "<explanation>", "actions": [{"name": "keyword_search_companies", "args": {"keyword": "kkr"}}], "summary": "<detailed summary>"}`

**Instance Attributes:**
- `hubspot: HubSpot` - HubSpot integration client
- `prospects: List[TargetPersona]` - List of prospect objects to process (mutated as contacts are created with IDs via `persona.update_hubspot_contact_id()`)

**Create Parameters:**
- `yaml_config_path: str` - Path to crm_manager.yaml config
- `workflow_instance_id: UUID` - Workflow instance for tracking
- `hubspot: HubSpot` - Initialized HubSpot client
- `prospects: List[TargetPersona]` - Prospects from research phase

#### LLM Callables

**`keyword_search_companies(keyword: str) -> str`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Docstring Args: `keyword (str): Keyword token to search for (e.g., brand acronym like 'kkr')`
- Purpose: Fuzzy search companies by keyword across name and domain using tokenized matching
- Integration usage:
  - Calls `hubspot.keyword_search_companies(keyword)` which uses CONTAINS_TOKEN operator on name and domain properties
- Returns: JSON string of search results (list of dicts with id, name, domain, description, parent_id) or error message
- Error Handling: try/except returns `f"Exception raised searching for companies with keyword {keyword}: {str(e)}"`

**`add_company_record(company_name: str, company_description: str, parent_company_id: Optional[str] = None) -> str`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Docstring Args: `company_name (str), company_description (str), parent_company_id (Optional[str])`
- Purpose: Create company record in HubSpot with demo flag if in development mode, optionally associate with parent company
- Integration usage:
  - Calls `hubspot.create_company(company_name, company_description)` which searches by name with lock, creates if not exists, handles 409 race condition
  - If parent_company_id provided, calls `hubspot.associate_parent_company(parent_company_id, company_id)` using batch associations API
- Returns: Success message with company ID or error string
- Error Handling: try/except returns `f"Exception raised creating company record {company_name}: {str(e)}"`

**`update_company_record(company_id: str, company_description: Optional[str] = None, parent_company_id: Optional[str] = None) -> str`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Docstring Args: `company_id (str), company_description (Optional[str]), parent_company_id (Optional[str])`
- Purpose: Update existing company record with new description or parent association (protected by demo record check in development)
- Integration usage:
  - Calls `hubspot.update_company(company_id, properties)` with description if provided (checks is_demo_record flag first, only updates if demo or in production)
  - If parent_company_id provided, calls `hubspot.associate_parent_company(parent_company_id, company_id)`
- Returns: Success message or error string
- Error Handling: try/except returns `f"Exception raised updating company record {company_id}: {str(e)}"`

**`add_contact_record(first_name: str, last_name: str, company_id: str, job_title: str, email: Optional[str] = None, linkedin_url: Optional[str] = None) -> str`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Docstring Args: `first_name (str), last_name (str), company_id (str), job_title (str), email (Optional[str]), linkedin_url (Optional[str])`
- Purpose: Create contact record in HubSpot with demo flag if in development, associate with company, and update prospects list with contact ID
- Integration usage:
  - Calls `hubspot.create_or_update_contact(first_name, last_name, company_id, job_title, email, linkedin_url)` which searches by name with lock, creates if not exists, handles email conflicts (409/400) by retrying without email, checks company association before creating it
- Returns: Success message with contact ID or error string
- Side Effects: Mutates `self.prospects` list by calling `persona.update_hubspot_contact_id(contact_id)` for matching prospects (first_name, last_name match and hubspot_contact_id is None)
- Error Handling: try/except returns `f"Exception raised creating contact record {first_name} {last_name}: {str(e)}"`

### `Outreach`
**Pattern:** Task Agent  
**Purpose:** Select target individuals for outreach, enrich missing emails, draft personalized initial outreach or follow-up messages referencing events and prospect context  
**LLM:** gpt-5, standard mode, temp=default, timeout=300s

**Prompt Strategy:**
- System prompt contains targeting_criteria and writing_guidelines from campaign AI logic via variable substitution, plus max_search_attempts (3)
- Instructed to search web up to max_search_attempts (3) for additional context if helpful (not required)
- Email enrichment workflow: identify targets first, then search for missing emails only if needed and confidence >50% (expensive operation), never enrich same individual twice
- Must not target individuals already contacted (check account_exec_outreach_phase in past_email_activity from HubSpot)
- Workflow discipline: When researching (web search or email enrichment), respond with actions only (no outreach); when drafting, respond with outreach only (no actions)
- Always explain thinking behind outreach, reference event and individual's relevance, address by name in body
- Context: Accumulates over rerun turns (research → draft)
- JSON Response: `{"explanation": "<reasoning>", "actions": [{"name": "search_web", "args": {"query": "..."}}], "outreach": [{"hubspot_contact_id": "...", "to": "...", "subject": "...", "body": "..."}]}`

**Instance Attributes:**
- `slack_bot: Slack` - For error notifications
- `channel_id: str` - Slack channel for notifications
- `tavily: Tavily` - Web search integration
- `hubspot: HubSpot` - For retrieving past email activity
- `hunter_io: HunterIO` - For email enrichment
- `targeting_criteria: str` - Campaign-specific targeting logic (injected into prompt via substitute_variables)
- `email_guidelines_definition: str` - Campaign-specific email writing guidelines (injected into prompt via substitute_variables)
- `search_attempts: int` - Counter for web searches (max 3), incremented in search_web callable

**Create Parameters:**
- `yaml_config_path: str` - Path to outreach.yaml config
- `workflow_instance_id: UUID` - Workflow instance for tracking
- `slack_bot: Slack` - Initialized Slack integration
- `channel_id: str` - Target Slack channel ID
- `tavily: Tavily` - Initialized Tavily client
- `hubspot: HubSpot` - Initialized HubSpot client
- `hunter_io: HunterIO` - Initialized Hunter.io client
- `targeting_criteria: str` - From campaign AI logic (outreach_selection_logic)
- `email_guidelines_definition: str` - From campaign AI logic (email_guidelines_logic)

#### LLM Callables

**`search_web(query: str) -> str | list[dict]`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Docstring Args: `query (str): The search query to execute`
- Purpose: Search the web for additional context about prospect/company/event (max 3 attempts)
- Integration usage:
  - Calls `tavily.search(query)` which uses Tavily API with exponential backoff retry (up to 5 retries, initial 1s, factor 2.0, jitter ±10%)
- Returns: Search results (list of dicts) or "You've reached the maximum number of search attempts. Do not search again." if limit exceeded
- Side Effects: Increments `self.search_attempts` counter
- Error Handling: Handled by Tavily client with exponential backoff

**`get_past_email_activity(hubspot_contact_id: str) -> str`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Docstring Args: `hubspot_contact_id (str): The ID of the contact to get past email activity for`
- Purpose: Retrieve recent email communication history for contact to inform outreach decisions
- Integration usage:
  - Calls `hubspot.get_recent_contact_emails(hubspot_contact_id)` which retrieves last 5 email engagements with direction, subject, body preview, sent_at via CRM v3, sorted by sent_at descending
- Returns: JSON string of past emails (list of dicts with id, subject, direction, from, to, sent_at, body_preview)
- Error Handling: None specified (errors propagate)

**`search_for_contact_info(first_name: str, last_name: str, company_domain_name: str) -> str`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Docstring Args: `first_name (str), last_name (str), company_domain_name (str)`
- Purpose: Find email address for prospect using Hunter.io email finder
- Integration usage:
  - If SLACK_CHANNEL_OVERRIDE env var set (test mode), returns "This is a test run -- use the email address: alex@qurrent.ai"
  - Otherwise calls `hunter_io.email_finder(company_domain_name, first_name, last_name)` which returns email, confidence score (0-100), sources
- Returns: JSON string with email and confidence score (data.email, data.score), or error message
- Error Handling: try/except returns "Failed to search for contact info" on exception

#### Direct Actions

**`draft_message(event_summary: str, target_personas: List[TargetPersona]) -> List[OutreachMessage]`**
- Purpose: Orchestrate initial outreach drafting for event-based prospects
- Message Thread modification:
  - Appends user message with event summary and JSON list of target individuals (includes past_email_activity from HubSpot via `hubspot.get_contact_email_exchange_stats()`)
- Integration usage:
  - Calls `hubspot.get_contact_email_exchange_stats(contact_id)` for each persona with hubspot_contact_id to get past activity (total_exchanged, last_exchange_at, account_exec_outreach_phase)
- Subagent usage:
  - Invokes self via `await self()` to get agent response
  - Calls `await self.get_rerun_responses(timeout=300)` to wait for actions to complete and get final response
- Returns: List of OutreachMessage objects or empty list if no valid prospects or agent returns no outreach
- Side Effects: Resets `search_attempts` to 0; sends Slack notification if no outreach drafted or no valid prospects after filtering; filters out prospects without valid hubspot_contact_id before drafting
- Error Handling: Filters out prospects without hubspot_contact_id, logs filtered count; returns empty list with Slack notification if no valid prospects or no outreach in response

**`draft_follow_up(hubspot_contact: Dict) -> Optional[OutreachMessage]`**
- Purpose: Draft follow-up email for contact in follow-up queue
- Message Thread modification:
  - Appends user message with contact details string (hubspot_contact_id, first_name, last_name, email, company_name, account_exec_email_subject, account_exec_email_body, account_exec_outreach_trigger)
  - Message includes phase-specific instructions if account_exec_outreach_phase present: "Draft a single, short follow-up email to the following contact. This is follow-up number {phase}. Be sure to reference the last email, but make this one distinct. You MUST use the exact same subject line and email address as the last email. Do not add Re: or any other modifications to the subject line."
  - Otherwise uses initial outreach prompt: "Draft an outreach message to the following contact. Prior to writing and enriching, search the web for information about the contact and the company and check past email activity."
- Integration usage: None (contact details already provided by caller from HubSpot)
- Subagent usage:
  - Invokes self via `await self()` to get agent response
  - Calls `await self.get_rerun_responses(timeout=300)` to wait for actions to complete and get final response
- Returns: OutreachMessage object for first message in response, or None if drafting failed
- Side Effects: Sends Slack notification if no outreach drafted
- Error Handling: Returns None if response contains no outreach messages

## YAML Configuration
*Credentials used -- provide keys, not values*

CUSTOMER_KEY_DEV

LLM_KEYS:
    ANTHROPIC_API_KEY
    OPENAI_API_KEY

HUBSPOT:
    HUBSPOT_API_KEY
    HUBSPOT_PORTAL_ID

HUNTER_IO:
    HUNTER_IO_API_KEY

SENDGRID:
    SENDGRID_API_KEY

TAVILY:
    TAVILY_API_KEY

EXA:
    EXA_API_KEY

SLACK:
    SLACK_BOT_TOKEN
    SLACK_SIGNING_SECRET
    SLACK_CHANNEL_ID

GOOGLE_DRIVE:
    AE_SERVICE_ACCOUNT_JSON (env var - service account JSON as string)
    # Alternative: GOOGLE_APPLICATION_CREDENTIALS (env var - path to JSON file)

ENVIRONMENT:
    ENVIRONMENT (development | production - controls demo record behavior)
    SLACK_CHANNEL_OVERRIDE (optional - override target channel, enables test mode for email addresses)
    START_IMMEDIATELY (optional - "true" to run campaigns on startup instead of waiting for schedule)

## Utils

**`MetricsTracker` (metrics.py)**
- Purpose: Track email engagement metrics per workflow and email, avoid duplicate event logging (delivered/bounce once, open unlimited), support webhook lookups to find workflow by email
- Implementation: Thread-safe singleton with RLock for file operations, stores data in JSON files per workflow (`data/email_metrics/email_metrics_{workflow_id}.json`), atomic writes via temp file + rename to prevent corruption, best-effort permissions handling for host + docker usage (setgid directories, group-writable)
- Key Methods:
  - `initialize_metrics(workflow_instance_id, recipient_emails)`: Create/update JSON with email → counters/events mapping (open_count, delivered_count, bounce_count, events arrays with timestamps)
  - `should_log_event(workflow_instance_id, email, event_type)`: Return True if event not yet logged (delivered/bounce once only, open unlimited)
  - `record_event(workflow_instance_id, email, event_type)`: Increment counter, append timestamp to events array, save atomically
  - `find_workflow_for_email(email)`: Search all metrics files in `data/email_metrics/` to find workflow for given email (for webhooks without workflow context)
- Dependencies: `threading`, `tempfile`, `json`, `pathlib`, `os`

**`GoogleDriveClient` (api/gdrive_utils.py)**
- Purpose: Fetch campaign definition documents from Google Drive using service account authentication
- Implementation: Async wrapper around google-api-python-client, uses `asyncio.to_thread` for sync API calls, reads AE_SERVICE_ACCOUNT_JSON env var or GOOGLE_APPLICATION_CREDENTIALS path
- Key Methods:
  - `list_files_in_folder(folder_id)`: Return list of Google Docs in folder with metadata (id, name, mimeType, size, modifiedTime, createdTime)
  - `download_file_content(file_id)`: Export Google Doc as plain text (mimeType="text/plain"), downloads in chunks
- Dependencies: `google-auth==2.x`, `google-api-python-client`, `google-auth-httplib2`

**Timezone Helpers (models.py)**
- Purpose: Centralized timezone handling for Pacific Time conversions and storage formatting
- Key Functions:
  - `now_pacific()`: Return current datetime in America/Los_Angeles timezone
  - `as_pacific(dt)`: Convert datetime to Pacific timezone
  - `format_pacific(dt)`: Format datetime as "YYYY-MM-DD HH:MM:SS" in Pacific (STORAGE_DT_FMT)
  - `parse_pacific(timestamp_str)`: Parse storage format string to Pacific datetime
- Dependencies: `zoneinfo`, `datetime`

**Deterministic Follow-up Scheduling (server.py)**
- Purpose: Calculate deterministic random follow-up times per campaign to avoid detection patterns while remaining reproducible
- Implementation: `time_until_follow_ups(campaign)` uses SHA256 hash of `{campaign.id}:{date}` to generate hour (10-13) and minute (0-59) within 10am-2pm PT window, returns seconds until target time
- Dependencies: `hashlib`, `datetime`, `zoneinfo`

## Dependencies

- `qurrent` - Qurrent OS SDK (Workflow, Agent, Slack, events, WebServer, LLM decorators, QurrentConfig, spawn_task)
- `exa-py==1.14.16` - Exa API client for websets and research
- `tavily-python` - Tavily web search API
- `sendgrid` - SendGrid email delivery API
- `aiohttp` - Async HTTP client for HubSpot and internal APIs
- `httpx` - Async HTTP client for metrics posting to Supervisor API
- `requests` - Sync HTTP client for Hunter.io
- `google-auth` - Google service account authentication
- `google-api-python-client` - Google Drive API client
- `google-auth-httplib2` - Google auth HTTP adapter
- `google-auth-oauthlib` - Google OAuth library
- `google-cloud-storage` - GCP storage (for blob store integration)
- `pydantic>=2.5` - Data validation and models (BaseModel for TargetPersona, OutreachMessage, LogicDefinition, Campaign)
- `loguru` - Structured logging
- `uvloop` - High-performance event loop
- `feedparser` - RSS parsing (unused in current implementation)
- `trafilatura` - Web content extraction (unused in current implementation)
- `pandas` - Data manipulation (unused in current implementation)
- `requests-html` - HTML parsing (unused in current implementation)
- `lxml_html_clean` - HTML cleaning (unused in current implementation)
- `python-docx` - Word document processing (unused in current implementation)
- `opentelemetry-api` - Observability and tracing
- `opentelemetry-sdk` - Observability SDK
- `opentelemetry-exporter-gcp-trace` - GCP trace exporter

## Integrations

### Prebuilt: `qurrent.Slack`
- Required Config Section: `SLACK`
- Required Keys:
  - `SLACK_BOT_TOKEN: str` - Bot user OAuth token with channels:write, chat:write scopes
  - `SLACK_SIGNING_SECRET: str` - Signing secret for webhook verification
  - `SLACK_CHANNEL_ID: str` - Default channel ID for notifications
- Methods Used:
  - `send_message(channel_id, message)`: Send markdown-formatted message to channel
  - `link(workflow_instance_id, channel_id)`: Associate workflow with channel for command routing (used during campaign configuration)
  - `unlink(channel_id)`: Remove workflow-channel association (used after campaign configuration completes)
- Commands: `/configure-campaigns` triggers immediate campaign refresh via server event loop

### Custom: `HubSpot`
**Location:** `prospecting/api/hubspot.py`  
**Type:** Two-way (queries and creates/updates records)

**Config Section:** `HUBSPOT`
- `HUBSPOT_API_KEY: str` - Private app token with CRM scopes (contacts, companies, associations, emails)
- `HUBSPOT_PORTAL_ID: str (optional)` - Portal/account ID

**Custom Properties Used:**
- Contacts: `account_exec_email_subject`, `account_exec_email_body`, `account_exec_outreach_trigger`, `account_exec_outreach_phase`, `account_exec_next_outreach_date`, `is_demo_record`
- Companies: `is_demo_record`

**Methods:**

**`keyword_search_companies(keyword: str, limit: int = 100) -> List[dict]`**
- Performs: Fuzzy search for companies using CONTAINS_TOKEN operator on name and domain properties
- Behavior: Returns up to limit companies with id, name, domain, description, parent_id properties
- Returns: List of company dicts

**`create_company(company_name: str, company_description: str) -> dict`**
- Performs: Create new company record with is_demo_record flag if ENVIRONMENT=development
- Behavior: Uses company name lock to prevent race conditions, searches by name first, creates if not exists, handles 409 conflict by returning existing record
- Returns: Company object with id

**`update_company(company_id: str, properties: Dict[str, str]) -> dict`**
- Performs: Update company properties (protected by demo record check in development mode)
- Behavior: Fetches company to check is_demo_record flag, only updates if is_demo_record=YES or ENVIRONMENT=production
- Returns: Updated company object or empty dict if skipped

**`associate_parent_company(parent_company_id: str, child_company_id: str) -> dict`**
- Performs: Create parent-child association between companies using batch associations API (type: company_to_company, label: child_to_parent)
- Behavior: Handles 409 if association already exists, returns {"status": "already_exists"}
- Returns: Association response or status dict

**`create_or_update_contact(first_name: str, last_name: str, company_id: str, job_title: str, email: Optional[str], linkedin_url: Optional[str]) -> dict`**
- Performs: Create or update contact by name, populate missing fields only (non-destructive updates), associate with company
- Behavior: Uses contact name lock (first_name::last_name lowercase key), searches by first+last name, creates if not exists, handles email conflicts (409/400) by retrying without email property, checks company association before creating it to avoid redundant API calls
- Returns: Contact object with id

**`update_contact(contact_id: str, properties: Dict[str, Any]) -> dict`**
- Performs: Update contact properties (protected by demo record check in development mode)
- Behavior: Fetches contact to verify is_demo_record flag, pre-checks email uniqueness via `_search_contact_by_email()`, retries without email on 400/409 conflicts, only updates if is_demo_record=YES or ENVIRONMENT=production
- Returns: Updated contact object or empty dict if skipped

**`is_contact_demo_record(contact_id: str) -> bool`**
- Performs: Check if contact has is_demo_record=YES property
- Behavior: Fetches contact with single property, returns False on 404 or missing/non-YES value
- Returns: Boolean

**`get_recent_contact_emails(contact_id: str, limit: int = 5, start_timestamp: Optional[int], end_timestamp: Optional[int]) -> List[Dict]`**
- Performs: Retrieve recent email engagements for contact with cleaned body previews (HTML stripped)
- Behavior: Fetches associated email objects via CRM v3 associations and batch read, sorts by sent_at descending, filters by timestamp window if provided
- Returns: List of email dicts with id, subject, direction (OUTGOING_EMAIL/INCOMING_EMAIL), from, to, sent_at, body_preview

**`get_contact_email_exchange_stats(contact_id: str, start_timestamp: Optional[int], end_timestamp: Optional[int]) -> Dict[str, Union[int, Optional[str]]]`**
- Performs: Return total email count, last exchange timestamp, and current outreach phase for contact
- Behavior: Calls `get_contact_email_summary()` for count/timestamp, fetches account_exec_outreach_phase property separately
- Returns: Dict with total_exchanged (int), last_exchange_at (str or None), account_exec_outreach_phase (str or None)

**`get_contacts_requiring_follow_up() -> List[dict]`**
- Performs: Query contacts where account_exec_next_outreach_date falls within today's PT window (00:00-24:00 as UTC epoch ms)
- Behavior: Calculates Pacific date boundaries (today 00:00 PT and tomorrow 00:00 PT) as UTC timestamps, searches with GTE/LT filters on account_exec_next_outreach_date property, fetches associated company name for each contact via associations API
- Returns: List of contact dicts with hubspot_contact_id, email, account_exec_email_subject, account_exec_email_body, account_exec_outreach_phase, account_exec_outreach_trigger, first_name, last_name, company_name

**`delete_demo_records() -> None`**
- Performs: Delete all contacts and companies where is_demo_record=YES (development cleanup utility)
- Behavior: Searches for demo records in batches of 100, deletes each via CRM v3, handles 404 gracefully, logs counts
- Returns: None (logs counts to console)

### Custom: `HunterIO`
**Location:** `prospecting/api/hunterio.py`  
**Type:** One-way (queries only)

**Config Section:** `HUNTER_IO`
- `HUNTER_IO_API_KEY: str` - Hunter.io API key

**Methods:**

**`email_finder(domain: str, first_name: str, last_name: str) -> dict`**
- Performs: Find most likely email address for person at company using Hunter.io API
- Sample Data: None (real API calls)
- Behavior: Returns email, confidence score (0-100), sources in response.data
- Returns: Dict with data.email, data.score fields

### Custom: `Tavily`
**Location:** `prospecting/api/tavily.py`  
**Type:** One-way (queries only)

**Config Section:** `TAVILY`
- `TAVILY_API_KEY: str` - Tavily API key

**Methods:**

**`search(query: str, max_retries: int = 5) -> list[dict]`**
- Performs: Web search with exponential backoff retry mechanism
- Sample Data: None (real API calls)
- Behavior: Retries up to max_retries on any exception, uses exponential backoff with jitter (initial 1s, factor 2.0, jitter ±10%)
- Returns: List of search result dicts

### Custom: `SendGrid`
**Location:** `prospecting/api/sengrid.py`  
**Type:** One-way (sends emails, receives webhooks separately via server)

**Config Section:** `SENDGRID`
- `SENDGRID_API_KEY: str` - SendGrid API key

**Methods:**

**`send_email(outreach_message: OutreachMessage, from_email: str = "cole@qurrent.ai", from_name: str = "Cole Salquist", bcc_emails: list[str] = ["48618838@bcc.hubspot.com"], is_demo_record: bool = True) -> bool`**
- Performs: Send HTML email with signature appended from cole_email_signature.html
- Behavior:
  - If is_demo_record, overrides recipient to alex@qurrent.ai regardless of outreach_message.to
  - Appends cole_email_signature.html content to body
  - Adds BCC recipients (default includes HubSpot logging address: 48618838@bcc.hubspot.com)
  - Sends via SendGrid API with HTML content type
- Returns: True if status 200/201/202, False otherwise

**Webhook Handler (server.py):**
- `SendGridWebhook.start(config, host="0.0.0.0", port=8000, webhook_endpoint="/sendgrid-event")`: Starts WebServer with POST endpoint
- `handle_sendgrid_event(event, config)`: Processes webhook events (open, delivered, bounce) by:
  1. Parsing payload (single dict or list of dicts)
  2. Finding workflow via `MetricsTracker.find_workflow_for_email(email)` (file IO in thread)
  3. Checking if should log via `MetricsTracker.should_log_event()` (file IO in thread)
  4. Posting to Supervisor API via httpx: `POST https://external.qurrent.ai/dev/metrics_data` with metric_id, workflow_instance_id, measure=1.0
  5. Recording locally via `MetricsTracker.record_event()` (file IO in thread)
- Events:
  - `SendGridWebhookEvent`: Custom event type with workflow_instance_id=-1 (placeholder), data=payload
  - Triggered: Webhook posts JSON to /sendgrid-event
  - Fields: event (type string), email (recipient), timestamp, and various metadata
  - Handling: Async via ingress queue with `spawn_task`, uses httpx for HTTP, uses `asyncio.to_thread` for file IO
- Metric Mappings:
  - open → 01990cd2-cc11-7902-82c0-d3d9d6f783ca
  - bounce → 01990cd3-894d-705a-8295-049f6acd7fff
  - delivered → 01990cd3-e918-7ae5-824e-33637e68a892

### Custom: `GoogleDriveClient`
**Location:** `prospecting/api/gdrive_utils.py`  
**Type:** One-way (reads files)

**Config Section:** `GOOGLE_DRIVE`
- `AE_SERVICE_ACCOUNT_JSON: str (env var)` - Service account JSON as string (preferred, set by load_secrets.py from Secret Manager)
- `GOOGLE_APPLICATION_CREDENTIALS: str (env var, alternative)` - Path to service account JSON file

**Methods:**

**`list_files_in_folder(folder_id: str) -> List[Dict]`**
- Performs: List Google Docs in folder with metadata
- Behavior: Queries Drive API v3 with mimeType filter for application/vnd.google-apps.document, returns files with properties
- Returns: List of file metadata dicts with id, name, mimeType, size, modifiedTime, createdTime

**`download_file_content(file_id: str) -> str`**
- Performs: Export Google Doc as plain text
- Behavior: Uses export_media with mimeType="text/plain", downloads content in chunks, wraps sync calls in `asyncio.to_thread`
- Returns: Plain text content as string

### External: Exa API
**Location:** `exa-py==1.14.16` library imported in workflow.py  
**Type:** One-way (queries websets and research API)

**Config Section:** `EXA`
- `EXA_API_KEY: str` - Exa API key

**Methods Used:**

**`exa.request(f"/websets/v0/websets/{webset_id}", method="GET", params={"expand": ["items"]}) -> dict`**
- Performs: Fetch webset with items and enrichments expanded
- Behavior: Returns webset object with items array, each item has enrichments array with summary strings (enrichments[0]["result"][0])
- Returns: Dict with items (list of dicts with enrichments arrays)

**`ResearchClient(exa).create_task(instructions: str, model: "exa-research", output_schema: dict) -> Task`**
- Performs: Initiate deep research task with structured output matching provided schema
- Behavior: Creates async research task, returns Task object with id. Workflow polls with `research_client.get_task(task.id)` in loop with 1 second sleep until status="completed". Extracts data.research_results from completed task.
- Returns: Task object with id, status, data (contains research_results array matching output schema when status="completed")
