# Workforce Specification: AI Account Executive

**Contributors:** Alex Reents, Alex McConville, Andrey Tretyak

## Overview

The AI Account Executive is an automated sales prospecting and outreach workforce that identifies compelling business events, researches relevant target personas, manages CRM records, and drafts personalized email outreach to decision-makers. The system continuously monitors curated news feeds (via Exa websets) for events that match campaign criteria, extracts key individuals at affected companies, enriches and creates CRM records in HubSpot, and sends targeted emails through SendGrid with multi-stage follow-up sequences.

The workflow operates on a daily schedule: event-based outreach runs at 8am Pacific, and follow-ups occur at deterministic times between 10am-2pm Pacific. Campaign logic is defined in Google Docs stored in a shared folder, which the system parses into structured targeting and messaging guidelines. The workforce tracks email engagement metrics (opens, bounces, deliveries) via SendGrid webhooks and automatically removes prospects from follow-up sequences when they respond.

Value proposition: This workforce enables scalable, event-driven prospecting with minimal human intervention. By automating research, CRM hygiene, email composition, and follow-up cadence, it allows sales teams to engage dozens of prospects daily with highly personalized, contextually relevant outreach—triggered by real-time business signals rather than cold outreach.

## Custom Instructions
*FDE-provided instructions for how this particular workforce specification should be configured*
<!--
[No custom instructions provided for this workforce]
-->

## Decision Audit

### Campaign Configuration Decisions

- [1] **Detect new or modified campaign definitions**
    - Inputs: Google Drive folder contents, last-modified timestamps, stored campaign records
    - Outputs: List of campaigns requiring configuration or update
    - Decision logic: Compare modification timestamps of Google Docs in the campaign folder against locally stored timestamps; identify new documents (not in storage) or updated documents (timestamp mismatch)
    - Logic location: internal code

- [2] **Parse campaign definition into structured logic**
    - Inputs: Campaign definition document (Google Doc text), existing logic (if update)
    - Outputs: Structured logic definition with five components (compelling event, target company, target personas, outreach selection, email guidelines) and Exa webset ID
    - Decision logic: LLM analyzes document content and sorts unstructured campaign instructions into predefined sections; validates that all required sections are present and webset ID is provided; if uncertain or sections are missing, requests clarification from campaign manager via Slack
    - Logic location: internal prompt (CampaignManager agent)

- [3] **Request clarification for incomplete definitions**
    - Inputs: Campaign document, identified gaps or ambiguities
    - Outputs: Slack message to campaign manager, wait for document update
    - Decision logic: If required logic sections are missing or instructions are unclear, send Slack message requesting manager update the document directly (not respond via Slack), then fetch updated document and re-parse
    - Logic location: internal prompt (CampaignManager agent)

### Event Selection & Research Decisions

- [4] **Select qualifying events from webset**
    - Inputs: News event summaries from Exa webset, compelling event criteria, target company criteria, past 30 days of selected events
    - Outputs: List of event summary strings that qualify for prospecting, reasoning explanation
    - Decision logic: LLM evaluates each webset item against compelling event definition and target company definition; excludes events already processed in past 30 days; returns deduplicated list with qualitative reasoning
    - Logic location: internal prompt (EventSelector agent)

- [5] **Identify target personas for each qualifying event**
    - Inputs: Event summary, target persona criteria
    - Outputs: List of individuals with name, title, company, domain, location, email (if found), LinkedIn URL, relevance explanation
    - Decision logic: Exa Research API performs deep research to identify decision-makers associated with the event who match target persona criteria; extracts structured contact information
    - Logic location: external (Exa Research API)

### CRM Management Decisions

- [6] **Determine if company exists in CRM**
    - Inputs: Company name from research, keyword search results from HubSpot
    - Outputs: Existing company record ID or decision to create new record
    - Decision logic: LLM performs keyword search using brand acronyms or domain tokens likely to match company name/domain; if results found, selects matching record; if no match, proceeds to create new company
    - Logic location: internal prompt (CRMManager agent)

- [7] **Create or update company record**
    - Inputs: Company name, company description (from event context), parent company relationship (if identified)
    - Outputs: Company record created/updated in HubSpot, description includes event mention
    - Decision logic: If company doesn't exist, create new record with description; if company exists, update description to mention news event; if parent/portfolio relationship inferred from event, create association after searching for parent company ID
    - Logic location: internal prompt (CRMManager agent)

- [8] **Create or update contact record**
    - Inputs: First name, last name, job title, company ID, email (optional), LinkedIn URL (optional)
    - Outputs: Contact record created/updated in HubSpot, associated with company, hubspot_contact_id assigned to TargetPersona
    - Decision logic: Search for contact by first and last name; if exists, update only missing fields (job title, email, LinkedIn); if new, create contact with all provided fields; ensure association to company record; store HubSpot contact ID back to TargetPersona object for downstream use
    - Logic location: internal prompt (CRMManager agent) and code

### Outreach Selection & Composition Decisions

- [9] **Select individuals for initial outreach**
    - Inputs: List of target personas with HubSpot contact IDs, past email activity, targeting criteria, event summary
    - Outputs: Subset of personas selected for outreach (those meeting criteria and having valid email addresses)
    - Decision logic: LLM evaluates each persona against targeting criteria; excludes individuals with existing outreach phase (already contacted); requires valid email address (searches using Hunter.io if not provided); only proceeds if confidence score is above 50%
    - Logic location: internal prompt (Outreach agent)

- [10] **Enrich missing email addresses**
    - Inputs: First name, last name, company domain, existing email (if any)
    - Outputs: Email address and confidence score, or failure message
    - Decision logic: If email missing or needs verification, invoke Hunter.io email finder with name and domain; only use email if confidence score ≥50%; if test environment, override with test email; if enrichment fails or confidence low, exclude individual from outreach
    - Logic location: internal prompt (Outreach agent) triggers action

- [11] **Conduct web research to personalize message**
    - Inputs: Search query (typically about individual, company, or event), max 3 search attempts
    - Outputs: Web search results from Tavily
    - Decision logic: LLM decides whether additional context is needed to personalize outreach; if yes, constructs search query and invokes Tavily search (up to 3 attempts); uses results to inform email composition
    - Logic location: internal prompt (Outreach agent)

- [12] **Draft personalized outreach email**
    - Inputs: Event summary, selected individual details, web research results, email writing guidelines, past email activity
    - Outputs: Email with subject, body, recipient address, HubSpot contact ID
    - Decision logic: LLM composes personalized email referencing the specific event and individual's relevance; follows writing guidelines (tone, structure, personalization); addresses individual by name; explains connection between event and recipient; no email drafted if individual excluded in selection step
    - Logic location: internal prompt (Outreach agent)

- [13] **Send email or redirect to test address**
    - Inputs: Outreach message, recipient HubSpot contact ID
    - Outputs: Email sent via SendGrid, CRM updated with outreach metadata
    - Decision logic: Check if contact is demo record; if demo or test environment, send to test address (alex@qurrent.ai); otherwise send to actual recipient; BCC HubSpot (48618838@bcc.hubspot.com) for activity logging; append email signature; update HubSpot contact with subject, body, trigger event, phase "1", and next outreach date (+3 days)
    - Logic location: internal code

### Follow-up Decisions

- [14] **Identify contacts requiring follow-up**
    - Inputs: Current date (Pacific time), HubSpot contact property account_exec_next_outreach_date
    - Outputs: List of contacts with next outreach date matching today
    - Decision logic: Query HubSpot for contacts where account_exec_next_outreach_date falls within today's Pacific timezone window (00:00:00 to 24:00:00); return contact details including outreach phase, last email content, and trigger event
    - Logic location: internal code

- [15] **Check if contact has responded**
    - Inputs: HubSpot contact ID, recent email activity
    - Outputs: Decision to remove from follow-up queue or continue with follow-up
    - Decision logic: Retrieve recent emails for contact; check for any incoming emails (direction = INCOMING_EMAIL); if response detected, remove contact from follow-up queue (clear outreach phase and next outreach date), increment reply metric, notify via Slack; otherwise proceed with follow-up
    - Logic location: internal code

- [16] **Draft follow-up email**
    - Inputs: Contact details, last outreach subject/body, original trigger event, current outreach phase (1, 2, or 3)
    - Outputs: Follow-up email with same subject line, distinct body content
    - Decision logic: LLM composes short follow-up email referencing previous email; makes message distinct from prior outreach while maintaining context; uses exact same subject line and email address (no "Re:" prefix); follows phase-specific prompting (emphasize brevity and reference to last email for follow-ups)
    - Logic location: internal prompt (Outreach agent)

- [17] **Determine next follow-up timing**
    - Inputs: Current outreach phase (1, 2, 3), current date
    - Outputs: Next outreach date or empty string (if no further follow-ups)
    - Decision logic: Apply follow-up delay schedule: after phase 1 (initial) → +3 days; after phase 2 (first follow-up) → +5 days; after phase 3 (second follow-up) → +7 days; after phase 4 (third follow-up) → no further follow-ups (empty string); update contact's account_exec_outreach_phase and account_exec_next_outreach_date
    - Logic location: internal code

### Operational & Scheduling Decisions

- [18] **Schedule daily event outreach runs**
    - Inputs: Campaign configuration, current time (Pacific)
    - Outputs: Workflow execution at 8am Pacific daily
    - Decision logic: Calculate seconds until next 8am Pacific; if already past 8am today, schedule for 8am tomorrow; execute event-based outreach workflow (event selection, research, CRM update, outreach drafting/sending); repeat daily
    - Logic location: internal code

- [19] **Schedule daily follow-up runs**
    - Inputs: Campaign ID, current date, current time (Pacific)
    - Outputs: Workflow execution at deterministic time between 10am-2pm Pacific daily
    - Decision logic: Hash campaign ID + date to generate consistent hour (10-13) and minute (0-59) within follow-up window; if today's window passed, calculate for tomorrow; execute follow-up workflow (identify due contacts, check responses, draft/send follow-ups); repeat daily
    - Logic location: internal code

- [20] **Refresh campaign configurations**
    - Inputs: Current time (Pacific), scheduled refresh time (7am)
    - Outputs: Re-run campaign configuration workflow to detect new/modified Google Docs
    - Decision logic: Every day at 7am Pacific, run campaign configuration workflow to check for new or updated campaign definitions in Google Drive folder; update local campaign storage; schedule new event/follow-up tasks for any new campaigns
    - Logic location: internal code

- [21] **Process SendGrid webhook events**
    - Inputs: SendGrid webhook payload (email events: open, bounce, delivered)
    - Outputs: Metrics logged to Supervisor, local tracking updated
    - Decision logic: Extract event type and recipient email from webhook; find workflow instance ID by searching metrics files; check if event should be logged (delivered/bounce logged once, opens logged multiple times); if should log, post metric to Supervisor API and record event locally with timestamp
    - Logic location: internal code

## Agent Design

### Console Agents

#### `researcher`
**Type:** Console Agent (method with `@console_agent` decorator)
**Purpose:** Orchestrates event discovery and prospect research
**Docstring:** "Research agent responsible for analyzing articles to find compelling events to seed targeted email outreach"

**Observable Tasks:**

**`get_webset_events(webset_id: str)`**
- `@observable` decorator
- Docstring: "Fetch recent webset items and return event summaries built from enrichments"
- Purpose: Retrieves news items from Exa webset and filters them through event selection criteria
- Technical Agent Calls: 
  - Creates `EventSelector` agent with compelling event logic, target company logic, and webset data
  - Calls `event_selector.select_events()` to get reasoning and filtered event summaries
- Integration Calls: 
  - `self.exa.request()` to fetch webset items with enrichments
  - `self.slack_bot.send_message()` to notify of reasoning and selected events
- Observability Output: `save_to_console(type='observable_output', content="Webset '{webset_id}' returned {count} recent items\n{summaries}\nReasoning: {reasoning}")`
- Returns: List of event summary strings

**`research_prospects(news_events: List[str])`**
- `@observable` decorator
- Docstring: "Research prospects for qualified events in parallel with error handling"
- Purpose: For each qualifying event, performs deep research to identify target personas
- Technical Agent Calls: None (uses direct workflow method)
- Integration Calls:
  - Spawns parallel tasks calling `self.research_event()` for each event
  - `self.research_event()` uses Exa Research API to identify personas
- Observability Output: `save_to_console(type='observable_output', content="Research completed for {count} events:\n- {event}: {prospect_count} prospects")`
- Returns: List of tuples (event_summary, List[TargetPersona])

#### `record_manager`
**Type:** Console Agent (method with `@console_agent` decorator)
**Purpose:** Orchestrates CRM record creation and updates
**Docstring:** "Agent responsible for managing the CRM"

**Observable Tasks:**

**`update_crm(prospects_with_events: List[Tuple[str, List[TargetPersona]]])`**
- `@observable` decorator
- Docstring: "Updating the CRM with the prospect research"
- Purpose: Creates/updates company and contact records for all researched prospects
- Technical Agent Calls:
  - Creates `CRMManager` agent for each event with prospects list
  - Appends user message with event summary and prospects JSON to agent's message thread
  - Calls `crm_manager()` with `run_actions_in_parallel=True` to invoke LLM
  - Calls `crm_manager.get_rerun_responses(wait_for_all=True, timeout=300)` to await action completion
- Integration Calls: None directly (CRMManager agent invokes HubSpot through @llmcallables)
- Observability Output: `save_to_console(type='observable_output', content="Event processed: {event}\nSummary of updates to CRM: {update_summary}")`
- Returns: List of tuples (event_summary, List[TargetPersona]) with updated hubspot_contact_id values

#### `outreach_manager`
**Type:** Console Agent (method with `@console_agent` decorator)
**Purpose:** Orchestrates email drafting and sending for initial outreach and follow-ups
**Docstring:** "Agent responsible for drafting outreach emails"

**Observable Tasks:**

**`draft_outreach(prospects_with_events: List[Tuple[str, List[TargetPersona]]])`**
- `@observable` decorator
- Docstring: "Draft initial outreach for all events"
- Purpose: For each event with target personas, drafts and sends personalized initial outreach emails
- Technical Agent Calls:
  - Spawns parallel tasks calling `self.send_initial_outreach()` for each event
  - `self.send_initial_outreach()` creates `Outreach` agent and calls `outreach_agent.draft_message()`
- Integration Calls:
  - `self.sendgrid.send_email()` to send emails
  - `self.hubspot.update_contact()` to record outreach metadata and schedule next follow-up
  - `self.hubspot.is_contact_demo_record()` to check if test mode
  - `self.slack_bot.send_message()` to display drafted emails
  - `MetricsTracker.initialize_metrics()` to register emails for tracking
- Observability Output: `save_to_console(type='observable_output', content="Outreach drafted for {count} events:\n- {event}: {message_count} outreach messages")` and per-message output with `save_to_console(type='output', content={recipient: message_body})`
- Returns: None

**`draft_followups()`**
- `@observable` decorator
- Docstring: "Send follow-up emails to prospects"
- Purpose: Identifies contacts due for follow-up and drafts/sends follow-up emails
- Technical Agent Calls:
  - Spawns parallel tasks calling `self.send_followup()` for each contact
  - `self.send_followup()` creates `Outreach` agent and calls `outreach_agent.draft_follow_up()`
- Integration Calls:
  - `self.hubspot.get_contacts_requiring_follow_up()` to retrieve due contacts
  - `self.hubspot.get_recent_contact_emails()` to check for responses
  - `self.hubspot.update_contact()` to update outreach phase and next date
  - `self.sendgrid.send_email()` to send follow-ups
  - `self.slack_bot.send_message()` to display drafted follow-ups
- Observability Output: `save_to_console(type='observable_output', content="Sent follow-up to {recipient}: {subject}")` or "No follow-ups sent" if none; per-message output with `save_to_console(type='output', content={recipient: message_body})`
- Returns: None

### Technical Agents

#### `CampaignManager`
**Type:** Technical Agent (extends `Agent` class)
**Pattern:** Orchestrator
**Purpose:** Parses unstructured campaign definition documents into structured logic definitions for downstream agents
**LLM:** claude-sonnet-4-20250514, standard mode, temp=0 (inferred), timeout=300s

**Prompt Strategy:**
- Expects campaign definition document with sections for compelling event, target company, target personas, outreach selection, email guidelines, and Exa webset ID
- Primary responsibility is sorting unstructured content into structured sections without adding/removing content (except for obvious optimization opportunities or clarifying intentional omissions)
- If uncertain or sections missing, instructs human campaign manager to update document directly (not respond via Slack), then fetches updated document
- Context: Accumulates (receives existing logic for updates, fetches updated document on clarifications)
- JSON Response: `{"actions": [], "logic_definition": {"exa_webset_id": "<id>", "compelling_event_logic": "<text>", "target_company_logic": "<text>", "target_personas_logic": "<text>", "outreach_selection_logic": "<text>", "email_guidelines_logic": "<text>"}}`

**Instance Attributes:**
- `slack_bot: Slack` - Slack integration for sending messages
- `channel_id: str` - Target Slack channel ID
- `google_drive_client: GoogleDriveClient` - Google Drive integration for fetching documents
- `file_id: str` - Current campaign document file ID being processed

**Create Parameters:**
- `yaml_config_path: str` - Path to agent configuration YAML
- `workflow_instance_id: UUID` - Workflow instance for this agent
- `slack_bot: Slack` - Slack integration instance
- `channel_id: str` - Slack channel ID for notifications
- `google_drive_client: GoogleDriveClient` - Google Drive client instance

#### LLM Callables

**`fetch_campaign_logic() -> str`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Docstring Args: None
- Purpose: Fetches latest content of campaign logic document from Google Drive
- Integration usage: Calls `self.google_drive_client.download_file_content(self.file_id)`
- Returns: Document content as plain text
- Error Handling: Raises ValueError if file_id not set

**`send_slack_message(message: str) -> str`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Docstring Args: `message (str): The message to send`
- Purpose: Sends message to Slack channel to communicate with campaign manager
- Integration usage: Calls `self.slack_bot.send_message(channel_id=self.channel_id, message=message)`
- Returns: "The message was sent successfully"

#### `EventSelector`
**Type:** Technical Agent (extends `Agent` class)
**Pattern:** Task
**Purpose:** Filters webset news items to identify events matching campaign criteria
**LLM:** gpt-5, standard mode, temp=0 (inferred), timeout=300s

**Prompt Strategy:**
- Receives compelling event definition and target company definition via variable substitution
- Evaluates numbered list of news event summaries against criteria
- Considers past 30 days of selections to avoid duplicates
- Returns brief reasoning without referencing indices (user isn't aware of index mapping) and list of selected event indices
- Context: Resets per invocation (new agent created for each webset fetch)
- JSON Response: `{"reasoning": "<explanation>", "selections": [0, 3, 7, ...]}`

**Instance Attributes:**
- `exa_webset: Dict` - Webset data structure with items and enrichments
- `today_date: str` - Current date in Pacific timezone (YYYY-MM-DD format)

**Create Parameters:**
- `yaml_config_path: str` - Path to agent configuration YAML
- `workflow_instance_id: UUID` - Workflow instance for this agent
- `compelling_event: str` - Campaign logic for compelling event criteria
- `target_company: str` - Campaign logic for target company criteria
- `exa_webset: Dict` - Webset data from Exa API

#### Direct Actions

**`select_events() -> Tuple[str, List[str]]`**
- Purpose: Orchestrates event selection process
- Message Thread modification:
  - Appends user message with formatted numbered list of event summaries
  - Appends user message with past 30 days of selected event indices
- Integration usage: None
- Subagent usage: None
- Util usage:
  - Uses `self._get_prompt()` to format event summaries
  - Uses `self._get_past_selections()` to load from `data/selected_events.json`
  - Uses `self._get_recent_selections()` to filter last 30 days
- Returns: Tuple of (reasoning string, list of selected event summaries)
- Side Effects: Writes selected event indices to `data/selected_events.json` with today's date as key

#### `CRMManager`
**Type:** Technical Agent (extends `Agent` class)
**Pattern:** Orchestrator
**Purpose:** Creates and updates company and contact records in HubSpot CRM based on research results
**LLM:** gpt-5, standard mode, temp=0 (inferred), timeout=300s

**Prompt Strategy:**
- Receives event summary and list of prospects (JSON) in initial user message
- First checks if companies exist via keyword search using brand acronyms or domain substrings
- Creates or updates company records with event mention in description
- Infers and creates parent/portfolio company relationships when identifiable
- Creates or updates contact records with association to companies
- Can run actions in parallel when efficient, but works iteratively when dependencies exist
- Retries system errors at least once before abandoning CRM update
- Context: Accumulates (receives prospects, action results build up in thread)
- JSON Response: `{"reasoning": "<explanation>", "actions": [{"name": "action_name", "args": {...}}], "summary": "<summary of actions taken>"}`

**Instance Attributes:**
- `hubspot: HubSpot` - HubSpot integration instance
- `prospects: List[TargetPersona]` - List of prospects being processed (updated with contact IDs during execution)

**Create Parameters:**
- `yaml_config_path: str` - Path to agent configuration YAML
- `workflow_instance_id: UUID` - Workflow instance for this agent
- `hubspot: HubSpot` - HubSpot integration instance
- `prospects: List[TargetPersona]` - List of prospects to process

#### LLM Callables

**`keyword_search_companies(keyword: str) -> str`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Docstring Args: `keyword (str): Keyword token to search for (e.g., brand acronym like 'kkr')`
- Purpose: Fuzzy search for companies in HubSpot by keyword across name and domain
- Integration usage: Calls `self.hubspot.keyword_search_companies(keyword)`
- Returns: JSON string of search results with company_id, company_name, domain, company_description, parent_company_id
- Error Handling: try/except returns "Exception raised searching for companies with keyword {keyword}: {error}"

**`add_company_record(company_name: str, company_description: str, parent_company_id: Optional[str] = None) -> str`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Docstring Args: `company_name (str): The name of the company to add`, `company_description (str): The description of the company to add`, `parent_company_id (Optional[str]): The ID of the parent company to add`
- Purpose: Creates new company record in HubSpot and optionally associates with parent company
- Integration usage: 
  - Calls `self.hubspot.create_company(company_name, company_description)`
  - If parent_company_id provided, calls `self.hubspot.associate_parent_company(parent_company_id, child_company_id)`
- Returns: "Successfully created record for company {name} with ID: {id}"
- Error Handling: try/except returns "Exception raised creating company record {name}: {error}"

**`update_company_record(company_id: str, company_description: Optional[str] = None, parent_company_id: Optional[str] = None) -> str`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Docstring Args: `company_id (str): The ID of the company to update`, `company_description (Optional[str]): The updated description of the company`, `parent_company_id (Optional[str]): The updated ID of the parent company`
- Purpose: Updates existing company record properties and parent association
- Integration usage:
  - Calls `self.hubspot.update_company(company_id, {"description": company_description})` if description provided
  - Calls `self.hubspot.associate_parent_company(parent_company_id, company_id)` if parent_company_id provided
- Returns: "Successfully updated company record {company_id}"
- Error Handling: try/except returns "Exception raised updating company record {company_id}: {error}"

**`add_contact_record(first_name: str, last_name: str, company_id: str, job_title: str, email: Optional[str] = None, linkedin_url: Optional[str] = None) -> str`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Docstring Args: `first_name (str): The first name of the contact to add`, `last_name (str): The last name of the contact to add`, `company_id (str): The ID of the company to add the contact to`, `job_title (str): The job title of the contact to add`, `email (Optional[str]): The email of the contact to add`, `linkedin_url (Optional[str]): The LinkedIn URL of the contact to add`
- Purpose: Creates contact record in HubSpot, associates with company, and updates prospects list with contact ID
- Integration usage: Calls `self.hubspot.create_or_update_contact(first_name, last_name, company_id, job_title, email, linkedin_url)`
- Subagent usage: None
- Returns: "Successfully created record for contact {first_name} {last_name} with contact ID: {contact_id}"
- Side Effects: Updates `self.prospects` list by setting `hubspot_contact_id` for matching persona
- Error Handling: try/except returns "Exception raised creating contact record {first_name} {last_name}: {error}"

#### `Outreach`
**Type:** Technical Agent (extends `Agent` class)
**Pattern:** Agentic Search
**Purpose:** Selects target individuals, enriches contact information, researches context, and drafts personalized outreach emails
**LLM:** gpt-5, standard mode, temp=0 (inferred), timeout=300s

**Prompt Strategy:**
- Receives targeting criteria and writing guidelines via variable substitution at creation
- Evaluates which individuals to target based on criteria, requiring valid email addresses
- Can search web up to 3 times for additional context (optional but encouraged)
- Must enrich missing emails via Hunter.io before drafting; excludes if confidence <50% or not found
- Explains reasoning behind outreach and web search decisions
- References event and addresses individual by name in email body
- Two-phase workflow: research/actions phase (respond with actions only), then drafting phase (respond with outreach only)
- Context: Accumulates across phases (research results inform drafting)
- JSON Response: `{"explanation": "<reasoning>", "actions": [{"name": "action_name", "args": {...}}], "outreach": [{"hubspot_contact_id": "<id>", "to": "<email>", "subject": "<subject>", "body": "<html body>"}]}`

**Instance Attributes:**
- `slack_bot: Slack` - Slack integration for notifications
- `channel_id: str` - Target Slack channel ID
- `tavily: Tavily` - Tavily integration for web search
- `hubspot: HubSpot` - HubSpot integration for contact data
- `hunter_io: HunterIO` - Hunter.io integration for email enrichment
- `targeting_criteria: str` - Campaign logic for outreach selection
- `email_guidelines_definition: str` - Campaign logic for email writing guidelines
- `search_attempts: int` - Counter for web searches (max 3, resets per draft_message call)

**Create Parameters:**
- `yaml_config_path: str` - Path to agent configuration YAML
- `workflow_instance_id: UUID` - Workflow instance for this agent
- `slack_bot: Slack` - Slack integration instance
- `channel_id: str` - Slack channel ID for notifications
- `tavily: Tavily` - Tavily integration instance
- `hubspot: HubSpot` - HubSpot integration instance
- `hunter_io: HunterIO` - Hunter.io integration instance
- `targeting_criteria: str` - Campaign outreach selection logic
- `email_guidelines_definition: str` - Campaign email guidelines logic

#### LLM Callables

**`search_web(query: str) -> str | list[dict]`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Docstring Args: `query (str): The search query to execute`
- Purpose: Searches web for context to personalize outreach; limited to 3 attempts
- Integration usage: Calls `self.tavily.search(query)`
- Returns: Search results from Tavily or "You've reached the maximum number of search attempts. Do not search again." if limit exceeded
- Side Effects: Increments `self.search_attempts`

**`get_past_email_activity(hubspot_contact_id: str) -> str`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Docstring Args: `hubspot_contact_id (str): The ID of the contact to get past email activity for`
- Purpose: Retrieves recent email history for contact to inform outreach
- Integration usage: Calls `self.hubspot.get_recent_contact_emails(hubspot_contact_id)`
- Returns: JSON string of email activity (id, subject, direction, from, to, sent_at, body_preview)

**`search_for_contact_info(first_name: str, last_name: str, company_domain_name: str) -> str`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Docstring Args: `first_name (str): The first name of the target persona`, `last_name (str): The last name of the target persona`, `company_domain_name (str): The domain name of the target persona's company`
- Purpose: Finds email address for contact using Hunter.io
- Integration usage: Calls `self.hunter_io.email_finder(company_domain_name, first_name, last_name)`
- Returns: JSON string with email address and confidence score, or "This is a test run -- use the email address: alex@qurrent.ai" if test environment
- Error Handling: try/except with warning log, returns "Failed to search for contact info" on exception

#### Direct Actions

**`draft_message(event_summary: str, target_personas: List[TargetPersona]) -> List[OutreachMessage]`**
- Purpose: Orchestrates drafting of initial outreach messages for an event
- Message Thread modification:
  - Appends user message with event summary and JSON array of target individuals (including past_email_activity from HubSpot)
- Integration usage:
  - Calls `self.hubspot.get_contact_email_exchange_stats()` to get past email activity for each persona
  - Calls `self.slack_bot.send_message()` if no valid prospects or no outreach drafted
- Subagent usage: None
- Util usage: None
- Returns: List of `OutreachMessage` objects
- Side Effects: Resets `self.search_attempts` to 0; filters out personas without valid hubspot_contact_id

**`draft_follow_up(hubspot_contact: Dict) -> Optional[OutreachMessage]`**
- Purpose: Orchestrates drafting of follow-up message for a single contact
- Message Thread modification:
  - Appends user message with contact details (ID, name, email, company, last email subject/body, trigger event, follow-up phase number)
  - Prompt varies: if follow-up phase exists, instructs to draft short follow-up with same subject line; otherwise instructs to draft new outreach with web research
- Integration usage:
  - Calls `self.slack_bot.send_message()` if no outreach drafted
- Subagent usage: None
- Util usage: None
- Returns: `OutreachMessage` object or None if no outreach drafted

## Happy Path Call Stack

```text
→ START EVENT: Scheduled daily run (8am Pacific)
  ├─ @console_agent: ProspectResearch.researcher(task="get_webset_events")
  │  └─ @observable: ProspectResearch.get_webset_events(webset_id)
  │     ├─ exa.request() → webset items with enrichments
  │     ├─ EventSelector() [TA - Task Agent]
  │     │  └─ EventSelector.select_events() [TA direct action]
  │     │     ├─ _get_prompt() → formatted event list
  │     │     ├─ _get_past_selections() → load JSON file
  │     │     ├─ _get_recent_selections() → filter last 30 days
  │     │     ├─ EventSelector() [TA LLM turn]
  │     │     │  └─ Returns {"reasoning": "...", "selections": [0, 3, 7]}
  │     │     └─ Writes selected events to data/selected_events.json
  │     ├─ slack_bot.send_message() → reasoning
  │     └─ slack_bot.send_message() → selected events
  │
  ├─ @console_agent: ProspectResearch.researcher(task="research_prospects", news_events=[...])
  │  └─ @observable: ProspectResearch.research_prospects(news_events)
  │     ├─ spawn_task(research_event(event_summary)) [parallel for each event]
  │     │  └─ research_event() [workflow method]
  │     │     ├─ ResearchClient(exa) → create task
  │     │     ├─ research_client.get_task() [polling loop] → raw_prospects
  │     │     └─ Returns (event_summary, [TargetPersona, ...])
  │     └─ asyncio.gather() → collect results
  │
  ├─ @console_agent: ProspectResearch.record_manager(task="update_crm", prospects_with_events=[...])
  │  └─ @observable: ProspectResearch.update_crm(prospects_with_events)
  │     ├─ spawn_task(update_single_event(event_summary, prospects)) [parallel for each event]
  │     │  └─ update_single_event() [nested async function]
  │     │     ├─ CRMManager() [TA - Orchestrator]
  │     │     ├─ message_thread.append(user message with event + prospects JSON)
  │     │     ├─ crm_manager() [TA LLM turn, run_actions_in_parallel=True]
  │     │     │  └─ @llmcallable: CRMManager.keyword_search_companies()
  │     │     │     └─ hubspot.keyword_search_companies() → company search results
  │     │     ├─ crm_manager.get_rerun_responses(wait_for_all=True, timeout=300)
  │     │     ├─ crm_manager() [TA LLM turn]
  │     │     │  ├─ @llmcallable: CRMManager.add_company_record()
  │     │     │  │  ├─ hubspot.create_company() → company_id
  │     │     │  │  └─ hubspot.associate_parent_company() [if parent exists]
  │     │     │  └─ @llmcallable: CRMManager.update_company_record()
  │     │     │     ├─ hubspot.update_company() → updated company
  │     │     │     └─ hubspot.associate_parent_company() [if parent exists]
  │     │     ├─ crm_manager.get_rerun_responses(wait_for_all=True, timeout=300)
  │     │     ├─ crm_manager() [TA LLM turn]
  │     │     │  └─ @llmcallable: CRMManager.add_contact_record()
  │     │     │     ├─ hubspot.create_or_update_contact() → contact_id
  │     │     │     └─ Updates self.prospects[i].hubspot_contact_id
  │     │     ├─ crm_manager.get_rerun_responses(wait_for_all=True, timeout=300)
  │     │     └─ Returns (event_summary, update_summary, updated_prospects)
  │     └─ asyncio.gather() → collect results
  │
  └─ @console_agent: ProspectResearch.outreach_manager(task="draft_outreach", prospects_with_events=[...])
     └─ @observable: ProspectResearch.draft_outreach(prospects_with_events)
        ├─ spawn_task(send_initial_outreach(event_summary, prospects)) [parallel for each event]
        │  └─ send_initial_outreach() [workflow method]
        │     ├─ Outreach() [TA - Agentic Search]
        │     ├─ outreach_agent.draft_message(event_summary, prospects) [TA direct action]
        │     │  ├─ hubspot.get_contact_email_exchange_stats() → past_email_activity
        │     │  ├─ message_thread.append(user message with event + target_individuals JSON)
        │     │  ├─ outreach_agent() [TA LLM turn - research phase]
        │     │  │  ├─ @llmcallable: Outreach.search_web()
        │     │  │  │  └─ tavily.search() → search results
        │     │  │  └─ @llmcallable: Outreach.search_for_contact_info()
        │     │  │     └─ hunter_io.email_finder() → email + confidence
        │     │  ├─ outreach_agent.get_rerun_responses(timeout=300)
        │     │  ├─ outreach_agent() [TA LLM turn - drafting phase]
        │     │  │  └─ Returns {"explanation": "...", "outreach": [{...}]}
        │     │  └─ Returns [OutreachMessage, ...]
        │     ├─ For each outreach_message:
        │     │  ├─ hubspot.is_contact_demo_record() → is_demo_record
        │     │  ├─ sendgrid.send_email(outreach_message, is_demo_record)
        │     │  └─ hubspot.update_contact(contact_id, {subject, body, trigger, phase: "1", next_date: +3 days})
        │     └─ MetricsTracker.initialize_metrics(workflow_instance_id, emails)
        ├─ asyncio.gather() → collect results
        ├─ For each (event_desc, outreach_messages):
        │  ├─ save_to_console(type="output", content={event_index: event_desc})
        │  ├─ slack_bot.send_message() → outreach subject/to/body
        │  └─ save_to_console(type="output", content={recipient: body})
        └─ save_to_console(type="observable_output", content="Outreach drafted for {count} events")

→ START EVENT: Scheduled daily run (10am-2pm Pacific, deterministic per campaign)
  └─ @console_agent: ProspectResearch.outreach_manager(task="draft_followups")
     └─ @observable: ProspectResearch.draft_followups()
        ├─ hubspot.get_contacts_requiring_follow_up() → follow_up_contacts
        ├─ spawn_task(send_followup(contact, today)) [parallel for each contact]
        │  └─ send_followup() [workflow method]
        │     ├─ hubspot.get_recent_contact_emails() → past_emails
        │     ├─ Check for INCOMING_EMAIL direction:
        │     │  ├─ If response detected:
        │     │  │  ├─ save_metric(metric_id="reply", measure=1)
        │     │  │  ├─ hubspot.update_contact(contact_id, {phase: "", next_date: ""})
        │     │  │  ├─ slack_bot.send_message() → "Removing {name} from follow-up queue"
        │     │  │  └─ Returns None
        │     │  └─ Else continue:
        │     ├─ Outreach() [TA - Agentic Search]
        │     ├─ outreach_agent.draft_follow_up(contact) [TA direct action]
        │     │  ├─ message_thread.append(user message with contact details + history)
        │     │  ├─ outreach_agent() [TA LLM turn]
        │     │  │  └─ Returns {"explanation": "...", "outreach": [{...}]}
        │     │  └─ Returns OutreachMessage or None
        │     ├─ hubspot.is_contact_demo_record() → is_demo_record
        │     ├─ sendgrid.send_email(outreach_message, is_demo_record)
        │     ├─ Calculate next_outreach_date based on phase: {0→3d, 1→5d, 2→7d, 3→""}
        │     ├─ hubspot.update_contact(contact_id, {subject, body, phase: phase+1, next_date})
        │     └─ Returns outreach_message
        ├─ asyncio.gather() → collect results
        ├─ For each successful_followup:
        │  ├─ slack_bot.send_message() → "Drafted {count} follow-up emails"
        │  ├─ slack_bot.send_message() → follow-up subject/to/body
        │  └─ save_to_console(type="output", content={recipient: body})
        └─ save_to_console(type="observable_output", content="Sent follow-up to {recipient}: {subject}")

→ START EVENT: Slack command "/configure-campaigns"
  ├─ CampaignConfiguration() [workflow]
  ├─ slack_bot.link(workflow_instance_id, channel_id)
  ├─ configuration_workflow.get_campaigns()
  │  ├─ Load stored campaigns from data/campaign_definitions.json
  │  ├─ google_drive_client.list_files_in_folder(CAMPAIGN_FOLDER_ID) → drive_files
  │  ├─ For each file_meta in drive_files:
  │  │  ├─ google_drive_client.download_file_content(file_id) → campaign_content
  │  │  ├─ Compare file_modified_time with stored campaign:
  │  │  │  ├─ If new campaign (not in storage):
  │  │  │  │  ├─ CampaignManager() [TA - Orchestrator]
  │  │  │  │  ├─ message_thread.append(user message with campaign_content)
  │  │  │  │  ├─ configuration_workflow.run_campaign_update(file_id)
  │  │  │  │  │  ├─ campaign_manager.file_id = file_id
  │  │  │  │  │  ├─ Loop until logic_definition returned or timeout:
  │  │  │  │  │  │  ├─ campaign_manager() [TA LLM turn]
  │  │  │  │  │  │  │  ├─ @llmcallable: CampaignManager.fetch_campaign_logic() [if needed]
  │  │  │  │  │  │  │  │  └─ google_drive_client.download_file_content(file_id)
  │  │  │  │  │  │  │  ├─ @llmcallable: CampaignManager.send_slack_message() [if clarification needed]
  │  │  │  │  │  │  │  │  └─ slack_bot.send_message()
  │  │  │  │  │  │  │  └─ Returns {"actions": [...], "logic_definition": {...}}
  │  │  │  │  │  │  ├─ campaign_manager.get_rerun_responses(timeout=300) [if actions present]
  │  │  │  │  │  │  ├─ If logic_definition returned: break
  │  │  │  │  │  │  ├─ Else: ingress.get_workflow_event() → wait for Slack message
  │  │  │  │  │  │  └─ message_thread.append(user message from Slack)
  │  │  │  │  │  └─ Returns LogicDefinition
  │  │  │  │  ├─ Create Campaign(id=file_id, name=file_name, logic=logic_definition)
  │  │  │  │  └─ slack_bot.send_message() → "Successfully constructed logic for campaign"
  │  │  │  └─ If modified campaign (timestamp mismatch):
  │  │  │     ├─ message_thread.append(existing logic + updated campaign_content)
  │  │  │     ├─ configuration_workflow.run_campaign_update(file_id) [same as above]
  │  │  │     └─ slack_bot.send_message() → "Successfully updated logic for campaign"
  │  │  └─ If no change: use stored campaign
  │  ├─ Write updated campaigns to data/campaign_definitions.json
  │  └─ Returns campaign_list
  ├─ configuration_workflow.close(status="completed")
  └─ slack_bot.unlink(channel_id)

→ INGRESS EVENT: SendGridWebhookEvent with payload [{event: "open", email: "recipient@example.com", ...}]
  └─ handle_sendgrid_event(event, config)
     ├─ Extract events_list from event.data
     ├─ For each item in events_list:
     │  ├─ Extract event_type and recipient_email
     │  ├─ MetricsTracker.find_workflow_for_email(recipient_email) → workflow_instance_id
     │  ├─ MetricsTracker.should_log_event(workflow_instance_id, recipient_email, event_type)
     │  │  └─ Checks if delivered/bounce already logged once, or open not yet logged
     │  ├─ If should_log:
     │  │  ├─ Map event_type to metric_id (open/bounce/delivered)
     │  │  ├─ http_client.post("dev/metrics_data", body={metric_id, workflow_instance_id, measure=1})
     │  │  └─ MetricsTracker.record_event(workflow_instance_id, recipient_email, event_type)
     │  └─ Else: skip (already logged)
     └─ Returns

→ WORKFLOW COMPLETE: After outreach drafted and sent, or follow-ups sent
```

## Data & Formats

### Referenced Documents Inventory and Input Data

- **Exa Websets**
    - Format: JSON via Exa API
    - Source: Exa API (pre-configured webset ID in campaign definition)
    - Intended Use: Source of news events for event selection phase; each item has enrichments with summary text

- **Campaign Logic Documents (Google Docs)**
    - Format: Plain text (exported from Google Docs)
    - Source: Google Drive folder (ID: 1GZoagbXw4sMYPLQ0cz7s2Q88lTwrbxZV)
    - Intended Use: Human-authored campaign definitions parsed into structured logic by CampaignManager agent; includes compelling event criteria, target company criteria, target persona criteria, outreach selection criteria, email guidelines, and Exa webset ID

- **Stored Campaign Definitions**
    - Format: JSON
    - Source: Local file `data/campaign_definitions.json`
    - Intended Use: Persistent storage of parsed campaign configurations to detect changes and avoid re-parsing unchanged documents

- **Selected Events History**
    - Format: JSON
    - Source: Local file `data/selected_events.json`
    - Intended Use: Track past 30 days of selected events to avoid duplicate processing; keyed by date (YYYY-MM-DD)

- **Email Metrics Tracking**
    - Format: JSON (one file per workflow instance)
    - Source: Local files `data/email_metrics/email_metrics_{workflow_instance_id}.json`
    - Intended Use: Track email events (open, delivered, bounce) per recipient to avoid duplicate metric logging and support SendGrid webhook processing

### Example Output Artifacts

- **Initial Outreach Emails**
    - Type: Email
    - Format: HTML email body via SendGrid
    - Recipients: Target personas identified through research
    - Contents: Personalized subject line, greeting with recipient name, reference to specific event and relevance to recipient, email signature (from cole_email_signature.html), BCC to HubSpot (48618838@bcc.hubspot.com)

- **Follow-up Emails**
    - Type: Email
    - Format: HTML email body via SendGrid
    - Recipients: Contacts with scheduled follow-up dates who have not responded
    - Contents: Same subject line as initial outreach (no "Re:" prefix), brief follow-up message referencing previous email, email signature

- **Slack Notifications**
    - Type: Message
    - Format: Markdown-formatted text in Slack
    - Recipients: Configured Slack channel
    - Contents: Event selection reasoning, selected events list, drafted outreach messages (subject/to/body), follow-up notifications, workflow completion messages, error messages

- **HubSpot Contact Updates**
    - Type: CRM Record Update
    - Format: HubSpot API property updates
    - Recipients: HubSpot contacts involved in outreach
    - Contents: `account_exec_email_subject`, `account_exec_email_body`, `account_exec_outreach_trigger`, `account_exec_outreach_phase` (1-4), `account_exec_next_outreach_date` (epoch milliseconds)

- **Supervisor Metrics**
    - Type: Metric Data Points
    - Format: JSON via Supervisor API
    - Recipients: Qurrent Supervisor observability platform
    - Contents: Metric ID (open/bounce/delivered/reply), workflow instance ID, measure value (1), timestamps

## Integrations

### Prebuilt: `qurrent.Slack`
- Required Config Section: `SLACK_CONFIG`
- Required Keys:
    - `SLACK_BOT_TOKEN: str` - Bot user OAuth token
    - `SLACK_APP_TOKEN: str` - App-level token for socket mode
    - `SLACK_CHANNEL_ID: str` - Default channel ID for notifications

### Custom: `HubSpot`
**Location:** `prospecting/api/hubspot.py`
**Type:** Two-way

**Config Section:** `HUBSPOT_API_KEY`
- `HUBSPOT_API_KEY: str` - HubSpot private app access token
- `HUBSPOT_PORTAL_ID: str` - HubSpot portal/account ID (optional)
- `ENVIRONMENT: str` - "production" or "development" (default); controls demo record restrictions

**Methods:**

**`keyword_search_companies(keyword: str, limit: int = 100) -> List[dict]`**
- Performs: Fuzzy search for companies using CONTAINS_TOKEN operator on name and domain fields
- Returns: List of dicts with company_id, company_name, domain, company_description, parent_company_id

**`create_company(company_name: str, company_description: str) -> dict`**
- Performs: Creates new company record; checks for existing record first to prevent duplicates; sets is_demo_record="YES" if not production
- Returns: HubSpot company object with id and properties

**`update_company(company_id: str, properties: Dict[str, str]) -> dict`**
- Performs: Updates company properties; validates is_demo_record in non-production environments
- Returns: Updated HubSpot company object

**`associate_parent_company(parent_company_id: str, child_company_id: str) -> dict`**
- Performs: Creates parent-child company association using batch associations API
- Returns: API response or {"status": "already_exists"} if 409 conflict

**`create_or_update_contact(first_name: str, last_name: str, company_id: str, job_title: str, email: Optional[str] = None, linkedin_url: Optional[str] = None) -> dict`**
- Performs: Searches for contact by name; if exists, updates only missing fields; if new, creates contact; ensures association to company; sets is_demo_record="YES" if not production
- Returns: HubSpot contact object with id and properties

**`update_contact(contact_id: str, properties: Dict[str, Any]) -> dict`**
- Performs: Updates contact properties; validates is_demo_record in non-production; pre-checks for email uniqueness to avoid conflicts
- Returns: Updated HubSpot contact object or {} if contact not found or invalid

**`is_contact_demo_record(contact_id: str) -> bool`**
- Performs: Checks if contact has is_demo_record property set to "YES"
- Returns: True if demo record, False otherwise or if contact not found

**`get_recent_contact_emails(contact_id: str, limit: int = 5, start_timestamp: Optional[int] = None, end_timestamp: Optional[int] = None) -> List[Dict[str, Optional[str]]]`**
- Performs: Retrieves recent email engagements for contact via CRM v3 API; returns cleaned email objects with id, subject, direction, from, to, sent_at, body_preview (truncated to 1000 chars)
- Returns: List of email dicts sorted by sent_at descending

**`get_contact_email_exchange_stats(contact_id: str, start_timestamp: Optional[int] = None, end_timestamp: Optional[int] = None) -> Dict[str, Union[int, Optional[str]]]`**
- Performs: Returns summary statistics of email exchanges with contact; includes total_exchanged count, last_exchange_at timestamp, and account_exec_outreach_phase from contact properties
- Returns: Dict with total_exchanged, last_exchange_at, account_exec_outreach_phase

**`get_contacts_requiring_follow_up() -> List[dict]`**
- Performs: Queries contacts where account_exec_next_outreach_date falls within today's Pacific timezone window (epoch milliseconds); retrieves contact properties and associated company name
- Returns: List of dicts with hubspot_contact_id, email, account_exec_email_subject, account_exec_email_body, account_exec_next_outreach_date, account_exec_outreach_phase, account_exec_outreach_trigger, first_name, last_name, company_name

**`delete_demo_records() -> None`**
- Performs: Searches for and deletes all contacts and companies with is_demo_record="YES" property
- Returns: None (logs deletion counts)

### Custom: `HunterIO`
**Location:** `prospecting/api/hunterio.py`
**Type:** One-way

**Config Section:** `HUNTER_IO_API_KEY`
- `HUNTER_IO_API_KEY: str` - Hunter.io API key

**Methods:**

**`email_finder(domain: str, first_name: str, last_name: str) -> dict`**
- Performs: Finds most likely email address for person at domain using name pattern matching
- Returns: {"data": {"email": str, "score": int, ...}} with confidence score 0-100

### Custom: `Tavily`
**Location:** `prospecting/api/tavily.py`
**Type:** One-way

**Config Section:** `TAVILY_API_KEY`
- `TAVILY_API_KEY: str` - Tavily API key

**Methods:**

**`search(query: str, max_retries: int = 5, initial_backoff: float = 1.0, backoff_factor: float = 2.0, jitter: float = 0.1) -> list[dict]`**
- Performs: Web search with exponential backoff retry mechanism
- Returns: List of search result dicts with title, url, content, score

### Custom: `SendGrid`
**Location:** `prospecting/api/sengrid.py`
**Type:** One-way

**Config Section:** `SENDGRID_API_KEY`
- `SENDGRID_API_KEY: str` - SendGrid API key

**Methods:**

**`send_email(outreach_message: OutreachMessage, from_email: str = "cole@qurrent.ai", from_name: str = "Cole Salquist", bcc_emails: list[str] = ["48618838@bcc.hubspot.com"], is_demo_record: bool = True) -> bool`**
- Performs: Sends HTML email via SendGrid; overrides recipient to alex@qurrent.ai if is_demo_record=True; appends email signature from cole_email_signature.html; adds BCC recipients
- Returns: True if status code 200/201/202, False otherwise

### Custom: `GoogleDriveClient`
**Location:** `prospecting/api/gdrive_utils.py`
**Type:** One-way

**Config Section:** `AE_SERVICE_ACCOUNT_JSON` (environment variable)
- `AE_SERVICE_ACCOUNT_JSON: JSON string` - Service account credentials JSON (loaded from GCP Secret Manager by load_secrets.py)

**Methods:**

**`list_files_in_folder(folder_id: str) -> List[Dict]`**
- Performs: Lists all Google Docs in specified folder (filters mimeType = 'application/vnd.google-apps.document')
- Returns: List of file metadata dicts with id, name, mimeType, size, modifiedTime, createdTime

**`download_file_content(file_id: str) -> str`**
- Performs: Exports Google Doc as plain text (text/plain mime type)
- Returns: Document content as UTF-8 string

### Prebuilt: External APIs (No Qurrent Integration)

**Exa API**
- Used directly via `exa_py.Exa` client
- Required Config: `EXA_API_KEY: str`
- Methods:
  - `exa.request(f"/websets/v0/websets/{webset_id}", method="GET", params={"expand": ["items"]})` - Fetches webset items with enrichments
  - `ResearchClient(exa).create_task(instructions, model="exa-research", output_schema)` - Creates research task
  - `research_client.get_task(task_id)` - Polls for task completion and retrieves research results

**SendGrid Webhook**
- Endpoint: `/sendgrid-event` (POST)
- Receives: JSON payload or array of event objects with fields: event (type), email (recipient), timestamp, etc.
- Triggers: `SendGridWebhookEvent` added to ingress queue for processing

## Utils

**`MetricsTracker` (class)**
**Location:** `prospecting/metrics.py`
- Purpose: Tracks email engagement metrics per workflow and recipient to avoid duplicate logging
- Implementation: Stores JSON files per workflow instance with nested structure: workflow_id → email → {open_count, delivered_count, bounce_count, events: {open: [timestamps], delivered: [timestamps], bounce: [timestamps]}}; uses atomic writes via temp file + rename; supports thread-safe operations with RLock
- Dependencies: Standard library (json, os, tempfile, threading, pathlib)

**Key Methods:**
- `initialize_metrics(workflow_instance_id: UUID, recipient_emails: list)` - Creates or updates metrics file with email recipients
- `should_log_event(workflow_instance_id: UUID, email: str, event_type: str) -> bool` - Returns True if event not yet logged (delivered/bounce logged once, open can repeat)
- `record_event(workflow_instance_id: UUID, email: str, event_type: str) -> bool` - Increments count and appends timestamp to events list
- `find_workflow_for_email(email: str) -> Optional[str]` - Searches all metrics files to find workflow instance ID for given email

**`load_secrets.py`**
**Location:** `load_secrets.py` (root)
- Purpose: Loads service account JSON from GCP Secret Manager and sets as environment variable
- Implementation: Uses `google.cloud.secretmanager` to fetch secret by name, parses JSON, and sets `AE_SERVICE_ACCOUNT_JSON` environment variable for GoogleDriveClient
- Dependencies: `google-cloud-secret-manager==2.20.0`

**Test Data Loaders/Dumpers**
**Location:** `prospecting/tests.py`
- Purpose: Support simulated test runs by loading/saving intermediate data (research prospects, CRM updates, drafted outreach)
- Implementation: JSON serialization/deserialization with automatic directory creation; supports TargetPersona and OutreachMessage model conversion
- Dependencies: Standard library (json, os)

**Key Functions:**
- `load_research_prospects()` - Returns List[Tuple[event_summary, List[TargetPersona]]]
- `dump_research_prospects(results)` - Writes to `data/tests/research_prospects.json`
- `load_update_crm()` - Returns updated prospects with HubSpot contact IDs
- `dump_update_crm(updated_prospects_with_events)` - Writes to `data/tests/update_crm.json`
- `load_draft_initial_outreach()` - Returns List[Tuple[event_summary, List[OutreachMessage]]]
- `dump_draft_initial_outreach(outreach_results)` - Writes to `data/tests/draft_outreach.json`
- `load_draft_followups()` - Returns List[OutreachMessage]
- `dump_draft_followups(messages)` - Writes to `data/tests/draft_followups.json`

## Directory Structure

```text
ai-account-exec/
    prospecting/
        agents/
            campaign_manager.py
            crm_manager.py
            event_selector.py
            outreach.py
            config/
                campaign_manager.yaml
                crm_manager.yaml
                event_selector.yaml
                outreach.yaml
        api/
            gcp_storage.py
            gdrive_utils.py
            hubspot.py
            hunterio.py
            rss.py
            sengrid.py
            slack_utils.py
            tavily.py
        cole_email_signature.html
        configuration_workflow.py
        metrics.py
        models.py
        tests.py
        workflow.py
    data/
        campaign_definitions.json
        selected_events.json
        email_metrics/
            email_metrics_{workflow_instance_id}.json
        tests/
            research_prospects.json
            update_crm.json
            draft_outreach.json
            draft_followups.json
    docker-compose.yaml
    Dockerfile
    load_secrets.py
    mypy.ini
    pyproject.toml
    README.md
    requirements.txt
    server.py
    startup.sh
```
