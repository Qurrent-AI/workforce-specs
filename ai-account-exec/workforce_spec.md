# Workforce Specification: AI Account Executive

**Contributors:** Alex Reents, Alex McConville, Andrey Tretyak

## Overview

The AI Account Executive is an automated prospecting and outreach system that monitors news events, identifies relevant prospects, and executes personalized email campaigns with multi-stage follow-up sequences. The system operates autonomously on a daily schedule, processing campaigns defined in Google Drive documents.

The workforce consists of two primary workflows:

1. **Campaign Configuration Workflow**: Synchronizes with Google Drive to parse campaign logic definitions. This workflow reads campaign documents that specify targeting criteria, compelling event definitions, target personas, outreach selection logic, and email writing guidelines. The CampaignManager agent extracts these structured definitions from natural language documents.

2. **Prospect Research Workflow**: Executes event-based prospecting for each configured campaign. This workflow monitors Exa websets for relevant news events, uses the EventSelector agent to qualify events against campaign criteria, leverages Exa's research API to identify target individuals, updates HubSpot CRM via the CRMManager agent, and sends personalized outreach emails through the Outreach agent with automated follow-up sequences.

The system runs continuously with daily scheduled execution: campaign configurations refresh at 7am PT, initial outreach runs at 8am PT, and follow-ups execute at deterministic randomized times between 10am-2pm PT. All emails are personalized based on news events, enriched with web research, and tracked through HubSpot CRM and SendGrid metrics.

## Custom Instructions
*FDE-provided instructions for how this particular workforce specification should be configured*
<!--
[Provide custom instructions here around how to understand and document this particular workforce]
-->

## Decision Audit

Documents the possible paths of workflow execution through the lens of decisions the workforce makes.

### Campaign Configuration Decisions

- [1] **Campaign Document Change Detection**
    - Inputs: Google Drive folder containing campaign definition documents with modification timestamps
    - Outputs: List of new or modified campaign documents requiring processing
    - Decision logic: Compare document modification timestamps (Pacific time) against stored timestamps. Identify new documents without stored records and modified documents with timestamp differences.
    - Logic location: internal code

- [2] **Campaign Logic Extraction**
    - Inputs: Campaign document content (natural language text from Google Doc)
    - Outputs: Structured logic definition with fields: compelling_event_logic, target_company_logic, target_personas_logic, outreach_selection_logic, email_guidelines_logic, exa_webset_id
    - Decision logic: Parse unstructured campaign document into structured sections by matching content to predefined categories. The agent sorts content into the appropriate logic definition fields without adding or removing information, except for obvious spelling/instruction mismatches. If sections are unclear or missing, the agent requests clarification from human campaign managers via Slack, instructing them to update the document directly rather than responding via message.
    - Logic location: internal prompt (CampaignManager agent)

- [3] **Campaign Logic Clarification**
    - Inputs: Ambiguous or incomplete campaign document sections
    - Outputs: Slack message requesting human clarification with specific questions about unclear sections
    - Decision logic: When campaign definition sections cannot be confidently classified or are missing required fields, send clarification request to Slack channel. Wait for human confirmation that document has been updated, then re-fetch and re-parse the document.
    - Logic location: internal prompt (CampaignManager agent)

- [4] **Timeout Handling for Campaign Configuration**
    - Inputs: Campaign configuration workflow runtime exceeding 15 minutes
    - Outputs: Final logic definition extracted from document state at timeout, or notification of incomplete configuration
    - Decision logic: If interactive clarification loop exceeds 15 minutes, fetch the current document content and extract logic definition based on current state. Notify via Slack whether logic definition was successfully captured or remains incomplete.
    - Logic location: internal code

### Event Selection Decisions

- [5] **Qualifying Event Selection**
    - Inputs: Exa webset items with enriched summaries, campaign compelling_event_logic, campaign target_company_logic, past event selections from last 30 days
    - Outputs: List of selected event indices with reasoning explanation
    - Decision logic: Evaluate each news event against compelling_event_logic criteria (what constitutes a marketing-qualified signal) and target_company_logic criteria (ideal customer profile characteristics). Filter out events matching recent selections from past 30 days to prevent duplicates. Select events meeting campaign criteria that have not been previously used for outreach.
    - Logic location: internal prompt (EventSelector agent)

### Prospect Research Decisions

- [6] **Target Persona Identification**
    - Inputs: Selected event summary, campaign target_personas_logic
    - Outputs: List of identified individuals with: first_name, last_name, job_title, company_name, company_domain_name, location, email (if available), linkedin_url (if available), relevance_explanation
    - Decision logic: Use Exa's research API with structured output schema to identify individuals matching target_personas_logic criteria (roles, responsibilities, characteristics of decision-makers) associated with the news event. Extract contact details and explain relevance of each identified person to the event and campaign criteria.
    - Logic location: external prompt (Exa research API)

### CRM Management Decisions

- [7] **Company Record Matching**
    - Inputs: Company name from prospect research, existing HubSpot company records
    - Outputs: Existing company record ID or decision to create new record
    - Decision logic: Perform keyword search in HubSpot using tokenized matching on company name and domain. Use substring tokens likely to appear in company name or domain (e.g., brand acronyms). If matching company found, return existing ID. If no match found, create new company record. Handle parent company relationships by searching for parent companies first to retrieve IDs for association.
    - Logic location: internal prompt (CRMManager agent)

- [8] **Company Record Update**
    - Inputs: News event summary, company record ID, existing company description
    - Outputs: Updated company record with event mention in description field
    - Decision logic: When company record exists, update description to include mention of the news event. If parent/portfolio company relationship can be inferred from news event, create or update parent-child association. Only update demo records in non-production environment.
    - Logic location: internal prompt (CRMManager agent)

- [9] **Contact Record Creation/Update**
    - Inputs: Prospect details (first_name, last_name, job_title, email, linkedin_url), company_id
    - Outputs: Contact record ID (new or existing)
    - Decision logic: Search for contact by first and last name. If contact exists, update only missing fields (job_title, email, linkedin_url) with new values. If contact doesn't exist, create new record with all provided details. Associate contact with company. Handle email conflicts by skipping email update if another contact already has that email.
    - Logic location: internal prompt (CRMManager agent)

- [10] **Parallel Action Execution Strategy**
    - Inputs: Multiple CRM operations required (searches, creates, updates)
    - Outputs: Sequence of action batches (searches first, then creates/updates after observing results)
    - Decision logic: Execute dependent operations iteratively. First run search actions in parallel, observe results, then run create/update actions in parallel based on search results. Retry failed actions at least once on system errors. Handle rate limiting by reducing parallelization on subsequent attempts.
    - Logic location: internal prompt (CRMManager agent)

### Outreach Selection Decisions

- [11] **Target Individual Selection**
    - Inputs: List of prospects with hubspot_contact_id, email addresses, past_email_activity, campaign outreach_selection_logic
    - Outputs: Subset of prospects selected for outreach
    - Decision logic: Filter prospects to only those with valid hubspot_contact_id. Apply outreach_selection_logic criteria (scoring, ranking, timing factors) to prioritize targets. Exclude individuals already in active outreach phase. Exclude prospects without email addresses or with very low confidence email matches (below 50%).
    - Logic location: internal prompt (Outreach agent)

- [12] **Email Address Enrichment**
    - Inputs: Prospect first_name, last_name, company_domain_name, existing email field
    - Outputs: Email address with confidence score, or decision not to contact
    - Decision logic: If email address not provided in prospect data, use Hunter.io email finder to search for professional email. If search returns confidence score below 50% or no email found, exclude prospect from outreach. Only enrich after selecting individual for outreach to avoid expensive unnecessary operations. Never enrich same individual more than once.
    - Logic location: internal prompt (Outreach agent)

- [13] **Pre-Outreach Research**
    - Inputs: Selected target individual, company, news event
    - Outputs: Enrichment research results from web search (up to 3 searches)
    - Decision logic: Optionally search web for additional information about lead, company, or event to improve personalization. Maximum 3 web searches allowed per outreach message. Research phase must complete before drafting message - respond only with search actions, not outreach content, during research phase.
    - Logic location: internal prompt (Outreach agent)

### Email Drafting Decisions

- [14] **Initial Email Composition**
    - Inputs: Event summary, target individual details, research findings, campaign email_guidelines_logic
    - Outputs: Email with subject line and body, or decision not to send
    - Decision logic: Draft personalized email referencing the specific news event and its relevance to the individual. Address recipient by name in body. Follow email_guidelines_logic for tone, structure, messaging strategy, and personalization approaches. Include explanation of reasoning behind outreach. If unable to draft appropriate message given available information and guidelines, provide explanation and skip outreach to this individual.
    - Logic location: internal prompt (Outreach agent)

- [15] **Follow-up Email Composition**
    - Inputs: Contact details from HubSpot (name, email, company), last email subject and body, original outreach trigger, current follow-up phase number (1, 2, or 3)
    - Outputs: Follow-up email with same subject line and recipient email as previous message
    - Decision logic: Draft short follow-up email referencing the last email while making this one distinct. Use exact same subject line without adding "Re:" or other modifications. For phase 1-3, reference previous message and maintain continuity. For follow-up composition, optionally enrich with web search about contact/company and check past email activity before drafting.
    - Logic location: internal prompt (Outreach agent)

- [16] **Response Detection**
    - Inputs: Contact HubSpot ID, past email history with direction indicators
    - Outputs: Decision to continue follow-up sequence or remove from queue
    - Decision logic: Check recent emails for contact. If any email has direction INCOMING_EMAIL (reply from contact), remove contact from follow-up queue by clearing outreach_phase and next_outreach_date fields. Increment reply metric. Notify via Slack. If no reply detected, continue with follow-up.
    - Logic location: internal code

### Follow-up Scheduling Decisions

- [17] **Follow-up Phase Progression**
    - Inputs: Current outreach phase (0=initial, 1=first follow-up, 2=second follow-up, 3=third follow-up)
    - Outputs: Next outreach date (milliseconds since epoch UTC) or empty string if sequence complete
    - Decision logic: Apply fixed delay schedule after each phase: 3 days after initial (phase 0→1), 5 days after first follow-up (phase 1→2), 7 days after second follow-up (phase 2→3). After third follow-up (phase 3), set next_outreach_date to empty string to end sequence. All dates calculated as midnight UTC of target date in Pacific timezone.
    - Logic location: internal code

- [18] **Daily Follow-up Contact Selection**
    - Inputs: Current date (Pacific timezone), HubSpot contacts with account_exec_next_outreach_date field
    - Outputs: List of contacts requiring follow-up today
    - Decision logic: Query HubSpot for contacts where account_exec_next_outreach_date falls within today's Pacific timezone window (00:00:00 to 23:59:59 as epoch milliseconds UTC). Retrieve contact details including email, name, company, last outreach subject/body, outreach trigger, and current phase.
    - Logic location: internal code

### Email Sending Decisions

- [19] **Demo Record Override**
    - Inputs: HubSpot contact ID, is_demo_record property value, ENVIRONMENT setting
    - Outputs: Final recipient email address for sending
    - Decision logic: Check contact's is_demo_record property. In non-production environment or for demo records, override recipient email to alex@qurrent.ai. In production for non-demo records, use actual contact email. All demo record emails redirected for testing safety.
    - Logic location: internal code

- [20] **Email Delivery Execution**
    - Inputs: Outreach message (to, subject, body), demo record status
    - Outputs: Email sent via SendGrid with BCC to HubSpot, or failure notification
    - Decision logic: Send email through SendGrid API using configured sender (cole@qurrent.ai). Append email signature HTML to body. Include BCC to HubSpot (48618838@bcc.hubspot.com) for activity tracking. If SendGrid returns 200/201/202 status, mark as success. If send fails, log error and skip CRM update for this recipient.
    - Logic location: internal code

- [21] **Post-Send CRM Update**
    - Inputs: HubSpot contact ID, email content (subject, body), event summary, current phase
    - Outputs: Updated contact properties in HubSpot
    - Decision logic: Only update CRM if email was successfully sent. Update contact properties: account_exec_email_subject, account_exec_email_body, account_exec_outreach_trigger (for initial only), account_exec_outreach_phase (increment by 1), account_exec_next_outreach_date (calculated based on new phase).
    - Logic location: internal code

### Metrics and Monitoring Decisions

- [22] **Email Metrics Registration**
    - Inputs: List of recipient emails, workflow_instance_id
    - Outputs: Initialized metrics tracking file for this workflow
    - Decision logic: After sending initial outreach, create or update metrics JSON file mapping workflow_instance_id to per-email counters. Initialize counters (open_count, delivered_count, bounce_count) and event arrays (open, delivered, bounce) to zero/empty for each recipient email.
    - Logic location: internal code

- [23] **SendGrid Event Processing**
    - Inputs: SendGrid webhook event (type: open/delivered/bounce, email, timestamp)
    - Outputs: Metric logged to Supervisor or event skipped
    - Decision logic: Find workflow_instance_id associated with recipient email by searching metrics files. Check if event type already logged for this email (delivered and bounce logged once only, opens can repeat). If not logged, post metric to Supervisor external API and record event in local metrics file. If already logged or workflow not found, skip.
    - Logic location: internal code

### Workflow Scheduling Decisions

- [24] **Daily Campaign Execution Timing**
    - Inputs: Current time (Pacific timezone), campaign configuration
    - Outputs: Wait duration until next scheduled run
    - Decision logic: Initial outreach runs once daily at 8am Pacific. Follow-ups run once daily at deterministic randomized time within 10am-2pm Pacific window (hour and minute determined by hash of campaign_id and date). Campaign configurations refresh at 7am Pacific. Calculate seconds until next scheduled execution time; if time has passed today, calculate for tomorrow.
    - Logic location: internal code

- [25] **Campaign Workflow Spawn**
    - Inputs: Configured campaigns list, scheduled_campaign_ids set
    - Outputs: New campaign workflow tasks spawned or skipped if already scheduled
    - Decision logic: For each campaign returned from configuration refresh, check if campaign_id already in scheduled_campaign_ids set. If not scheduled, spawn daily run task and follow-up task as main tasks. Add campaign_id to set to prevent duplicate scheduling across refreshes.
    - Logic location: internal code

## Data & Formats

### Referenced Documents Inventory and Input Data

- **Campaign Definition Documents**
    - Format: Google Doc (plain text export)
    - Source: Google Drive folder (ID: 1GZoagbXw4sMYPLQ0cz7s2Q88lTwrbxZV)
    - Intended Use: Parsed by CampaignConfiguration workflow to extract logic definitions for campaign execution

- **Exa Webset Items**
    - Format: JSON with enrichments array containing summary results
    - Source: Exa API websets endpoint
    - Intended Use: Source of news events for EventSelector agent to qualify against campaign criteria

- **HubSpot CRM Records**
    - Format: JSON objects with properties fields
    - Source: HubSpot CRM API (companies, contacts, associations)
    - Intended Use: CRMManager agent creates/updates company and contact records; Outreach agent retrieves contact details and email history

- **Campaign Definitions Storage**
    - Format: JSON
    - Source: Local file (data/campaign_definitions.json)
    - Intended Use: Persists parsed campaign logic definitions with modification timestamps

- **Event Selection History**
    - Format: JSON (date -> list of event indices)
    - Source: Local file (data/selected_events.json)
    - Intended Use: Tracks past 30 days of selected events to prevent duplicate outreach

- **Email Metrics Tracking**
    - Format: JSON (workflow_id -> {email -> {counters, events}})
    - Source: Local files (data/email_metrics/email_metrics_{workflow_id}.json)
    - Intended Use: Maps recipient emails to workflow instances and tracks SendGrid events (open, delivered, bounce)

### Example Output Artifacts

- **Initial Outreach Email**
    - Type: Email
    - Format: HTML (with plain text body + HTML signature)
    - Recipients: Target prospects identified through research
    - Contents: Personalized subject line, body referencing specific news event and recipient's relevance, professional signature

- **Follow-up Email**
    - Type: Email
    - Format: HTML (with plain text body + HTML signature)
    - Recipients: Contacts in active outreach sequence without replies
    - Contents: Same subject line as previous email, short body referencing last message with distinct approach, professional signature

- **Slack Notifications**
    - Type: Message
    - Format: Markdown text
    - Recipients: Configured Slack channel
    - Contents: Event selection reasoning, outreach drafted summaries, campaign configuration updates, error notifications

- **HubSpot CRM Updates**
    - Type: Record updates
    - Format: HubSpot property key-value pairs
    - Recipients: HubSpot portal
    - Contents: Contact properties (account_exec_email_subject, account_exec_email_body, account_exec_outreach_trigger, account_exec_outreach_phase, account_exec_next_outreach_date); Company properties (description with event mentions, parent associations)

- **Supervisor Console Output**
    - Type: Observable output
    - Format: Text/JSON
    - Recipients: Qurrent Supervisor platform
    - Contents: Business-friendly summaries of workflow steps (webset item counts, prospect research results, CRM update summaries, outreach drafted counts)

## Integration Summary

**Integrations:**
- **Exa**: AI-powered web research and monitoring. Provides websets for news event sourcing and research API for prospect identification with structured output
- **HubSpot CRM**: Customer relationship management. Stores company and contact records, tracks associations, maintains email history, queries follow-up schedules
- **Hunter.io**: Email finder and verification. Discovers professional email addresses for prospects given name and company domain
- **Tavily**: Web search API. Enriches outreach with additional information about prospects, companies, and events
- **SendGrid**: Email delivery service. Sends outreach emails with HTML formatting, BCC tracking, and webhook events
- **Google Drive**: Document storage. Hosts campaign definition documents with modification tracking
- **Google Cloud Storage**: File storage. Stores campaign and metrics data in environment-specific buckets (account_exec_development, account_exec_production)
- **Slack**: Team communication. Receives notifications, campaign updates, clarification requests, and supports /configure-campaigns command

## Directory Structure
ai-account-exec/
├── prospecting/
│   ├── agents/
│   │   ├── config/
│   │   │   ├── campaign_manager.yaml
│   │   │   ├── crm_manager.yaml
│   │   │   ├── event_selector.yaml
│   │   │   └── outreach.yaml
│   │   ├── campaign_manager.py
│   │   ├── crm_manager.py
│   │   ├── event_selector.py
│   │   └── outreach.py
│   ├── api/
│   │   ├── gcp_storage.py
│   │   ├── gdrive_utils.py
│   │   ├── hubspot.py
│   │   ├── hunterio.py
│   │   ├── sengrid.py
│   │   ├── slack_utils.py
│   │   └── tavily.py
│   ├── configuration_workflow.py
│   ├── metrics.py
│   ├── models.py
│   ├── tests.py
│   └── workflow.py
├── data/
│   ├── campaign_definitions.json
│   ├── selected_events.json
│   └── email_metrics/
└── server.py

## Agents

**Note:** Document Console Agents first (what business stakeholders see), then Technical Agents (implementation details).

### Console Agents

#### `researcher`
**Type:** Console Agent (method with `@console_agent` decorator)
**Purpose:** Analyzes articles to find compelling events that seed targeted email outreach
**Docstring:** "Research agent responsible for analzing articles to find compelling events to seed targeted email outreach"

**Observable Tasks:**

**`get_webset_events(webset_id: str)`**
- `@observable` decorator
- Docstring: "Fetch recent webset items and return event summaries built from enrichments"
- Purpose: Retrieves news events from Exa webset and filters them against campaign criteria
- Technical Agent Calls: Calls `EventSelector.select_events()` to evaluate events against compelling_event_logic and target_company_logic
- Integration Calls: Calls `exa.request()` to fetch webset items with enrichments
- Observability Output: `save_to_console(type='observable_output', content=f"Webset '{webset_id}' returned {len(summaries)} recent items\n{summary_str}\nReasoning: {reasoning}")`
- Returns: List[str] of selected event summaries

**`research_prospects(news_events: List[str])`**
- `@observable` decorator
- Docstring: "Research prospects for qualified events in parallel with error handling"
- Purpose: Identifies target individuals associated with each qualifying news event
- Technical Agent Calls: None (uses Exa research API directly)
- Integration Calls: Calls `research_event()` method which uses Exa ResearchClient to identify target personas
- Observability Output: `save_to_console(type='observable_output', content=f"Research completed for {len(successful_research_results)} events:\n{details}")`
- Returns: List[Tuple[str, List[TargetPersona]]] mapping event summaries to identified prospects

#### `record_manager`
**Type:** Console Agent (method with `@console_agent` decorator)
**Purpose:** Manages the CRM by creating/updating company and contact records
**Docstring:** "Agent responsible for managing the CRM"

**Observable Tasks:**

**`update_crm(prospects_with_events: List[Tuple[str, List[TargetPersona]]])`**
- `@observable` decorator
- Docstring: "Updating the CRM with the prospect research"
- Purpose: Creates or updates HubSpot company and contact records for all prospects, processes events in parallel
- Technical Agent Calls: Creates `CRMManager` instance for each event and calls it with run_actions_in_parallel=True, then awaits rerun responses
- Integration Calls: Via CRMManager agent's @llmcallables to HubSpot API
- Observability Output: `save_to_console(type='observable_output', content=observable_output)` containing summaries of CRM updates per event
- Returns: List[Tuple[str, List[TargetPersona]]] with updated prospects containing hubspot_contact_id fields

#### `outreach_manager`
**Type:** Console Agent (method with `@console_agent` decorator)
**Purpose:** Drafts and sends personalized outreach emails
**Docstring:** "Agent responsible for drafting outreach emails"

**Observable Tasks:**

**`draft_outreach(prospects_with_events: List[Tuple[str, List[TargetPersona]]])`**
- `@observable` decorator
- Docstring: "Draft initial outreach for all events"
- Purpose: Generates personalized initial outreach emails for prospects, executes in parallel per event
- Technical Agent Calls: Calls `send_initial_outreach()` which creates Outreach agent instance and calls `draft_message()`
- Integration Calls: Via Outreach agent to Tavily (web search), Hunter.io (email enrichment), HubSpot (email history), SendGrid (send email)
- Observability Output: `save_to_console(type='observable_output', content=f"Outreach drafted for {len(normalized_results)} events:\n{details}")` and individual message outputs
- Returns: None (side effects: emails sent, CRM updated, metrics initialized)

**`draft_followups()`**
- `@observable` decorator
- Docstring: "Send follow-up emails to prospects"
- Purpose: Drafts and sends follow-up emails to contacts in active outreach sequences
- Technical Agent Calls: Calls `send_followup()` which creates Outreach agent instance and calls `draft_follow_up()`
- Integration Calls: Via Outreach agent to HubSpot (get follow-up contacts, email history), SendGrid (send email)
- Observability Output: `save_to_console(type='observable_output', content=follow_up_summary)` listing sent follow-ups or "No follow-ups sent"
- Returns: None (side effects: follow-up emails sent, CRM updated)

### Technical Agents

#### `CampaignManager`
**Type:** Technical Agent (extends `Agent` class)
**Pattern:** Task
**Purpose:** Parses campaign definition documents into structured logic definitions through iterative clarification with human campaign managers
**LLM:** claude-sonnet-4-20250514, standard mode, temp=0 (default), timeout=300s

**Prompt Strategy:**
- Parse campaign definition into 6 structured logic sections: compelling_event_logic, target_company_logic, target_personas_logic, outreach_selection_logic, email_guidelines_logic, and exa_webset_id
- Primary responsibility is sorting unstructured content into structured sections without adding/removing content (except for obvious spelling/instruction fixes)
- Request clarification from human campaign managers via Slack when uncertain, instructing them to update document directly
- Context: accumulates across clarification iterations
- JSON Response: `{"actions": [] or [{"name": "fetch_campaign_logic"|"send_slack_message", "args": {...}}], "logic_definition": {} or {structured fields}}`

**Instance Attributes:**
- `slack_bot: Slack` - For sending clarification messages
- `channel_id: str` - Slack channel ID for notifications
- `google_drive_client: GoogleDriveClient` - For fetching campaign documents
- `file_id: str` - Current campaign document ID being processed

**Create Parameters:**
- `yaml_config_path: str` - Path to agent YAML config ("./prospecting/agents/config/campaign_manager.yaml")
- `workflow_instance_id: UUID` - From workflow
- `slack_bot: Slack` - Passed from workflow
- `channel_id: str` - From workflow config["SLACK_CHANNEL_ID"]
- `google_drive_client: GoogleDriveClient` - Created in workflow

#### LLM Callables

**`fetch_campaign_logic() -> str`**
- `@llmcallable(rerun_agent=True)`
- Docstring Args: None
- Purpose: Retrieves the latest content of the campaign logic document from Google Drive
- Integration usage:
    - Calls `google_drive_client.download_file_content(file_id)` to fetch document text
- Returns: Plain text content of campaign document
- Error Handling: Raises ValueError if file_id not set

**`send_slack_message(message: str) -> str`**
- `@llmcallable(rerun_agent=True)`
- Docstring Args: `message (str): The message to send`
- Purpose: Sends clarification requests to Slack channel
- Integration usage:
    - Calls `slack_bot.send_message(channel_id, message)` to post message
- Returns: "The message was sent successfully"

#### `CRMManager`
**Type:** Technical Agent (extends `Agent` class)
**Pattern:** Orchestrator
**Purpose:** Manages HubSpot CRM updates for prospect research results, creating/updating company and contact records with parallel action execution
**LLM:** gpt-5, standard mode, temp=0 (default), timeout=300s

**Prompt Strategy:**
- Process event-based prospect research results (news event summary + list of prospects)
- Search for existing companies by keyword (tokenized matching), create if not found, update descriptions with event mentions
- Infer and create parent/portfolio company relationships from news events
- Create or update contact records with prospect details and associate with companies
- Execute actions in parallel when efficient; work iteratively when actions depend on prior results
- Handle rate limiting by reducing parallelization and retry system errors at least once
- Context: accumulates
- JSON Response: `{"reasoning": "<explanation>", "actions": [{"name": "keyword_search_companies"|"add_company_record"|"update_company_record"|"add_contact_record", "args": {...}}], "summary": "<summary of actions taken>"}`

**Instance Attributes:**
- `hubspot: HubSpot` - HubSpot API client for CRM operations
- `prospects: List[TargetPersona]` - Current prospects being processed (updated with hubspot_contact_id)

**Create Parameters:**
- `yaml_config_path: str` - Path to agent YAML config ("./prospecting/agents/config/crm_manager.yaml")
- `workflow_instance_id: UUID` - From workflow
- `hubspot: HubSpot` - Passed from workflow
- `prospects: List[TargetPersona]` - Passed from workflow

#### LLM Callables

**`keyword_search_companies(keyword: str) -> str`**
- `@llmcallable(rerun_agent=True)`
- Docstring Args: `keyword (str): Keyword token to search for (e.g., brand acronym like 'kkr')`
- Purpose: Fuzzy search companies by keyword across name and domain
- Integration usage:
    - Calls `hubspot.keyword_search_companies(keyword)` which uses HubSpot CONTAINS_TOKEN operator
- Returns: JSON string of search results with company_id, company_name, domain, company_description, parent_company_id
- Error Handling: try/except returns exception message string

**`add_company_record(company_name: str, company_description: str, parent_company_id: Optional[str] = None) -> str`**
- `@llmcallable(rerun_agent=True)`
- Docstring Args: `company_name (str): The name of the company to add`, `company_description (str): The description of the company to add`, `parent_company_id (Optional[str]): The ID of the parent company to add`
- Purpose: Creates new company in CRM and optionally associates with parent company
- Integration usage:
    - Calls `hubspot.create_company(company_name, company_description)` to create record
    - Calls `hubspot.associate_parent_company(parent_company_id, child_company_id)` if parent_company_id provided
- Returns: Success message with company_id
- Error Handling: try/except returns exception message string

**`update_company_record(company_id: str, company_description: Optional[str] = None, parent_company_id: Optional[str] = None) -> str`**
- `@llmcallable(rerun_agent=True)`
- Docstring Args: `company_id (str): The ID of the company to update`, `company_description (Optional[str]): The updated description of the company`, `parent_company_id (Optional[str]): The updated ID of the parent company`
- Purpose: Updates existing company record properties and associations
- Integration usage:
    - Calls `hubspot.update_company(company_id, {"description": company_description})` if description provided
    - Calls `hubspot.associate_parent_company(parent_company_id, company_id)` if parent_company_id provided
- Returns: Success message for company_id
- Error Handling: try/except returns exception message string

**`add_contact_record(first_name: str, last_name: str, company_id: str, job_title: str, email: Optional[str] = None, linkedin_url: Optional[str] = None) -> str`**
- `@llmcallable(rerun_agent=True)`
- Docstring Args: `first_name (str): The first name of the contact to add`, `last_name (str): The last name of the contact to add`, `company_id (str): The ID of the company to add the contact to`, `job_title (str): The job title of the contact to add`, `email (Optional[str]): The email of the contact to add`, `linkedin_url (Optional[str]): The LinkedIn URL of the contact to add`
- Purpose: Creates or updates contact in CRM and updates local prospects list with hubspot_contact_id
- Integration usage:
    - Calls `hubspot.create_or_update_contact(first_name, last_name, company_id, job_title, email, linkedin_url)` which handles search, create/update, and association
- Subagent usage:
    - Iterates through `self.prospects` to find matching persona and call `persona.update_hubspot_contact_id(contact_id)`
- Returns: Success message with contact_id
- Side Effects: Updates matching TargetPersona object's hubspot_contact_id field in self.prospects list
- Error Handling: try/except returns exception message string

#### `EventSelector`
**Type:** Technical Agent (extends `Agent` class)
**Pattern:** Task
**Purpose:** Selects qualifying news events from Exa webset based on campaign criteria while avoiding duplicate selections
**LLM:** gpt-5, standard mode, temp=0 (default), timeout=300s

**Prompt Strategy:**
- Evaluate news events against compelling_event_logic and target_company_logic criteria
- Filter out events selected in past 30 days to prevent duplicates
- Provide brief qualitative reasoning explaining selection without referencing event indices
- Include enough detail in reasoning for reader to understand events (reader doesn't have access to event descriptions)
- Context: resets (single call)
- JSON Response: `{"reasoning": "<explanation>", "selections": [id1, id4, id7, ...]}`

**Instance Attributes:**
- `exa_webset: Dict` - Webset data with items and enrichments
- `today_date: str` - Current date in Pacific timezone (YYYY-MM-DD format)

**Create Parameters:**
- `yaml_config_path: str` - Path to agent YAML config ("./prospecting/agents/config/event_selector.yaml")
- `workflow_instance_id: UUID` - From workflow
- `compelling_event: str` - Campaign compelling_event_logic substituted into system prompt
- `target_company: str` - Campaign target_company_logic substituted into system prompt
- `exa_webset: Dict` - Webset data from Exa API

#### Direct Actions

**`select_events() -> Tuple[str, List[str]]`**
- Purpose: Orchestrates event selection by extracting summaries, retrieving past selections, calling LLM, and persisting selections
- Message Thread modification:
    - Appends user messages with formatted event summaries (numbered with separators) and past selections from last 30 days
- Integration usage:
    - Reads from local file `data/selected_events.json` for past selections (date -> list of event indices)
    - Writes merged selections back to file after LLM response
- Util usage:
    - Uses `_get_prompt()` to format event summaries with numbered separators
    - Uses `_get_past_selections()` to read JSON file
    - Uses `_get_recent_selections()` to filter last 30 days
- Returns: Tuple of (reasoning string, list of selected event summaries)
- Side Effects: Updates data/selected_events.json with today's selections

#### `Outreach`
**Type:** Technical Agent (extends `Agent` class)
**Pattern:** Agentic Search
**Purpose:** Drafts personalized outreach emails by researching leads via web search, enriching with email addresses, and applying campaign-specific guidelines
**LLM:** gpt-5, standard mode, temp=0 (default), timeout=300s

**Prompt Strategy:**
- Select individuals for outreach based on targeting_criteria (campaign outreach_selection_logic)
- Enrich missing email addresses via Hunter.io (max 3 searches), exclude if confidence below 50%
- Optionally search web up to max_search_attempts times (3) for lead/company/event information
- Draft personalized messages following writing_guidelines (campaign email_guidelines_logic), reference event and individual's relevance, address by name
- Two-phase workflow: research phase responds only with actions (search_web, search_for_contact_info, get_past_email_activity), drafting phase responds only with outreach array
- Context: accumulates (for multiple searches/enrichments before drafting)
- JSON Response: `{"explanation": "<reasoning>", "actions": [{"name": "search_web"|"search_for_contact_info"|"get_past_email_activity", "args": {...}}], "outreach": [] or [{"hubspot_contact_id": "id", "to": "email", "subject": "subject", "body": "body"}, ...]}`

**Instance Attributes:**
- `slack_bot: Slack` - For notifications when no outreach drafted
- `channel_id: str` - Slack channel ID for notifications
- `tavily: Tavily` - Web search API client
- `hubspot: HubSpot` - CRM API client for email history
- `hunter_io: HunterIO` - Email finder API client
- `targeting_criteria: str` - Campaign outreach_selection_logic substituted into system prompt
- `email_guidelines_definition: str` - Campaign email_guidelines_logic substituted into system prompt
- `search_attempts: int` - Counter for web searches (max 3, reset per message drafting session)

**Create Parameters:**
- `yaml_config_path: str` - Path to agent YAML config ("./prospecting/agents/config/outreach.yaml")
- `workflow_instance_id: UUID` - From workflow
- `slack_bot: Slack` - Passed from workflow
- `channel_id: str` - From workflow config["SLACK_CHANNEL_ID"]
- `tavily: Tavily` - Passed from workflow
- `hubspot: HubSpot` - Passed from workflow
- `hunter_io: HunterIO` - Passed from workflow
- `targeting_criteria: str` - Campaign outreach_selection_logic
- `email_guidelines_definition: str` - Campaign email_guidelines_logic

#### Direct Actions

**`draft_message(event_summary: str, target_personas: List[TargetPersona]) -> List[OutreachMessage]`**
- Purpose: Orchestrates initial outreach drafting by preparing persona data with past email activity, calling agent with iterative action execution, and returning messages
- Message Thread modification:
    - Appends user message with event summary and JSON array of target individuals (including hubspot_contact_id, past_email_activity stats)
- Integration usage:
    - Calls `hubspot.get_contact_email_exchange_stats()` for each persona to retrieve past_email_activity
    - Calls `slack_bot.send_message()` if no valid prospects or no outreach drafted
- Subagent usage:
    - Calls `self()` to invoke LLM, then `self.get_rerun_responses(timeout=300)` if actions returned
- Returns: List[OutreachMessage] or empty list if no outreach drafted
- Side Effects: Resets search_attempts to 0; filters out prospects without hubspot_contact_id

**`draft_follow_up(hubspot_contact: Dict) -> Optional[OutreachMessage]`**
- Purpose: Orchestrates follow-up email drafting by formatting contact history and calling agent
- Message Thread modification:
    - Appends user message with contact details (ID, name, email, company) and outreach history (last email subject/body, original trigger, phase number)
    - Different prompting for initial vs follow-ups: follow-ups instructed to reference last email with distinct content and use exact same subject line without "Re:"
- Integration usage:
    - Calls `slack_bot.send_message()` if no outreach drafted
- Subagent usage:
    - Calls `self()` to invoke LLM, then `self.get_rerun_responses(timeout=300)` if actions returned
- Returns: OutreachMessage or None if no outreach drafted

#### LLM Callables

**`search_web(query: str) -> str | list[dict]`**
- `@llmcallable(rerun_agent=True)`
- Docstring Args: `query (str): The search query to execute`
- Purpose: Searches web for information to enrich outreach (max 3 attempts tracked by search_attempts counter)
- Integration usage:
    - Calls `tavily.search(query)` which wraps TavilyClient with exponential backoff retry
- Returns: Search results as list of dicts, or warning string if max attempts reached
- Side Effects: Increments self.search_attempts counter

**`get_past_email_activity(hubspot_contact_id: str) -> str`**
- `@llmcallable(rerun_agent=True)`
- Docstring Args: `hubspot_contact_id (str): The ID of the contact to get past email activity for`
- Purpose: Retrieves summary of recent email communication for a contact
- Integration usage:
    - Calls `hubspot.get_recent_contact_emails(hubspot_contact_id)` to fetch recent email objects
- Returns: JSON string of email list with id, subject, direction, from, to, sent_at, body_preview

**`search_for_contact_info(first_name: str, last_name: str, company_domain_name: str) -> str`**
- `@llmcallable(rerun_agent=True)`
- Docstring Args: `first_name (str): The first name of the target persona`, `last_name (str): The last name of the target persona`, `company_domain_name (str): The domain name of the target persona's company`
- Purpose: Finds professional email address using Hunter.io
- Integration usage:
    - Calls `hunter_io.email_finder(company_domain_name, first_name, last_name)` which wraps Hunter.io API
- Returns: JSON string of contact data with email and confidence score, or test email "alex@qurrent.ai" if SLACK_CHANNEL_OVERRIDE env var set, or "Failed to search for contact info" on error
- Error Handling: try/except logs warning and returns failure string

## YAML Configuration
*Credentials used -- provide keys, not values*

CUSTOMER_KEY_DEV

LLM_KEYS:
    ANTHROPIC_API_KEY
    OPENAI_API_KEY

HUBSPOT:
    HUBSPOT_API_KEY
    HUBSPOT_PORTAL_ID (optional)

HUNTER_IO:
    HUNTER_IO_API_KEY

TAVILY:
    TAVILY_API_KEY

SENDGRID:
    SENDGRID_API_KEY

EXA:
    EXA_API_KEY

SLACK:
    SLACK_BOT_TOKEN
    SLACK_APP_TOKEN
    SLACK_CHANNEL_ID

GOOGLE:
    AE_SERVICE_ACCOUNT_JSON (environment variable set by load_secrets.py from Secret Manager)
    GOOGLE_APPLICATION_CREDENTIALS (fallback path to service account JSON file)

ENVIRONMENT:
    ENVIRONMENT: development | production (determines demo record handling and GCP bucket selection)
    SLACK_CHANNEL_OVERRIDE (optional, overrides SLACK_CHANNEL_ID for testing)
    START_IMMEDIATELY: true | false (whether to run campaigns immediately on startup)

## Utils

**`prospecting.metrics.MetricsTracker`**
- Purpose: Thread-safe utility class for tracking email metrics by workflow instance to avoid duplicate logging of SendGrid webhook events
- Implementation: Stores data in JSON files (data/email_metrics/email_metrics_{workflow_id}.json) with per-email counters (open_count, delivered_count, bounce_count) and event timestamp arrays. Uses file locking, atomic writes, and file permission management for docker compatibility.
- Methods: `initialize_metrics(workflow_instance_id, recipient_emails)`, `load_metrics_data(workflow_instance_id)`, `save_metrics_data(workflow_instance_id, metrics_data)`, `should_log_event(workflow_instance_id, email, event_type)`, `record_event(workflow_instance_id, email, event_type)`, `find_workflow_for_email(email)`
- Dependencies: `threading.RLock` for locking, `tempfile` for atomic writes, `pathlib.Path` for file operations

**`prospecting.api.gcp_storage.read_from_gcp(file_name, default) -> Dict[str, Any]`**
- Purpose: Reads JSON data from GCP storage bucket or local file (based on USE_LOCAL flag)
- Implementation: Uses google-cloud-storage client to access bucket named account_exec_{environment}. Creates default content if file doesn't exist.
- Dependencies: `google-cloud-storage`

**`prospecting.api.gcp_storage.write_to_gcp(file_name, content) -> bool`**
- Purpose: Writes JSON data to GCP storage bucket or local file (based on USE_LOCAL flag)
- Implementation: Uploads JSON string to blob at path prospecting/{file_name}
- Dependencies: `google-cloud-storage`

**`prospecting.api.slack_utils.fetch_canvas_content(slack_bot, channel_id, canvas_name, clean_content) -> str`**
- Purpose: Fetches and optionally cleans content from Slack Canvas
- Implementation: Uses Slack files.list API to find canvas by name, then downloads content via private URL. Cleaning converts HTML to markdown (headers, bold, italic, lists).
- Dependencies: `aiohttp` for HTTP requests, `re` for HTML parsing

**`prospecting.api.slack_utils.delete_all_messages(slack_bot, channel_id, delay_seconds) -> int`**
- Purpose: Deletes all messages and threaded replies from a Slack channel
- Implementation: Uses conversations_history and conversations_replies APIs with pagination. Processes messages in batches with optional delay between deletions.
- Dependencies: Slack SDK (via slack_bot.app.client)

**`prospecting.models.as_pacific(dt: datetime) -> datetime`**
- Purpose: Converts datetime to Pacific timezone
- Implementation: Replaces tzinfo with ZoneInfo("America/Los_Angeles") or converts if already timezone-aware
- Dependencies: `zoneinfo.ZoneInfo`

**`prospecting.models.format_pacific(dt: datetime) -> str`**
- Purpose: Formats datetime as Pacific timezone string
- Implementation: Converts to Pacific and formats as "%Y-%m-%d %H:%M:%S"

**`prospecting.models.parse_pacific(timestamp_str: str) -> datetime`**
- Purpose: Parses timestamp string to Pacific datetime
- Implementation: Uses strptime with "%Y-%m-%d %H:%M:%S" format and adds Pacific timezone

## Dependencies
- `tavily-python` - Web search API client
- `exa-py==1.14.16` - AI research and web monitoring API
- `google-auth` - Google authentication for service accounts
- `google-api-python-client` - Google Drive API client
- `google-cloud-storage` - GCP storage for campaign data
- `aiohttp` - Async HTTP client for API calls
- `httpx` - Async HTTP client for metrics posting
- `requests` - Synchronous HTTP client for Hunter.io
- `sendgrid` - Email delivery service SDK
- `pydantic>=2.5` - Data validation and modeling
- `feedparser` - RSS feed parsing (unused in current implementation)
- `lxml_html_clean` - HTML cleaning utilities
- `trafilatura` - Web content extraction (unused in current implementation)
- `requests-html` - HTML parsing (unused in current implementation)
- `opentelemetry-*` - Observability and tracing
- `pandas` - Data manipulation (unused in current implementation)
- `python-docx` - Word document processing (unused in current implementation)

## Integrations

### Prebuilt: `qurrent.Slack`
- Required Config Section: `SLACK`
- Required Keys:
    - `SLACK_BOT_TOKEN: str` - Bot user OAuth token for API access
    - `SLACK_APP_TOKEN: str` - App-level token for socket mode
    - `SLACK_CHANNEL_ID: str` - Default channel for notifications

### Custom: `HubSpot`
**Location:** `prospecting/api/hubspot.py`
**Type:** One-way (outbound only - no webhook ingress)

**Config Section:** `HUBSPOT`
- `HUBSPOT_API_KEY: str` - HubSpot private app API key
- `HUBSPOT_PORTAL_ID: str` - HubSpot portal ID (optional)

**Methods:**

**`keyword_search_companies(keyword: str, limit: int = 100) -> List[dict]`**
- Performs: Fuzzy search for companies using tokenized matching on name and domain fields
- Behavior: Uses HubSpot CONTAINS_TOKEN operator with both name and domain filter groups (OR logic). Returns up to limit companies with id, name, domain, description, parent_company_id
- Returns: List of company dicts

**`create_company(company_name: str, company_description: str) -> dict`**
- Performs: Creates new company record with name and description
- Behavior: Uses lock to prevent race conditions. Searches for existing company first. Sets is_demo_record="YES" in non-production. Handles 409 conflict by retrieving existing company
- Returns: Company object with id

**`update_company(company_id: str, properties: Dict[str, str]) -> dict`**
- Performs: Updates existing company properties
- Behavior: Uses lock for thread safety. Validates is_demo_record property in non-production (only updates demo records). PATCH request to update properties
- Returns: Updated company object

**`associate_parent_company(parent_company_id: str, child_company_id: str) -> dict`**
- Performs: Creates parent-child company association using batch associations API
- Behavior: Uses lock for thread safety. Creates parent_to_child_company association type. Handles 409 conflict as already_exists
- Returns: API response dict or {"status": "already_exists"}

**`create_or_update_contact(first_name: str, last_name: str, company_id: str, job_title: str, email: Optional[str] = None, linkedin_url: Optional[str] = None) -> dict`**
- Performs: Creates new contact or updates existing contact matched by name, then ensures company association
- Behavior: Uses lock per contact name to prevent race conditions. Searches by first+last name. If exists, updates only missing fields (jobtitle, email, hs_linkedin_url). If not exists, creates new contact. Handles email conflicts by retrying without email. Ensures company association (skips if already associated). Sets is_demo_record="YES" in non-production
- Returns: Contact object with id

**`update_contact(contact_id: str, properties: Dict[str, Any]) -> dict`**
- Performs: Updates contact properties for demo records only in non-production
- Behavior: Uses lock for thread safety. Fetches contact to verify is_demo_record property. Pre-checks email uniqueness before update. Retries without email on 400/409 conflicts. Returns existing data if no updatable properties or non-demo record
- Returns: Updated or existing contact object

**`is_contact_demo_record(contact_id: str) -> bool`**
- Performs: Checks if contact is a demo record
- Behavior: Fetches is_demo_record property and returns True if value is "YES"
- Returns: Boolean

**`get_recent_contact_emails(contact_id: str, limit: int = 5, start_timestamp: Optional[int] = None, end_timestamp: Optional[int] = None) -> List[Dict[str, Optional[str]]]`**
- Performs: Retrieves recent email engagement objects for contact
- Behavior: Fetches associated email IDs via associations API, batch reads email objects (100 per batch), filters by timestamp window, sorts by sent_at descending, returns top limit
- Returns: List of email dicts with id, subject, direction, from, to, sent_at, body_preview

**`get_contact_email_exchange_stats(contact_id: str, start_timestamp: Optional[int] = None, end_timestamp: Optional[int] = None) -> Dict[str, Union[int, Optional[str]]]`**
- Performs: Returns total email exchanges, last exchange date, and current outreach phase for contact
- Behavior: Calls get_contact_email_summary for recent emails, fetches account_exec_outreach_phase property from contact record
- Returns: Dict with total_exchanged (int), last_exchange_at (ISO string), account_exec_outreach_phase (string)

**`get_contacts_requiring_follow_up() -> List[dict]`**
- Performs: Queries contacts due for follow-up today using account_exec_next_outreach_date property
- Behavior: Calculates today's Pacific timezone window as UTC epoch milliseconds (00:00:00 to 24:00:00). Searches contacts where account_exec_next_outreach_date falls within window. Retrieves contact properties and associated company name for each result
- Returns: List of contact dicts with hubspot_contact_id, email, account_exec_email_subject, account_exec_email_body, account_exec_next_outreach_date, account_exec_outreach_phase, account_exec_outreach_trigger, first_name, last_name, company_name

**`delete_demo_records() -> None`**
- Performs: Deletes all contacts and companies with is_demo_record="YES"
- Behavior: Uses lock for thread safety. Searches for demo records in batches of 100 with pagination. Deletes each object sequentially. Ignores 404 errors
- Returns: None (logs deleted counts)

### Custom: `HunterIO`
**Location:** `prospecting/api/hunterio.py`
**Type:** One-way (outbound only)

**Config Section:** `HUNTER_IO`
- `HUNTER_IO_API_KEY: str` - Hunter.io API key

**Methods:**

**`email_finder(domain: str, first_name: str, last_name: str) -> dict`**
- Performs: Finds email address given name and company domain
- Behavior: GET request to /v2/email-finder with domain, first_name, last_name params. Returns email and confidence score
- Returns: JSON response dict with data.email and data.score

**`domain_search(domain: str) -> dict`**
- Performs: Finds email addresses related to a domain
- Returns: JSON response with emails for domain

**`email_verifier(email: str) -> dict`**
- Performs: Verifies deliverability of an email address
- Returns: JSON response with verification result

### Custom: `Tavily`
**Location:** `prospecting/api/tavily.py`
**Type:** One-way (outbound only)

**Config Section:** `TAVILY`
- `TAVILY_API_KEY: str` - Tavily API key

**Methods:**

**`search(query: str, max_retries: int = 5, initial_backoff: float = 1.0, backoff_factor: float = 2.0, jitter: float = 0.1) -> list[dict]`**
- Performs: Web search with exponential backoff retry mechanism
- Behavior: Wraps TavilyClient.search() with retry loop. On failure, waits initial_backoff * backoff_factor^retry seconds with random jitter. Raises after max_retries
- Returns: List of search result dicts

### Custom: `SendGrid`
**Location:** `prospecting/api/sengrid.py`
**Type:** Two-way (outbound emails + inbound webhooks)

**Config Section:** `SENDGRID`
- `SENDGRID_API_KEY: str` - SendGrid API key

**Methods:**

**`send_email(outreach_message: OutreachMessage, from_email: str = "cole@qurrent.ai", from_name: str = "Cole Salquist", bcc_emails: list[str] = ["48618838@bcc.hubspot.com"], is_demo_record: bool = True) -> bool`**
- Performs: Sends email via SendGrid API with HTML body and signature
- Behavior: Overrides recipient to "alex@qurrent.ai" if is_demo_record=True. Appends email signature HTML to body. Adds BCC recipients for HubSpot tracking. Checks response status 200/201/202 for success
- Returns: True if sent successfully, False otherwise

**Custom Events:**
- `SendGridWebhookEvent`:
    - Event type: `"SendGridWebhook"`
    - Required: `workflow_instance_id: UUID | int`, `data: dict | list`
    - Triggered by: SendGrid webhook POST to /sendgrid-event endpoint
    - Handled by: `handle_sendgrid_event()` in server.py which processes open/delivered/bounce events, looks up workflow_instance_id by recipient email, checks if event should be logged, posts metric to Supervisor API

### Custom: `GoogleDriveClient`
**Location:** `prospecting/api/gdrive_utils.py`
**Type:** One-way (outbound only - read-only access)

**Config Section:** `GOOGLE`
- `AE_SERVICE_ACCOUNT_JSON: str (env var)` - Service account JSON string loaded from Secret Manager
- `GOOGLE_APPLICATION_CREDENTIALS: str (env var)` - Fallback path to service account JSON file

**Methods:**

**`list_files_in_folder(folder_id: str) -> List[Dict]`**
- Performs: Lists all Google Docs in a Drive folder
- Behavior: Queries with filter 'mimeType = "application/vnd.google-apps.document"'. Returns file metadata with id, name, mimeType, size, modifiedTime, createdTime. Uses supportsAllDrives and includeItemsFromAllDrives for shared drive support
- Returns: List of file metadata dicts

**`download_file_content(file_id: str) -> str`**
- Performs: Downloads Google Doc content as plain text
- Behavior: Exports Google Doc using mimeType "text/plain". Uses MediaIoBaseDownload to stream content. Only supports Google Docs (raises ValueError for other types)
- Returns: Plain text string content

### Prebuilt: Exa (via exa-py SDK)
**Location:** Used via `exa_py.Exa` and `exa_py.research.client.ResearchClient`
**Type:** One-way (outbound only)

**Config Section:** `EXA`
- `EXA_API_KEY: str` - Exa API key

**Usage:**
- **Webset retrieval**: `exa.request(f"/websets/v0/websets/{webset_id}", method="GET", params={"expand": ["items"]})` - Fetches webset with enriched news event summaries
- **Prospect research**: `ResearchClient(exa).create_task(instructions, model="exa-research", output_schema)` - Creates research task with structured output schema. Poll with `get_task(task_id)` until status="completed" and data is available. Returns research_results with prospect details
