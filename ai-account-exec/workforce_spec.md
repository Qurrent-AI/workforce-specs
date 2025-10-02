# Workforce Specification: AI Account Executive

## Background

The AI Account Executive is an automated sales prospecting and outreach system that monitors news events, identifies qualified prospects, manages CRM records, and executes personalized email campaigns with multi-stage follow-ups. The system operates continuously, refreshing campaign definitions daily from Google Drive, monitoring news via Exa websets, conducting deep research to identify decision-makers, enriching CRM data, drafting personalized outreach emails, and tracking engagement metrics through SendGrid webhooks.

The workflow supports multiple concurrent campaigns, each with custom AI logic definitions stored as Google Docs. It runs on a scheduled basis: initial event-based outreach at 8am PT daily, and follow-ups at deterministic random times between 10am-2pm PT to avoid detection patterns. The system integrates with HubSpot CRM, Hunter.io for email enrichment, Tavily and Exa for research, SendGrid for email delivery, and Slack for human oversight.

## Custom Spec Instructions
*FDE-provided instructions for how the workflow specification should be configured*

Create an Examples section that shows two happy-path outreach sequences.

## Examples

This section demonstrates two complete happy-path outreach sequences from event selection through follow-up completion.

### Example 1: Portfolio Company Acquisition Event

**Day 1 (8:00 AM PT) - Event Selection & Initial Outreach**

1. **Event Detected**: "KKR announces acquisition of regional healthcare network MediCare Partners for $2.5B, plans digital transformation initiative"

2. **EventSelector Decision**: Qualifies event based on campaign criteria (private equity activity, healthcare sector, digital transformation mention)

3. **Research Phase**: Exa Research API identifies 3 target personas:
   - Sarah Chen, VP of Digital Strategy at KKR (NYC)
   - Michael Torres, Chief Technology Officer at MediCare Partners (Boston)
   - Jennifer Liu, Managing Director at KKR's Healthcare Vertical (SF)

4. **CRM Update**: CRMManager agent:
   - Searches for "KKR" → finds existing company record
   - Updates KKR company description to mention MediCare acquisition
   - Creates new company record for "MediCare Partners" with parent association to KKR
   - Creates contact records for all 3 personas, associates with respective companies

5. **Outreach Selection & Drafting**: Outreach agent:
   - Filters: Excludes Sarah Chen (already contacted per HubSpot phase property)
   - Enriches: Uses Hunter.io to find Michael Torres's email (confidence: 87%)
   - Searches web: Finds recent interview with Jennifer Liu about healthcare tech investments
   - Drafts 2 personalized emails referencing the acquisition and each persona's role

6. **Email Delivery**:
   - Sends emails via SendGrid with BCC to HubSpot
   - Updates HubSpot contacts: sets phase=1, next_outreach_date=(today + 3 days)
   - Initializes metrics tracking for recipients

7. **Slack Notification**: Posts summary to channel with event reasoning and outreach details

**Day 4 (11:23 AM PT) - First Follow-up**

8. **Follow-up Trigger**: Deterministic scheduler (hash of campaign ID + date) triggers at 11:23 AM PT

9. **Contact Query**: HubSpot returns Michael Torres and Jennifer Liu (next_outreach_date within today's window)

10. **Reply Check**: Retrieves recent emails for both contacts
    - Michael Torres: No incoming emails detected
    - Jennifer Liu: Incoming email found yesterday → removes from queue, updates phase="", sends Slack notification

11. **Follow-up Drafting** (Michael only): Outreach agent:
    - Searches web for recent MediCare news (finds post-acquisition announcement)
    - Drafts short follow-up referencing original email and new development
    - Uses exact same subject line (no "Re:" prefix)

12. **Follow-up Delivery**:
    - Sends via SendGrid
    - Updates HubSpot: phase=2, next_outreach_date=(today + 5 days)

**Day 9 (10:45 AM PT) - Second Follow-up**

13. **Contact Query**: Returns Michael Torres (no reply detected)

14. **Follow-up Drafting**: Even shorter message, references previous two touchpoints

15. **Delivery**: Updates phase=3, next_outreach_date=(today + 7 days)

**Day 16 (1:12 PM PT) - Final Follow-up**

16. **Contact Query**: Returns Michael Torres

17. **Final Follow-up**: Last attempt message, acknowledges no response

18. **Delivery**: Updates phase=4, next_outreach_date="" (sequence complete)

**Engagement Tracking Throughout**:
- SendGrid webhook fires on email open (Day 4, 11:25 AM) → MetricsTracker logs to Supervisor API
- Delivered event logged once per email
- Open events logged unlimited times

### Example 2: Funding Round Announcement

**Day 1 (8:00 AM PT) - Event Selection & Initial Outreach**

1. **Event Detected**: "AI startup DataFlow secures $50M Series B led by Andreessen Horowitz, announces enterprise data platform launch"

2. **EventSelector Decision**: Qualifies event (growth-stage funding, AI/data sector, product launch timing)

3. **Research Phase**: Identifies 2 target personas:
   - Alex Kumar, CEO & Co-founder at DataFlow (San Francisco)
   - Rachel Martinez, CTO at DataFlow (San Francisco)

4. **CRM Update**: CRMManager agent:
   - Searches "DataFlow" → no existing record found
   - Creates company record for "DataFlow" with funding event in description
   - Searches "Andreessen Horowitz" → finds existing investor record
   - Creates company association (DataFlow as portfolio company of a16z)
   - Creates contact records for both personas

5. **Outreach Selection & Drafting**: Outreach agent:
   - Evaluates both contacts: Selects Rachel Martinez (CTO more relevant for technical platform discussion)
   - Email already available from research (found on company website)
   - Searches web: Finds Rachel's recent podcast interview about data infrastructure challenges
   - Drafts personalized email connecting Qurrent's workflow automation to DataFlow's platform needs

6. **Email Delivery**: Sends to Rachel, updates HubSpot (phase=1, next_date=Day 4)

**Day 4 (12:34 PM PT) - First Follow-up**

7. **Follow-up Check**: Rachel Martinez queued for follow-up

8. **Reply Detection**: No incoming emails detected

9. **Follow-up Drafting**: Short message, references original email and podcast discussion

10. **Delivery**: Updates phase=2, next_date=Day 9

**Day 6 (2:15 PM) - Reply Received**

11. **Engagement Detection**: HubSpot receives incoming email from Rachel (BCC forwarding)

**Day 9 (10:18 AM PT) - Follow-up Trigger (Skipped)**

12. **Reply Check**: Detects incoming email from Day 6

13. **Queue Removal**:
    - Updates HubSpot: phase="", next_date="" (clears follow-up sequence)
    - Logs reply metric to Supervisor API
    - Sends Slack notification: "Removing Rachel Martinez from follow-up queue because they have responded to outreach"

14. **Sequence Complete**: No further automated outreach to this contact

## Path Audit

### Decision Ledger

- **Campaign Configuration Refresh (Daily at 7am PT)**
  - Inputs: Google Drive folder containing campaign definition documents
  - Outputs: List of Campaign objects with parsed AI logic definitions
  - Decision logic: For each Google Doc in the folder, check last modified timestamp against stored version. If new or modified, parse the document using CampaignManager agent to extract structured logic definitions (compelling event criteria, target company profile, target personas, outreach selection logic, email guidelines). If human clarification is needed, request updates via Slack and wait for human to edit document, then re-fetch and parse.
  - Logic location: Orchestration code in `server.py::configure_campaigns()` and `configuration_workflow.py::get_campaigns()`, with parsing logic in `CampaignManager` agent prompt

- **Event Selection from Webset (Daily at 8am PT per campaign)**
  - Inputs: Exa webset ID (from campaign logic), webset items with summaries, past selection history (last 30 days)
  - Outputs: List of event summary strings selected for prospecting
  - Decision logic: EventSelector agent evaluates webset items against compelling event criteria and target company criteria (both from campaign AI logic), deduplicates against past 30 days of selections, and returns qualified event summaries with reasoning
  - Logic location: External prompt in campaign definition document, injected into EventSelector agent's system prompt via variable substitution

- **Prospect Research per Event**
  - Inputs: Event summary string, target personas logic from campaign
  - Outputs: List of TargetPersona objects (name, title, company, location, email if found, LinkedIn URL, relevance explanation)
  - Decision logic: Use Exa Research API with instructions combining event summary and target personas logic to identify individuals matching persona criteria associated with the event. Retry up to 3 times on failure. If all retries fail, skip event.
  - Logic location: External prompt (target personas logic) from campaign document, combined with event summary in workflow code and passed to Exa Research API

- **CRM Record Management per Event**
  - Inputs: Event summary, list of TargetPersona objects from research
  - Outputs: Updated TargetPersona list with HubSpot contact IDs populated
  - Decision logic: CRMManager agent receives prospects and event summary, searches for matching company records by keyword, creates/updates company records with event mention in description, infers parent-portfolio relationships if detectable from event, creates/updates contact records, and associates contacts with companies. Agent works iteratively with multiple action rounds (search, then create/update). Updates prospects list with HubSpot contact IDs.
  - Logic location: Internal prompt in CRMManager agent config (crm_manager.yaml)

- **Outreach Target Selection and Email Drafting per Event**
  - Inputs: Event summary, list of TargetPersona objects with HubSpot IDs and past email activity stats, targeting criteria from campaign, email guidelines from campaign
  - Outputs: List of OutreachMessage objects (HubSpot contact ID, recipient email, subject, body)
  - Decision logic: Outreach agent evaluates prospects against targeting criteria (external logic from campaign), filters out individuals already contacted (check outreach phase in HubSpot), searches web up to 3 times for additional context if helpful, enriches missing email addresses using Hunter.io (only if confidence >50%), and drafts personalized emails per email guidelines (external logic from campaign). Agent uses rerun pattern: first turn for research actions, subsequent turn for drafting.
  - Logic location: External prompts (targeting criteria and email guidelines) from campaign document, injected into Outreach agent's system prompt

- **Email Delivery and CRM Update**
  - Inputs: OutreachMessage object, demo record flag
  - Outputs: Email sent status, HubSpot contact updated with email content and next outreach date
  - Decision logic: Check if contact is demo record. If demo, send to test address (alex@qurrent.ai) instead of actual recipient. Send via SendGrid with BCC to HubSpot. If send succeeds, update HubSpot contact with subject, body, event trigger, outreach phase (set to 1), and next outreach date (3 days from today at midnight PT as epoch ms). Initialize metrics tracking for recipient email.
  - Logic location: Internal code in workflow.py::send_initial_outreach()

- **Follow-up Qualification Check (Daily at deterministic time 10am-2pm PT per campaign)**
  - Inputs: HubSpot contacts with account_exec_next_outreach_date within today's PT window
  - Outputs: List of contacts requiring follow-up, or contact removed from queue
  - Decision logic: Query HubSpot for contacts where next outreach date falls within today. For each contact, check recent email history for incoming emails. If incoming email exists, log reply metric, clear outreach phase and next date in HubSpot, notify Slack, and skip follow-up. Otherwise, proceed to draft follow-up.
  - Logic location: Internal code in workflow.py::send_followup() and hubspot.py::get_contacts_requiring_follow_up()

- **Follow-up Email Drafting**
  - Inputs: HubSpot contact details (ID, name, email, company, last subject, last body, trigger, current phase)
  - Outputs: OutreachMessage for follow-up or None if no outreach drafted
  - Decision logic: Outreach agent receives contact details and current phase number. Agent can search web for additional context. Draft follow-up that references prior email but is distinct. Must use exact same subject line and email address (no "Re:" prefix). If drafting fails, notify Slack and return None.
  - Logic location: External prompts (targeting criteria and email guidelines) from campaign document apply, with follow-up-specific instructions in workflow code passed to Outreach agent

- **Follow-up Delivery and Next Phase Scheduling**
  - Inputs: OutreachMessage, contact details including current phase
  - Outputs: Email sent, HubSpot updated with next phase and date
  - Decision logic: Send follow-up via SendGrid (with demo record check). Calculate next outreach date based on phase: phase 1→3 days, phase 2→5 days, phase 3→7 days, phase 4+→no further follow-ups (clear date). Update HubSpot contact with new subject, body, incremented phase, and next date.
  - Logic location: Internal code in workflow.py::send_followup() with follow-up delay mapping (FOLLOW_UP_DELAY_DAYS)

- **Engagement Metrics Tracking (Continuous via webhook)**
  - Inputs: SendGrid webhook events (open, delivered, bounce) with recipient email and event type
  - Outputs: Metric logged to Qurrent Supervisor API, local tracking updated
  - Decision logic: Parse webhook payload for event type and recipient email. Find workflow instance ID by searching metrics files for email. Check if event should be logged (delivered/bounce: only once; open: unlimited). If yes, post metric to Supervisor API, record event locally with timestamp.
  - Logic location: Internal code in server.py::handle_sendgrid_event() with deduplication logic in metrics.py::MetricsTracker

## High Level Architecture

**High Level Architecture Components:**

- **Phases**:
  - Phase 1: Campaign Configuration - Parse Google Drive documents to extract AI logic definitions
  - Phase 2: Event Selection - Evaluate webset items against campaign criteria to identify qualified events
  - Phase 3: Prospect Research - Identify target individuals associated with each event using Exa Research API
  - Phase 4: CRM Management - Create/update company and contact records in HubSpot with event context
  - Phase 5: Initial Outreach - Select targets, enrich emails, draft personalized messages, send and track
  - Phase 6: Follow-up Management - Monitor due dates, check for replies, draft and send follow-ups with increasing delays

- **Decision Points**:
  - Campaign document modified? → Re-parse with CampaignManager agent
  - Event qualifies per campaign criteria? → EventSelector agent decides
  - Research API fails? → Retry up to 3 times, then skip event
  - Company exists in CRM? → CRMManager agent searches and creates/updates accordingly
  - Target has email? → Enrich via Hunter.io if missing and confidence >50%
  - Contact already responded? → Remove from follow-up queue
  - Follow-up phase reached limit? → Clear next date and stop sequence

- **User Touchpoints**:
  - Campaign definition editing in Google Drive (human edits trigger re-parsing)
  - Slack notifications for campaign updates, event selections, errors, and reply detections
  - Slack command `/configure-campaigns` to force campaign refresh
  - Human can provide clarifications when CampaignManager agent requests via Slack

## Data & Formats

### Referenced Documents Inventory

#### Input Data

- **Google Drive Campaign Definitions**
  - Format: Google Docs (exported as plain text)
  - Source: Google Drive folder (ID: 1GZoagbXw4sMYPLQ0cz7s2Q88lTwrbxZV)
  - Intended Use: CampaignManager agent parses to extract structured AI logic definitions (compelling event, target company, target personas, outreach selection, email guidelines)

- **Exa Webset Items**
  - Format: JSON objects with enrichments array containing summary strings
  - Source: Exa API webset endpoint with expand=items
  - Intended Use: EventSelector agent evaluates summaries to select qualified events

- **HubSpot Contact/Company Records**
  - Format: JSON responses from HubSpot CRM API
  - Source: HubSpot API queries (search, get, batch read)
  - Intended Use: CRMManager reads/writes records; Outreach agent reads past activity; follow-up logic reads due dates and phases

- **SendGrid Webhook Events**
  - Format: JSON array or single object with event type, email, timestamp
  - Source: SendGrid webhook POST to /sendgrid-event
  - Intended Use: Metrics tracking for engagement (open, delivered, bounce)

### Example Output Artifacts

- **Event Selection Reasoning**
  - Type: Slack message
  - Format: Plain text with event summaries in bullet list
  - Recipients: Configured Slack channel
  - Contents: EventSelector agent's reasoning for selections and list of chosen event summaries

- **Initial Outreach Email**
  - Type: Email via SendGrid
  - Format: HTML with plain text fallback, includes email signature
  - Recipients: Target prospects (or test address for demo records)
  - Contents: Personalized subject and body referencing event and prospect's role, sender signature, BCC to HubSpot

- **Follow-up Email**
  - Type: Email via SendGrid
  - Format: HTML with plain text fallback, includes email signature
  - Recipients: Prospects in follow-up queue
  - Contents: Short follow-up referencing prior email, same subject line, sender signature

- **CRM Update Summary**
  - Type: Slack message and console output
  - Format: Plain text summary
  - Recipients: Slack channel and Qurrent console
  - Contents: Which companies/contacts were created/updated, parent relationships established

- **Metrics Data Files**
  - Type: Local JSON files
  - Format: Nested JSON with workflow → email → event counts and timestamps
  - Recipients: Internal storage (data/email_metrics/)
  - Contents: Tracking for open_count, delivered_count, bounce_count per email per workflow

## Integrations

**Real Integrations:**
- **Exa (exa-py)**: Fetches webset items and conducts deep prospect research via Research API with structured output schemas
- **HubSpot CRM**: Creates/updates companies and contacts, associates records, queries follow-up dates, retrieves email history
- **Hunter.io**: Finds and verifies email addresses for prospects by name and company domain
- **Tavily**: Web search for additional context during outreach drafting (up to 3 searches per agent invocation)
- **SendGrid**: Sends outreach and follow-up emails with HTML formatting and signature, tracks engagement via webhooks
- **Google Drive**: Reads campaign definition documents from shared folder using service account authentication
- **Slack**: Sends notifications for campaign updates, event selections, errors, and receives commands for manual refresh
- **Qurrent Supervisor API**: Logs engagement metrics (open, delivered, bounce) for dashboard visibility

## Technical Highlights

### Complex Logic Demonstrated

- **Dynamic Prompt Injection**: Campaign-specific AI logic (compelling event criteria, target personas, email guidelines) is stored in Google Drive, parsed by CampaignManager agent, and injected into EventSelector, CRMManager, and Outreach agents via message_thread variable substitution
- **Multi-Campaign Scheduling**: Each campaign runs on independent schedules (8am for events, deterministic random 10am-2pm for follow-ups based on campaign ID hash), managed via asyncio tasks spawned per campaign
- **Parallel Agent Execution**: Research, CRM updates, and outreach drafting all execute in parallel across multiple events using `spawn_task` and `asyncio.gather` for performance
- **Rerun Pattern for LLM Callables**: Agents use `@llmcallable(rerun_agent=True)` decorator to trigger model re-invocation after action execution, enabling iterative workflows (e.g., CRMManager searches first, then creates records based on results)
- **Deterministic Follow-up Windows**: Follow-up times are deterministically random (10am-2pm PT) based on SHA256 hash of campaign ID + date to avoid pattern detection while remaining reproducible
- **Demo/Production Record Separation**: HubSpot records tagged with `is_demo_record=YES` in development mode; emails to demo records redirected to test address; updates restricted to demo records only
- **Race Condition Prevention**: HubSpot client uses asyncio locks per company name and contact name to prevent duplicate record creation during parallel agent execution
- **Webhook-Driven Metrics**: SendGrid events processed asynchronously via ingress queue, deduplicated locally (delivered/bounce once, open unlimited), and posted to external metrics API

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
- If uncertain, uses llmcallables to fetch updated document or send Slack message to request human clarification
- Loops until human confirms updates, then provides final structured logic
- Must respond with JSON containing either empty logic_definition + actions, or complete logic_definition + no actions
- Context: Accumulates over multiple turns when clarification needed

**Instance Attributes:**
- `slack_bot: Slack` - For sending clarification requests to human
- `channel_id: str` - Slack channel for notifications
- `google_drive_client: GoogleDriveClient` - For fetching latest document content
- `file_id: str` - Google Drive file ID of current campaign document being parsed

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
- Receives numbered list of event summaries and past 30 days of selections
- Must respond with reasoning (qualitative, no indices, detailed enough for reader without access to descriptions) and array of selected indices
- Reasoning should refer to "events" not "items"
- Context: Single-turn evaluation
- JSON Response: Ex. `{"reasoning": "<explanation>", "selections": [0, 3, 7]}`

**Instance Attributes:**
- `exa_webset: Dict` - Webset object from Exa API containing items with enrichments
- `today_date: str` - Current date in YYYY-MM-DD format (America/Los_Angeles)

**Create Parameters:**
- `yaml_config_path: str` - Path to event_selector.yaml config
- `workflow_instance_id: UUID` - Workflow instance for tracking
- `compelling_event: str` - Campaign's compelling event criteria (injected into prompt)
- `target_company: str` - Campaign's target company criteria (injected into prompt)
- `exa_webset: Dict` - Webset data from Exa API

#### Direct Actions

**`select_events() -> Tuple[str, List[str]]`**
- Purpose: Parse webset enrichments, append to thread with past selections, invoke agent, extract selected summaries, persist selections to disk
- Message Thread modification:
  - Appends user message with formatted event summaries (numbered with separators)
  - Appends user message with recent past selections (list of indices from last 30 days)
- Util usage:
  - Reads/writes `data/selected_events.json` for persistence (date → list of selected summary indices)
- Returns: Tuple of (reasoning string, list of selected event summary strings)
- Side Effects: Updates selected_events.json with today's selections merged with existing data

### `CRMManager`
**Pattern:** Task Agent
**Purpose:** Create/update HubSpot company and contact records based on prospect research results, inferring parent-child relationships from event context
**LLM:** gpt-5, standard mode, temp=default, timeout=300s

**Prompt Strategy:**
- Receives event summary and prospect list (JSON) via user message appended by workflow
- Instructed to keyword search companies first, then create/update records, add event mention to descriptions, infer parent-portfolio relationships
- Explicitly told to run actions in parallel when efficient, work iteratively (search first, then act on results)
- Must return JSON with reasoning, actions array, and summary of actions taken after completion
- Context: Accumulates over multiple rerun turns
- JSON Response: Ex. `{"reasoning": "<explanation>", "actions": [{"name": "keyword_search_companies", "args": {"keyword": "kkr"}}], "summary": "<detailed summary>"}`

**Instance Attributes:**
- `hubspot: HubSpot` - HubSpot integration client
- `prospects: List[TargetPersona]` - List of prospect objects to process (mutated as contacts are created with IDs)

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
  - Calls `hubspot.keyword_search_companies(keyword)` which uses CONTAINS_TOKEN operator
- Returns: JSON string of search results or error message
- Error Handling: try/except returns formatted error string

**`add_company_record(company_name: str, company_description: str, parent_company_id: Optional[str] = None) -> str`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Docstring Args: `company_name (str), company_description (str), parent_company_id (Optional[str])`
- Purpose: Create company record in HubSpot and optionally associate with parent company
- Integration usage:
  - Calls `hubspot.create_company(company_name, company_description)` to create record
  - If parent_company_id provided, calls `hubspot.associate_parent_company(parent_company_id, company_id)`
- Returns: Success message with company ID or error string
- Error Handling: try/except returns formatted error string

**`update_company_record(company_id: str, company_description: Optional[str] = None, parent_company_id: Optional[str] = None) -> str`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Docstring Args: `company_id (str), company_description (Optional[str]), parent_company_id (Optional[str])`
- Purpose: Update existing company record with new description or parent association
- Integration usage:
  - Calls `hubspot.update_company(company_id, properties)` with description if provided
  - If parent_company_id provided, calls `hubspot.associate_parent_company(parent_company_id, company_id)`
- Returns: Success message or error string
- Error Handling: try/except returns formatted error string

**`add_contact_record(first_name: str, last_name: str, company_id: str, job_title: str, email: Optional[str] = None, linkedin_url: Optional[str] = None) -> str`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Docstring Args: `first_name (str), last_name (str), company_id (str), job_title (str), email (Optional[str]), linkedin_url (Optional[str])`
- Purpose: Create contact record in HubSpot, associate with company, and update prospects list with contact ID
- Integration usage:
  - Calls `hubspot.create_or_update_contact(first_name, last_name, company_id, job_title, email, linkedin_url)`
- Returns: Success message with contact ID or error string
- Side Effects: Mutates `self.prospects` list by calling `persona.update_hubspot_contact_id(contact_id)` for matching prospects
- Error Handling: try/except returns formatted error string

### `Outreach`
**Pattern:** Task Agent
**Purpose:** Select target individuals for outreach, enrich missing emails, draft personalized initial outreach or follow-up messages referencing events and prospect context
**LLM:** gpt-5, standard mode, temp=default, timeout=300s

**Prompt Strategy:**
- System prompt contains targeting_criteria and writing_guidelines from campaign AI logic via variable substitution
- Instructed to search web up to max_search_attempts (3) for additional context
- Email enrichment workflow: identify targets first, then search for missing emails only if needed and confidence >50%
- Must not target individuals already contacted (check account_exec_outreach_phase in past_email_activity)
- Workflow discipline: When researching, respond with actions only (no outreach); when drafting, respond with outreach only (no actions)
- Context: Accumulates over rerun turns (research → draft)
- JSON Response: Ex. `{"explanation": "<reasoning>", "actions": [{"name": "search_web", "args": {"query": "..."}}], "outreach": [{"hubspot_contact_id": "...", "to": "...", "subject": "...", "body": "..."}]}`

**Instance Attributes:**
- `slack_bot: Slack` - For error notifications
- `channel_id: str` - Slack channel for notifications
- `tavily: Tavily` - Web search integration
- `hubspot: HubSpot` - For retrieving past email activity
- `hunter_io: HunterIO` - For email enrichment
- `targeting_criteria: str` - Campaign-specific targeting logic (injected into prompt)
- `email_guidelines_definition: str` - Campaign-specific email writing guidelines (injected into prompt)
- `search_attempts: int` - Counter for web searches (max 3)

**Create Parameters:**
- `yaml_config_path: str` - Path to outreach.yaml config
- `workflow_instance_id: UUID` - Workflow instance for tracking
- `slack_bot: Slack` - Initialized Slack integration
- `channel_id: str` - Target Slack channel ID
- `tavily: Tavily` - Initialized Tavily client
- `hubspot: HubSpot` - Initialized HubSpot client
- `hunter_io: HunterIO` - Initialized Hunter.io client
- `targeting_criteria: str` - From campaign AI logic
- `email_guidelines_definition: str` - From campaign AI logic

#### LLM Callables

**`search_web(query: str) -> str | list[dict]`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Docstring Args: `query (str): The search query to execute`
- Purpose: Search the web for additional context about prospect/company/event (max 3 attempts)
- Integration usage:
  - Calls `tavily.search(query)` which returns list of search results
- Returns: Search results or "You've reached the maximum number of search attempts" if limit exceeded
- Side Effects: Increments `self.search_attempts` counter
- Error Handling: Handled by Tavily client with exponential backoff

**`get_past_email_activity(hubspot_contact_id: str) -> str`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Docstring Args: `hubspot_contact_id (str): The ID of the contact`
- Purpose: Retrieve recent email communication history for contact to inform outreach
- Integration usage:
  - Calls `hubspot.get_recent_contact_emails(hubspot_contact_id)` which returns last 5 emails with direction, subject, body preview
- Returns: JSON string of past emails
- Error Handling: None specified (errors propagate)

**`search_for_contact_info(first_name: str, last_name: str, company_domain_name: str) -> str`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Docstring Args: `first_name (str), last_name (str), company_domain_name (str)`
- Purpose: Find email address for prospect using Hunter.io email finder
- Integration usage:
  - If SLACK_CHANNEL_OVERRIDE env var set (test mode), returns test email alex@qurrent.ai
  - Otherwise calls `hunter_io.email_finder(company_domain_name, first_name, last_name)`
- Returns: JSON string with email and confidence score, or error message
- Error Handling: try/except returns "Failed to search for contact info" on exception

#### Direct Actions

**`draft_message(event_summary: str, target_personas: List[TargetPersona]) -> List[OutreachMessage]`**
- Purpose: Orchestrate initial outreach drafting for event-based prospects
- Message Thread modification:
  - Appends user message with event summary and JSON list of target individuals (includes past_email_activity)
- Integration usage:
  - Calls `hubspot.get_contact_email_exchange_stats(contact_id)` for each persona to get past activity
- Subagent usage:
  - Invokes self via `await self()` to get agent response
  - Calls `await self.get_rerun_responses(timeout=300)` to wait for actions to complete and get final response
- Returns: List of OutreachMessage objects or empty list if no valid prospects
- Side Effects: Resets `search_attempts` to 0; sends Slack notification if no outreach drafted
- Error Handling: Filters out prospects without valid hubspot_contact_id before drafting

**`draft_follow_up(hubspot_contact: Dict) -> Optional[OutreachMessage]`**
- Purpose: Draft follow-up email for contact in follow-up queue
- Message Thread modification:
  - Appends user message with contact details string (ID, name, email, company, last subject/body, trigger, phase)
  - Message includes phase-specific instructions (short follow-up, reference last email, use exact same subject)
- Integration usage: None (contact details already provided by caller)
- Subagent usage:
  - Invokes self via `await self()` to get agent response
  - Calls `await self.get_rerun_responses(timeout=300)` to wait for actions to complete and get final response
- Returns: OutreachMessage object for first message in response, or None if drafting failed
- Side Effects: Sends Slack notification if no outreach drafted
- Error Handling: Returns None if response contains no outreach messages

## Configuration

```yaml
CUSTOMER_KEY_DEV: [required - get from Qurrent]

LLM_KEYS:
  ANTHROPIC_API_KEY: [required for Claude models]
  OPENAI_API_KEY: [required for GPT models]

HUBSPOT:
  HUBSPOT_API_KEY: [required - private app token with CRM scopes]
  HUBSPOT_PORTAL_ID: [optional - portal/account ID]

HUNTER_IO:
  HUNTER_IO_API_KEY: [required - for email enrichment]

SENDGRID:
  SENDGRID_API_KEY: [required - for sending emails]

TAVILY:
  TAVILY_API_KEY: [required - for web search during outreach]

EXA:
  EXA_API_KEY: [required - for webset fetching and research API]

SLACK:
  SLACK_BOT_TOKEN: [required - bot token with channels:write, chat:write]
  SLACK_SIGNING_SECRET: [required - for webhook verification]
  SLACK_CHANNEL_ID: [required - channel for notifications]

GOOGLE_DRIVE:
  AE_SERVICE_ACCOUNT_JSON: [required - service account JSON as string, set by load_secrets.py from Secret Manager]
  # Alternative: GOOGLE_APPLICATION_CREDENTIALS env var with path to JSON file

ENVIRONMENT:
  ENVIRONMENT: [development | production - controls demo record behavior]
  SLACK_CHANNEL_OVERRIDE: [optional - override target channel, enables test mode]
  START_IMMEDIATELY: [optional - "true" to run campaigns on startup instead of waiting for schedule]
```

## Utils

**`MetricsTracker` (metrics.py)**
- Purpose: Track email engagement metrics per workflow and email, avoid duplicate event logging, support webhook lookups
- Implementation: Thread-safe singleton with RLock, stores data in JSON files per workflow (data/email_metrics/email_metrics_{workflow_id}.json), atomic writes via temp file + rename
- Key Methods:
  - `initialize_metrics(workflow_instance_id, recipient_emails)`: Create/update JSON with email → counters/events mapping
  - `should_log_event(workflow_instance_id, email, event_type)`: Return True if event not yet logged (delivered/bounce once only, open unlimited)
  - `record_event(workflow_instance_id, email, event_type)`: Increment counter, append timestamp, save atomically
  - `find_workflow_for_email(email)`: Search all metrics files to find workflow for given email (for webhooks)
- Dependencies: `threading`, `tempfile`, `json`, `pathlib`

**`GoogleDriveClient` (api/gdrive_utils.py)**
- Purpose: Fetch campaign definition documents from Google Drive using service account
- Implementation: Async wrapper around google-api-python-client, uses asyncio.to_thread for sync API calls
- Key Methods:
  - `list_files_in_folder(folder_id)`: Return list of Google Docs in folder with metadata (id, name, modifiedTime)
  - `download_file_content(file_id)`: Export Google Doc as plain text and return content string
- Dependencies: `google-auth==2.x`, `google-api-python-client`, `google-auth-httplib2`

**Timezone Helpers (models.py)**
- Purpose: Centralized timezone handling for Pacific Time conversions and storage formatting
- Key Functions:
  - `now_pacific()`: Return current datetime in America/Los_Angeles timezone
  - `as_pacific(dt)`: Convert datetime to Pacific timezone
  - `format_pacific(dt)`: Format datetime as "YYYY-MM-DD HH:MM:SS" in Pacific
  - `parse_pacific(timestamp_str)`: Parse storage format string to Pacific datetime
- Dependencies: `zoneinfo`, `datetime`

## Dependencies

- `qurrent` - Qurrent OS SDK (Workflow, Agent, Slack, events, WebServer, LLM decorators)
- `exa-py==1.14.16` - Exa API client for websets and research
- `tavily-python` - Tavily web search API
- `sendgrid` - SendGrid email delivery API
- `aiohttp` - Async HTTP client for HubSpot and external APIs
- `httpx` - Async HTTP client for metrics posting
- `requests` - Sync HTTP client for Hunter.io
- `google-auth` - Google service account authentication
- `google-api-python-client` - Google Drive API client
- `google-cloud-storage` - GCP storage (for blob store integration)
- `pydantic>=2.5` - Data validation and models
- `loguru` - Structured logging
- `uvloop` - High-performance event loop
- `feedparser` - RSS parsing (unused in current implementation)
- `trafilatura` - Web content extraction (unused in current implementation)
- `pandas` - Data manipulation (unused in current implementation)
- `opentelemetry-*` - Observability and tracing

## Integrations

### Prebuilt: `qurrent.Slack`
- Required Config Section: `SLACK`
- Required Keys:
  - `SLACK_BOT_TOKEN: str` - Bot user OAuth token with channels:write, chat:write scopes
  - `SLACK_SIGNING_SECRET: str` - Signing secret for webhook verification
  - `SLACK_CHANNEL_ID: str` - Default channel ID for notifications
- Methods Used:
  - `send_message(channel_id, message)`: Send markdown-formatted message to channel
  - `link(workflow_instance_id, channel_id)`: Associate workflow with channel for command routing
  - `unlink(channel_id)`: Remove workflow-channel association
- Commands: `/configure-campaigns` triggers immediate campaign refresh

### Custom: `HubSpot`
**Location:** `prospecting/api/hubspot.py`
**Type:** Two-way (queries and creates/updates records)

**Config Section:** `HUBSPOT`
- `HUBSPOT_API_KEY: str` - Private app token with CRM scopes (contacts, companies, associations, emails)
- `HUBSPOT_PORTAL_ID: str (optional)` - Portal/account ID

**Methods:**

**`keyword_search_companies(keyword: str, limit: int = 100) -> List[dict]`**
- Performs: Fuzzy search for companies using CONTAINS_TOKEN operator on name and domain
- Behavior: Returns up to limit companies with id, name, domain, description, parent_id
- Returns: List of company dicts

**`create_company(company_name: str, company_description: str) -> dict`**
- Performs: Create new company record with demo flag if in development mode
- Behavior: Checks for existing company by name first (with lock), creates if not exists, handles 409 race condition
- Returns: Company object with id

**`update_company(company_id: str, properties: Dict[str, str]) -> dict`**
- Performs: Update company properties (protected by demo record check in development)
- Behavior: Fetches company to check is_demo_record flag, only updates if demo or in production
- Returns: Updated company object

**`associate_parent_company(parent_company_id: str, child_company_id: str) -> dict`**
- Performs: Create parent-child association between companies using batch associations API
- Behavior: Handles 409 if association already exists
- Returns: Association response or {"status": "already_exists"}

**`create_or_update_contact(first_name: str, last_name: str, company_id: str, job_title: str, email: Optional[str], linkedin_url: Optional[str]) -> dict`**
- Performs: Create or update contact by name, populate missing fields only, associate with company
- Behavior: Searches by first+last name with lock, creates if not exists, handles email conflicts (409/400) by retrying without email, checks company association before creating it
- Returns: Contact object with id

**`update_contact(contact_id: str, properties: Dict[str, Any]) -> dict`**
- Performs: Update contact properties (protected by demo record check)
- Behavior: Fetches contact to verify demo flag, pre-checks email uniqueness, retries without email on 400/409
- Returns: Updated contact object or empty dict if skipped

**`is_contact_demo_record(contact_id: str) -> bool`**
- Performs: Check if contact has is_demo_record=YES property
- Behavior: Returns False on 404 or missing property
- Returns: Boolean

**`get_recent_contact_emails(contact_id: str, limit: int = 5, start_timestamp: Optional[int], end_timestamp: Optional[int]) -> List[Dict]`**
- Performs: Retrieve recent email engagements for contact with cleaned body previews
- Behavior: Fetches associated email objects via CRM v3, sorts by sent_at descending, filters by timestamp window
- Returns: List of email dicts with id, subject, direction, from, to, sent_at, body_preview

**`get_contact_email_exchange_stats(contact_id: str, start_timestamp: Optional[int], end_timestamp: Optional[int]) -> Dict[str, Union[int, Optional[str]]]`**
- Performs: Return total email count, last exchange timestamp, and current outreach phase
- Behavior: Calls get_contact_email_summary and fetches account_exec_outreach_phase property
- Returns: Dict with total_exchanged (int), last_exchange_at (str or None), account_exec_outreach_phase (str or None)

**`get_contacts_requiring_follow_up() -> List[dict]`**
- Performs: Query contacts where account_exec_next_outreach_date falls within today's PT window (00:00-24:00 as UTC epoch ms)
- Behavior: Calculates Pacific date boundaries as UTC timestamps, searches with GTE/LT filters, fetches associated company name for each
- Returns: List of contact dicts with hubspot_contact_id, email, account_exec_email_subject, account_exec_email_body, account_exec_outreach_phase, account_exec_outreach_trigger, first_name, last_name, company_name

**`delete_demo_records() -> None`**
- Performs: Delete all contacts and companies where is_demo_record=YES (dev cleanup utility)
- Behavior: Searches for demo records in batches of 100, deletes each, handles 404 gracefully
- Returns: None (logs counts)

### Custom: `HunterIO`
**Location:** `prospecting/api/hunterio.py`
**Type:** One-way (queries only)

**Config Section:** `HUNTER_IO`
- `HUNTER_IO_API_KEY: str` - Hunter.io API key

**Methods:**

**`email_finder(domain: str, first_name: str, last_name: str) -> dict`**
- Performs: Find most likely email address for person at company
- Sample Data: None (real API calls)
- Behavior: Returns email, confidence score (0-100), sources
- Returns: Dict with data.email, data.score

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
**Type:** One-way (sends emails, receives webhooks separately)

**Config Section:** `SENDGRID`
- `SENDGRID_API_KEY: str` - SendGrid API key

**Methods:**

**`send_email(outreach_message: OutreachMessage, from_email: str = "cole@qurrent.ai", from_name: str = "Cole Salquist", bcc_emails: list[str] = ["48618838@bcc.hubspot.com"], is_demo_record: bool = True) -> bool`**
- Performs: Send HTML email with signature appended
- Behavior:
  - If is_demo_record, overrides recipient to alex@qurrent.ai
  - Appends cole_email_signature.html to body
  - Adds BCC recipients (includes HubSpot logging address)
  - Sends via SendGrid API
- Returns: True if status 200/201/202, False otherwise

**Webhook Handler:**
- `SendGridWebhook.start(config, host="0.0.0.0", port=8000, webhook_endpoint="/sendgrid-event")`: Starts WebServer with POST endpoint
- `handle_sendgrid_event(event, config)`: Processes webhook events (open, delivered, bounce) by finding workflow via MetricsTracker, checking if should log, posting to Supervisor API, recording locally
- Events:
  - `SendGridWebhookEvent`: Custom event type with workflow_instance_id=-1 (placeholder), data=payload
  - Triggered: Webhook posts JSON array or single object to /sendgrid-event
  - Fields: event (type), email (recipient), timestamp, and various metadata
  - Handling: Async via ingress queue, uses httpx for metrics API posting, uses asyncio.to_thread for file IO

### Custom: `GoogleDriveClient`
**Location:** `prospecting/api/gdrive_utils.py`
**Type:** One-way (reads files)

**Config Section:** `GOOGLE_DRIVE`
- `AE_SERVICE_ACCOUNT_JSON: str (env var)` - Service account JSON as string (preferred, set by load_secrets.py)
- `GOOGLE_APPLICATION_CREDENTIALS: str (env var, alternative)` - Path to service account JSON file

**Methods:**

**`list_files_in_folder(folder_id: str) -> List[Dict]`**
- Performs: List Google Docs in folder with metadata
- Behavior: Queries Drive API with mimeType filter for Google Docs, returns id, name, mimeType, size, modifiedTime, createdTime
- Returns: List of file metadata dicts

**`download_file_content(file_id: str) -> str`**
- Performs: Export Google Doc as plain text
- Behavior: Uses export_media with mimeType="text/plain", downloads in chunks
- Returns: Plain text content as string

### External: Exa API
**Location:** `exa-py` library imported in workflow.py
**Type:** One-way (queries websets and research API)

**Config Section:** `EXA`
- `EXA_API_KEY: str` - Exa API key

**Methods Used:**

**`exa.request(f"/websets/v0/websets/{webset_id}", method="GET", params={"expand": ["items"]}) -> dict`**
- Performs: Fetch webset with items and enrichments
- Behavior: Returns webset object with items array, each item has enrichments array with summary strings
- Returns: Dict with items (list of dicts with enrichments)

**`ResearchClient(exa).create_task(instructions: str, model: "exa-research", output_schema: dict) -> Task`**
- Performs: Initiate deep research task with structured output
- Behavior: Creates async research task, polls with get_task(task.id) until status="completed", extracts data.research_results
- Returns: Task object with id, status, data (contains research_results array matching output schema)
