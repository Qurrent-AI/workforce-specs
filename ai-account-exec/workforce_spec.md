# Workforce Specification: AI Account Executive

#### Contributors
Alex Reents, Alex McConville, Andrey Tretyak, root, Qurrent Coder, dependabot[bot]

## Overview

The AI Account Executive is an automated sales prospecting and outreach system that monitors news events to identify timely opportunities for personalized B2B engagement. The system operates as two parallel workflows: (1) Campaign Configuration, which parses and stores campaign logic from Google Drive documents, and (2) Prospect Research, which runs daily to discover relevant news events, research prospects, update the CRM, and send personalized outreach emails with automated follow-ups.

The workforce operates autonomously on a scheduled basis. Each morning at 8am Pacific, the system fetches news events from an Exa webset, identifies compelling events matching campaign criteria, researches target personas associated with those events, creates or updates CRM records in HubSpot, and drafts personalized initial outreach emails. Follow-ups are sent on a deterministic schedule (3, 5, and 7 days after initial contact) unless prospects respond. The system tracks email engagement metrics (opens, deliveries, bounces) via SendGrid webhooks and removes contacts from follow-up sequences when they reply.

Campaign definitions are stored as Google Docs in a designated folder. The system monitors this folder daily at 7am Pacific for new or modified campaign documents. When changes are detected, a campaign manager agent parses the human-authored logic into structured prompts that guide prospect selection, event qualification, and email personalization for that campaign. Multiple campaigns can run in parallel, each with its own targeting criteria and messaging guidelines.

## Custom Instructions
*FDE-provided instructions for how this particular workforce specification should be configured*
<!--
This workforce represents a production sales automation system. Campaign logic is defined by human sales strategists in Google Docs and parsed by the CampaignManager agent. The EventSelector, CRMManager, and Outreach agents use this logic to make decisions about event qualification, prospect targeting, and message personalization. All outreach activity is logged to HubSpot and tracked via SendGrid webhooks for metric reporting.
-->

## Path Audit

Defines the possible paths for workflow execution.

### Agent Architecture

**Core Agent Responsibilities:**
- **CampaignManager Agent**: Monitors campaign configuration documents in Google Drive; parses human-authored campaign logic into structured prompts for use by downstream agents; validates completeness of campaign definitions; requests clarification from human campaign managers via Slack when needed
    - Located in: campaign configuration workflow (runs daily at 7am Pacific)
- **EventSelector Agent**: Reviews news events from Exa webset against campaign-defined compelling event criteria and target company criteria; selects qualified events that have not been used in the past 30 days; provides reasoning for event selections
    - Located in: prospect research workflow main loop (runs daily at 8am Pacific per campaign)
- **CRMManager Agent**: Searches HubSpot for existing company and contact records; creates new records or updates existing records with event context; establishes parent/child company relationships when detected; ensures all prospects have valid HubSpot IDs before outreach
    - Located in: prospect research workflow after event research (runs daily at 8am Pacific per campaign)
- **Outreach Agent**: Evaluates prospects against targeting criteria; searches the web for additional context; enriches missing email addresses via Hunter.io; drafts personalized initial outreach and follow-up messages adhering to campaign email guidelines; decides which prospects to target based on past email activity
    - Located in: prospect research workflow for initial outreach (runs daily at 8am Pacific per campaign) and follow-up outreach (runs daily at deterministic time between 10am-2pm Pacific per campaign)

**User Touchpoints**: 
- Human campaign managers edit campaign logic documents in Google Drive to define targeting criteria and email guidelines; the CampaignManager agent may request clarification via Slack if definitions are incomplete
- Slack channel receives workflow status notifications, event selection reasoning, outreach drafts, and error messages
- All drafted emails are visible in Slack before being sent, though no explicit approval gate is implemented
- HubSpot serves as the system of record for all prospect and company data, outreach history, and follow-up scheduling

### Decision Ledger

**Campaign Configuration Decisions:**

1. Detect new or modified campaign documents
   - Inputs: Google Drive folder listing with file metadata (modified timestamps)
   - Outputs: List of campaigns requiring logic refresh
   - Decision logic: Compare stored last-modified timestamps (from local JSON file) against Google Drive file metadata; identify new files (not in storage) or modified files (timestamp mismatch)
   - Logic location: Internal code (CampaignConfiguration.get_campaigns)

2. Parse campaign logic document into structured definitions
   - Inputs: Plain text content of Google Doc campaign definition
   - Outputs: Structured LogicDefinition object with six fields: exa_webset_id, compelling_event, target_company, target_personas, outreach_selection, email_guidelines
   - Decision logic: Agent extracts and sorts unstructured campaign content into predefined sections; preserves formatting; identifies obvious spelling/instruction errors; detects missing sections; does not add/remove content except for optimization
   - Logic location: Internal prompt (CampaignManager agent system prompt in campaign_manager.yaml)

3. Request clarification from human campaign manager
   - Inputs: Incomplete or ambiguous campaign definition content
   - Outputs: Slack message to human with instructions to update document; subsequent fetch of updated document after human confirmation
   - Decision logic: When uncertain about campaign criteria or unable to classify instructions, send Slack message asking human to update the Google Doc directly (not respond via Slack); wait for human confirmation; re-fetch document; continue parsing
   - Logic location: Internal prompt (CampaignManager agent); action invocation is LLM-driven (fetch_campaign_logic, send_slack_message @llmcallables)

4. Determine campaign definition completeness
   - Inputs: Parsed campaign logic structure from agent
   - Outputs: Complete LogicDefinition stored to JSON, or timeout handling if human doesn't respond within 15 minutes
   - Decision logic: Agent must return logic_definition dictionary with all six required fields populated; if timeout occurs before completion, re-fetch latest document content and extract final definition
   - Logic location: Internal code (CampaignConfiguration.run_campaign_update); internal prompt (CampaignManager agent must return logic_definition when complete)

**Prospect Research Decisions (Event-Based Outreach):**

5. Fetch news events from Exa webset
   - Inputs: Exa webset ID from campaign definition
   - Outputs: List of news event summaries from webset items (uses "Summary" enrichment field or item description as fallback)
   - Decision logic: Retrieve all items from specified webset via Exa API; extract summary text from enrichments array
   - Logic location: Internal code (ProspectResearch.get_webset_events)

6. Select qualified events for prospecting
   - Inputs: List of news event summaries, past event selections from last 30 days (stored in data/selected_events.json), compelling event logic, target company logic
   - Outputs: Reasoning explanation and list of selected event indices; selected events saved to JSON file with today's date
   - Decision logic: Agent evaluates each event against compelling event criteria and target company criteria; excludes events already selected in past 30 days; provides qualitative reasoning describing selected events without referencing indices
   - Logic location: External prompt (EventSelector agent; compelling_event_logic and target_company_logic are runtime-injected from campaign definition via message_thread.substitute_variables)

7. Research prospects for each qualified event (parallel)
   - Inputs: Event summary text, target_personas logic from campaign definition
   - Outputs: List of TargetPersona objects with fields: first_name, last_name, job_title, company_name, company_domain_name, location, email (optional), linkedin_url (optional), relevance_explanation
   - Decision logic: Use Exa Research API with structured output schema to identify names, titles, companies of target personas mentioned in or related to the news event; follow target_personas criteria
   - Logic location: Internal code (ProspectResearch.research_event); external prompt (target_personas logic from campaign definition passed to Exa research instructions)

8. Retry failed research tasks (optimistic error handling)
   - Inputs: Exception from research task; retry attempt counter (max 3 attempts)
   - Outputs: Research results or None if all retries fail; Slack notification on final failure
   - Decision logic: On exception, wait 2 seconds and retry; if final attempt fails, log error to Slack ("Error calling Exa's research API after 3 attempts") and return None; continue with other events
   - Logic location: Internal code (ProspectResearch.research_event exception handling)

9. Identify company records in CRM (parallel per event)
   - Inputs: Event summary, list of prospect personas
   - Outputs: Updated prospect list with hubspot_contact_id populated for each persona
   - Decision logic: Agent performs keyword search for each company using tokenized matching on name/domain; if no record exists, create new company record; if parent company detected from event context, search for parent and establish association; for each persona, search by first/last name or create new contact; associate contact with company; update prospect objects with CRM IDs
   - Logic location: Internal prompt (CRMManager agent); actions are LLM-driven (keyword_search_companies, add_company_record, update_company_record, add_contact_record @llmcallables)

10. Decide to add vs update company record
    - Inputs: Keyword search results from HubSpot
    - Outputs: Action to create new company or update existing company description
    - Decision logic: If keyword search returns matches, use existing company ID and update description to mention the news event; if no matches, create new company with event context in description field
    - Logic location: Internal prompt (CRMManager agent); actions are LLM-driven

11. Infer parent company relationships
    - Inputs: News event summary mentioning portfolio/parent companies
    - Outputs: Parent company keyword search and association creation
    - Decision logic: When event mentions parent/portfolio company relationship (e.g., "KKR portfolio company"), search for parent company first to get ID, then pass parent_company_id when creating or updating child company record
    - Logic location: Internal prompt (CRMManager agent); actions are LLM-driven

12. Handle CRM rate limiting and errors
    - Inputs: Exception response from HubSpot API indicating rate limit or system error
    - Outputs: Retry action with possible reduced parallelization
    - Decision logic: If action returns rate limit error, agent retries with fewer parallel actions; system errors retried at least once before abandoning CRM update for that event
    - Logic location: Internal prompt (CRMManager agent instructions: "It's possible the CRM system rate-limits your requests -- if so, retry the action, possibly with less parallelization. System errors should be re-attempted at least once")

13. Determine CRM update completeness
    - Inputs: Agent's final response after all CRM actions complete
    - Outputs: Summary of companies added/updated, contacts added/updated, parent relationships created
    - Decision logic: Agent must return summary field describing all CRM changes; workflow extracts updated prospect list (now with hubspot_contact_id populated) from CRMManager.prospects instance attribute
    - Logic location: Internal code (ProspectResearch.update_crm extracts crm_manager.prospects after agent completes); internal prompt (CRMManager agent must provide summary)

14. Filter prospects without valid HubSpot contact IDs
    - Inputs: List of target personas after CRM update
    - Outputs: Filtered list containing only personas with hubspot_contact_id populated
    - Decision logic: If hubspot_contact_id is None, exclude persona from outreach; log warning to Slack: "No outreach drafted for event: [event]. No prospects with valid HubSpot contact IDs found."
    - Logic location: Internal code (Outreach.draft_message filtering valid_target_individuals)

15. Select prospects for outreach
    - Inputs: Event summary, list of valid prospects with HubSpot IDs, past email activity stats from HubSpot, outreach_selection logic from campaign
    - Outputs: List of prospects to target (may be subset of input list); explanation of selection reasoning
    - Decision logic: Agent evaluates each prospect against outreach_selection criteria; checks past_email_activity field (total_exchanged, last_exchange_at, account_exec_outreach_phase); excludes prospects already in outreach sequence (account_exec_outreach_phase is set); may search web for additional context (max 3 searches)
    - Logic location: External prompt (Outreach agent; outreach_selection logic from campaign definition injected via message_thread.substitute_variables)

16. Decide to search the web for prospect context
    - Inputs: Prospect details, event summary, search attempt counter (max 3)
    - Outputs: Web search results from Tavily or skip if max attempts reached
    - Decision logic: Agent decides whether web search will improve outreach personalization; if helpful, invoke search_web action; if counter exceeds 3, action returns "You've reached the maximum number of search attempts. Do not search again."
    - Logic location: Internal prompt (Outreach agent instructions: "If helpful, though not required, you can search the web up to 3 times"); action is LLM-driven (search_web @llmcallable)

17. Enrich missing email addresses
    - Inputs: Prospect with no email address; company domain name, first name, last name
    - Outputs: Email address with confidence score from Hunter.io, or failure message
    - Decision logic: If persona has no email, invoke search_for_contact_info action after identifying prospects to target; if confidence score < 50 or no email found, exclude prospect from outreach; never enrich same individual twice
    - Logic location: Internal prompt (Outreach agent instructions: "If an email address is not provided, take the action to search for it. If the search returns a very low confidence score (below 50) or does not find an email address at all, do not select this individual to reach out to. Only search for the email address after identifying the individual(s) to reach out to.")

18. Override email address in test mode
    - Inputs: Environment variable SLACK_CHANNEL_OVERRIDE is set
    - Outputs: Test email address "alex@qurrent.ai" instead of Hunter.io result
    - Decision logic: When SLACK_CHANNEL_OVERRIDE env var is set, return test email address; log "Using test email address"
    - Logic location: Internal code (Outreach.search_for_contact_info checks environment variable)

19. Draft personalized outreach email
    - Inputs: Event summary, selected prospect details, email_guidelines logic from campaign
    - Outputs: OutreachMessage object with fields: hubspot_contact_id, to (email), subject, body
    - Decision logic: Agent writes email adhering to email_guidelines criteria; must reference event and how it relates to specific individual; must address individual by name in body; may incorporate web search findings if performed; follows specified tone, structure, personalization approaches from guidelines
    - Logic location: External prompt (Outreach agent; email_guidelines logic from campaign definition injected via message_thread.substitute_variables)

20. Determine workflow completion after outreach actions
    - Inputs: Agent response after web searches and email enrichment
    - Outputs: Final outreach message list or empty list with explanation
    - Decision logic: Agent workflow separates research phase (return actions only, no outreach) from drafting phase (return outreach only, no actions); after rerun responses complete, use final response to extract outreach list; if empty, send Slack notification with explanation
    - Logic location: Internal prompt (Outreach agent instructions: "When you are researching the contact, DO NOT respond with the outreach message -- only actions. When you are ready to draft the outreach message(s), DO NOT respond with any actions -- only the message")

21. Send outreach email via SendGrid
    - Inputs: OutreachMessage, demo record flag from HubSpot
    - Outputs: Email sent status (true/false)
    - Decision logic: If is_demo_record is true, override recipient to "alex@qurrent.ai"; always BCC "48618838@bcc.hubspot.com" for HubSpot tracking; append email signature from cole_email_signature.html; send via SendGrid API; if status code is 200/201/202, return true, else return false
    - Logic location: Internal code (SendGrid.send_email)

22. Update HubSpot contact after initial outreach sent
    - Inputs: OutreachMessage, email sent status
    - Outputs: Updated HubSpot contact properties or skip if email failed
    - Decision logic: If email not sent, log warning and skip CRM update; if sent, update contact with: account_exec_email_subject, account_exec_email_body, account_exec_outreach_trigger (event summary), account_exec_outreach_phase="1", account_exec_next_outreach_date (3 days from today at midnight UTC as epoch milliseconds)
    - Logic location: Internal code (ProspectResearch.send_initial_outreach)

23. Initialize metrics tracking for outreach recipients
    - Inputs: List of recipient email addresses from outreach messages
    - Outputs: JSON file per workflow instance with email metric counters initialized to 0
    - Decision logic: Create or update data/email_metrics/email_metrics_{workflow_instance_id}.json; for each email, initialize open_count, delivered_count, bounce_count to 0 and events arrays to empty
    - Logic location: Internal code (MetricsTracker.initialize_metrics called after initial outreach sent)

**Follow-Up Outreach Decisions:**

24. Determine follow-up execution time
    - Inputs: Campaign ID, today's date in Pacific timezone
    - Outputs: Seconds to wait until deterministic time window (10am-2pm Pacific) for this campaign
    - Decision logic: Hash campaign ID + today's date with SHA256; use first byte mod 4 to pick hour (10, 11, 12, or 13); use second byte mod 60 for minute; if time has passed today, calculate for tomorrow's deterministic window
    - Logic location: Internal code (time_until_follow_ups function in server.py)

25. Identify contacts requiring follow-up today
    - Inputs: Today's date (Pacific timezone midnight boundaries converted to UTC epoch milliseconds)
    - Outputs: List of HubSpot contacts where account_exec_next_outreach_date falls within today's window
    - Decision logic: Search HubSpot for contacts where account_exec_next_outreach_date >= start of today (UTC) AND < start of tomorrow (UTC); retrieve contact properties and associated company name
    - Logic location: Internal code (HubSpot.get_contacts_requiring_follow_up)

26. Check if contact has responded to outreach
    - Inputs: HubSpot contact ID
    - Outputs: Decision to remove from follow-up queue or proceed with follow-up draft
    - Decision logic: Fetch recent contact emails from HubSpot; if any email has direction="INCOMING_EMAIL", contact has responded; log metric (reply count); update contact to clear account_exec_outreach_phase and account_exec_next_outreach_date; send Slack notification; return None to skip follow-up
    - Logic location: Internal code (ProspectResearch.send_followup checks past_emails for incoming direction)

27. Draft follow-up email
    - Inputs: Contact details including last email subject/body, outreach trigger, outreach phase number
    - Outputs: OutreachMessage for follow-up or None if no outreach should be sent
   - Decision logic: Agent drafts short follow-up referencing last email; must use exact same subject line as last email (no "Re:" or modifications); distinctness increases with follow-up number; for phase > 0, agent told "This is follow-up number {phase}. Be sure to reference the last email, but make this one distinct."
    - Logic location: Internal prompt (Outreach agent with different prompting for follow-ups vs initial outreach; see Outreach.draft_follow_up)

28. Send follow-up email and update contact
    - Inputs: OutreachMessage, demo record flag
    - Outputs: Email sent status; updated HubSpot contact properties
    - Decision logic: Send email via SendGrid; if send fails, log error and return None; if send succeeds and next phase exists in FOLLOW_UP_DELAY_DAYS map (phase+1: 0, 3, 5, 7 days), calculate next_outreach_date as midnight UTC + delay days; update contact with new subject/body, incremented phase, next date; if final follow-up (phase 3), set next_outreach_date to empty string
    - Logic location: Internal code (ProspectResearch.send_followup)

**Email Metrics Tracking Decisions:**

29. Process SendGrid webhook event
    - Inputs: SendGrid webhook payload (single event dict or list of events)
    - Outputs: Metrics logged to Qurrent Supervisor API; local metrics JSON file updated
    - Decision logic: For each event, check event type; if not in METRIC_MAPPINGS (open, bounce, delivered), skip; find workflow_instance_id for recipient email by searching email_metrics JSON files; check if event type already logged (delivered/bounce only logged once; opens can repeat); if should log, POST metric to Supervisor API with appropriate metric_id; record event timestamp in local JSON
    - Logic location: Internal code (handle_sendgrid_event function in server.py)

30. Deduplicate metric events
    - Inputs: Workflow instance ID, recipient email, event type
    - Outputs: Boolean indicating whether to log this event
    - Decision logic: Load metrics JSON for workflow; check email_data[email_type_count] and events array; if event_type is "delivered" or "bounce" and events array has entries, return false (already logged); if event_type is "open", allow multiple (commented-out code suggests this was once deduplicated but now allows repeats)
    - Logic location: Internal code (MetricsTracker.should_log_event)

**Workflow Scheduling Decisions:**

31. Schedule daily campaign configuration refresh
    - Inputs: Current time in Pacific timezone
    - Outputs: Sleep duration until 7am Pacific tomorrow
    - Decision logic: Calculate seconds until 7am Pacific; if 7am has passed today, calculate for tomorrow; sleep for that duration, then run configure_campaigns
    - Logic location: Internal code (manage_campaigns loop with _get_wait_seconds(hour=7))

32. Schedule daily event-based outreach
    - Inputs: Campaign definition, current time in Pacific timezone
    - Outputs: Sleep duration until 8am Pacific tomorrow
    - Decision logic: Calculate seconds until 8am Pacific; if 8am has passed today, calculate for tomorrow; sleep for that duration, then run_campaign_workflow with run_followups=False
    - Logic location: Internal code (schedule_daily_run function)

33. Schedule daily follow-up outreach
    - Inputs: Campaign definition, current time in Pacific timezone
    - Outputs: Sleep duration until deterministic time window (10am-2pm Pacific)
    - Decision logic: Use time_until_follow_ups to get deterministic wait time; sleep for that duration, then run_campaign_workflow with run_followups=True
    - Logic location: Internal code (schedule_followups function)

34. Trigger immediate campaign run on Slack command
    - Inputs: Slack slash command "/configure-campaigns"
    - Outputs: Immediate execution of configure_campaigns; if start_immediately flag is set, also run event-based outreach for all campaigns
    - Decision logic: Event loop listens for configure-campaigns command; when received, call configure_campaigns; if START_IMMEDIATELY env var is "true", spawn run_campaign_workflow tasks for all campaigns immediately
    - Logic location: Internal code (main event loop in server.py)

35. Decide whether to use simulated test data
    - Inputs: SIMULATED_STEPS list (configured in workflow.py)
    - Outputs: Return hard-coded test data for specified steps, or execute actual function
    - Decision logic: Check if step name (research_prospects, update_crm, draft_outreach, draft_followups) is in SIMULATED_STEPS list; if yes, load from JSON file in data/tests/; if no, execute provided async function
    - Logic location: Internal code (ProspectResearch._simulate_or_call helper method)

## Data & Formats

### Referenced Documents Inventory and Input Data

- **Campaign Logic Documents**
    - Format: Google Docs (exported as plain text)
    - Source: Google Drive folder ID 1GZoagbXw4sMYPLQ0cz7s2Q88lTwrbxZV (monitored by GoogleDriveClient)
    - Intended Use: Configuration workflow parses documents into LogicDefinition objects with six structured prompt fields for use by EventSelector, CRMManager, and Outreach agents

- **Exa Webset Items**
    - Format: JSON (from Exa API response with items array containing enrichments)
    - Source: Exa webset specified by exa_webset_id in campaign definition
    - Intended Use: EventSelector agent evaluates webset items as candidate news events; uses "Summary" enrichment field or item description as event text

- **HubSpot Contact Records**
    - Format: JSON (from HubSpot CRM API)
    - Source: HubSpot portal via API (properties: firstname, lastname, email, jobtitle, hs_linkedin_url, account_exec_outreach_phase, account_exec_next_outreach_date, account_exec_email_subject, account_exec_email_body, account_exec_outreach_trigger, is_demo_record)
    - Intended Use: Outreach agent checks past email activity to determine targeting; follow-up workflow queries contacts requiring follow-up; all outreach history tracked via custom HubSpot properties

- **HubSpot Company Records**
    - Format: JSON (from HubSpot CRM API)
    - Source: HubSpot portal via API (properties: name, domain, description, hs_parent_company_id, is_demo_record)
    - Intended Use: CRMManager agent searches, creates, and updates company records; establishes parent/child associations

- **HubSpot Email Engagements**
    - Format: JSON (from HubSpot CRM API batch read of email objects)
    - Source: HubSpot portal via associations API (properties: hs_email_subject, hs_email_direction, hs_email_from, hs_email_to, hs_email_text, hs_email_html, hs_email_sent_datetime)
    - Intended Use: Outreach agent reviews past email activity to avoid duplicate outreach; follow-up workflow checks for incoming emails (responses) to remove contacts from follow-up sequence

- **Stored Campaign Definitions**
    - Format: JSON (data/campaign_definitions.json)
    - Source: Local file system (updated by configuration workflow)
    - Intended Use: Track campaign IDs, names, last_modified_time, and ai_logic (LogicDefinition) to detect changes in Google Drive documents

- **Selected Events History**
    - Format: JSON (data/selected_events.json)
    - Source: Local file system (updated by EventSelector agent)
    - Intended Use: Track which event indices were selected on which dates over past 30 days to avoid duplicate event processing

- **Email Metrics Tracking**
    - Format: JSON (data/email_metrics/email_metrics_{workflow_instance_id}.json)
    - Source: Local file system (updated by MetricsTracker)
    - Intended Use: Track open_count, delivered_count, bounce_count, and event timestamps per recipient email per workflow instance; deduplicate SendGrid webhook events

- **Cole Email Signature**
    - Format: HTML (prospecting/cole_email_signature.html)
    - Source: Local file system
    - Intended Use: Appended to all outreach email bodies before sending via SendGrid

- **Test/Simulation Data**
    - Format: JSON (data/tests/research_prospects.json, update_crm.json, draft_outreach.json, draft_followups.json)
    - Source: Local file system (dumped by workflow after successful execution, loaded during simulation)
    - Intended Use: Allow testing of workflow steps without calling external APIs; controlled by SIMULATED_STEPS configuration

### Example Output Artifacts

- **Parsed Campaign Logic**
    - Type: Structured configuration object
    - Format: LogicDefinition model with fields: exa_webset_id, compelling_event, target_company, target_personas, outreach_selection, email_guidelines
    - Recipients: Saved to data/campaign_definitions.json; used by ProspectResearch workflow agents
    - Contents: Natural language prompts that define event qualification rules, company targeting criteria, persona targeting rules, outreach prioritization logic, and email writing guidelines

- **Initial Outreach Email**
    - Type: Email message
    - Format: HTML (with signature appended)
    - Recipients: Target prospects identified by Outreach agent (or alex@qurrent.ai for demo records)
    - Contents: Subject line, body with event reference and personalized hook, Cole Salquist's email signature; BCC to 48618838@bcc.hubspot.com for HubSpot tracking

- **Follow-Up Email**
    - Type: Email message
    - Format: HTML (with signature appended)
    - Recipients: Contacts in HubSpot follow-up queue who haven't responded
    - Contents: Same subject line as initial email (no "Re:" prefix), short body referencing last email with distinct messaging, signature; BCC to HubSpot

- **Slack Notifications**
    - Type: Slack message
    - Format: Plain text or markdown (some use bold with asterisks)
    - Recipients: Channel ID from config (SLACK_CHANNEL_ID)
    - Contents: Event selection reasoning, event summaries with bullets, drafted outreach messages (subject + to + body), follow-up notifications, error messages, campaign update status, contact removal from follow-up queue

- **Qurrent Console Logs**
    - Type: Observable output
    - Format: Plain text or JSON (for structured content)
    - Recipients: Qurrent OS console (via save_to_console)
    - Contents: Webset event counts and summaries, research completion summaries, CRM update summaries, outreach drafted summaries, follow-up summaries, error messages; types: "observable_output", "output", "error"

- **HubSpot Contact Updates**
    - Type: CRM record updates
    - Format: JSON (HubSpot API properties object)
    - Recipients: HubSpot CRM (specific contact IDs)
    - Contents: account_exec_email_subject, account_exec_email_body, account_exec_outreach_trigger (event summary), account_exec_outreach_phase (1, 2, 3, or empty), account_exec_next_outreach_date (epoch milliseconds or empty)

- **Email Engagement Metrics**
    - Type: Metric data points
    - Format: JSON (posted to Qurrent Supervisor API)
    - Recipients: Qurrent Supervisor at https://external.qurrent.ai/dev/metrics_data
    - Contents: metric_id (UUID for open/bounce/delivered), workflow_instance_id, measure (always 1.0); tracked locally in data/email_metrics/ JSON files

## Integration Summary

**Integrations:**

- **Exa (Prebuilt SDK)**: Provides webset monitoring for news event sourcing; each campaign configured with an exa_webset_id; retrieves items with enrichments via API; also provides Research API (exa-research model) for structured prospect research against news events with JSON output schema

- **Exa Research Client**: Separate research task API for identifying target personas from event descriptions; accepts natural language instructions, output schema (JSON Schema), and model name; returns structured research_results with person/company details; polls for task completion; retry logic with 3 max attempts and Slack error notification

- **Tavily**: Web search API for enriching prospect context during outreach drafting; Outreach agent can invoke up to 3 searches per workflow run; exponential backoff retry with jitter (max 5 retries); search results used to personalize email messaging

- **HubSpot CRM**: Central system of record for companies, contacts, and outreach tracking; supports keyword search (tokenized CONTAINS_TOKEN), create/update companies and contacts, parent/child company associations, contact-company associations, email engagement history retrieval (batch read of email objects), follow-up queue queries (by account_exec_next_outreach_date), demo record filtering (is_demo_record property); rate limiting handled with exponential backoff; persistent session with connection reuse; locks prevent race conditions on create/update operations

- **Hunter.io**: Email finder API for enriching missing prospect email addresses; called by Outreach agent when prospect has no email; takes domain, first_name, last_name; returns email with confidence score; if confidence < 50, prospect excluded from outreach; overridden with test email in SLACK_CHANNEL_OVERRIDE mode

- **SendGrid**: Transactional email service for outreach delivery; sends HTML emails with signature; overrides recipient to alex@qurrent.ai for demo records; always BCCs 48618838@bcc.hubspot.com for HubSpot tracking; returns success on 200/201/202 status codes

- **SendGrid Webhooks**: Event notifications for email engagement metrics (open, delivered, bounce); webhook endpoint /sendgrid-event listens on port 8000; events queued via Qurrent ingress; handler finds workflow by recipient email, checks deduplication, logs metric to Supervisor API, records timestamp locally

- **Google Drive (via Service Account)**: Campaign configuration document storage; service account JSON credentials loaded from Secret Manager (AE_SERVICE_ACCOUNT_JSON env var); lists Google Docs in folder ID 1GZoagbXw4sMYPLQ0cz7s2Q88lTwrbxZV; downloads docs as plain text; tracks modified timestamps to detect changes; read-only access via drive.readonly scope

- **GCP Secret Manager**: Credential storage for API keys; load_secrets.py fetches secrets: ae_customer_keys, llm_keys, ae_additional_keys, ae_service_account; parsed as YAML and exported to environment variables; content also written to config.yaml for Qurrent Config loading

- **GCP Cloud Storage**: Optional persistence layer for JSON data files (e.g., selected events history); supports local file fallback via USE_LOCAL flag; bucket name: account_exec_{environment}; currently not actively used (local file storage preferred)

- **Qurrent Slack**: Bidirectional Slack integration for notifications and commands; registers /configure-campaigns slash command; sends messages to configured channel ID; links/unlinks workflow instances to channels; used for campaign manager clarifications, event reasoning, outreach visibility, error alerts

- **Qurrent Ingress**: Event queue for handling SendGrid webhooks and Slack commands; get_start_event() blocks until event arrives; events routed to appropriate handlers (SendGridWebhookEvent → handle_sendgrid_event); supports workflow-level event delivery (get_workflow_event for campaign manager human-in-loop)

- **Qurrent Supervisor API**: Metrics reporting endpoint at https://external.qurrent.ai/dev/metrics_data; receives email engagement metrics (open, bounce, delivered) with metric_id, workflow_instance_id, measure; authenticated via CUSTOMER_KEY_DEV

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
├── data/
│   ├── campaign_definitions.json
│   ├── selected_events.json
│   ├── email_metrics/
│   │   └── email_metrics_{workflow_instance_id}.json
│   └── tests/
│       ├── research_prospects.json
│       ├── update_crm.json
│       ├── draft_outreach.json
│       └── draft_followups.json
├── server.py
├── load_secrets.py
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Agents

### `CampaignManager`
**Pattern:** Task
**Purpose:** Parse human-authored campaign logic documents from Google Drive into structured prompt definitions for downstream agents; request clarification from humans when definitions are incomplete or ambiguous
**LLM:** claude-sonnet-4-20250514 (fallback: gpt-5), standard mode, temp=default, timeout=300 seconds

**Prompt Strategy:**
- Sorts unstructured campaign document into six predefined logic definition sections
- Preserves formatting; identifies obvious instruction errors; does not add/remove content except for optimization
- When uncertain or missing sections, asks human to update Google Doc directly (not respond via Slack)
- Must return empty logic_definition dictionary when clarifying; only returns populated logic_definition when complete
- Context: accumulates across rerun loop (human clarification messages appended to thread)
- JSON Response: `{"actions": [{"name": "fetch_campaign_logic" | "send_slack_message", "args": {...}}], "logic_definition": {} | {"exa_webset_id": "...", "compelling_event_logic": "...", "target_company_logic": "...", "target_personas_logic": "...", "outreach_selection_logic": "...", "email_guidelines_logic": "..."}}`

**Instance Attributes:**
- `slack_bot: Slack` - Qurrent Slack integration for sending clarification messages
- `channel_id: str` - Slack channel ID for sending messages
- `google_drive_client: GoogleDriveClient` - Client for fetching campaign documents
- `file_id: str` - Google Drive file ID of current campaign being processed

**Create Parameters:**
- `yaml_config_path: str` - Path to campaign_manager.yaml
- `workflow_instance_id: UUID` - Workflow instance ID from parent workflow
- `slack_bot: Slack` - Passed from CampaignConfiguration workflow
- `channel_id: str` - Passed from parent workflow config
- `google_drive_client: GoogleDriveClient` - Instantiated in CampaignConfiguration

#### LLM Callables

**`fetch_campaign_logic() -> str`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Docstring Args: None
- Purpose: Retrieves latest content of campaign logic document from Google Drive
- Integration usage:
    - Calls `self.google_drive_client.download_file_content(self.file_id)` to fetch plain text export of Google Doc
- Returns: Plain text content of campaign document; raises ValueError if no file_id set
- Error Handling: Raises ValueError("No File ID provided for campaign logic") if file_id not set

**`send_slack_message(message: str) -> str`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Docstring Args: `message (str): The message to send`
- Purpose: Send clarification request to human campaign manager in Slack channel
- Integration usage:
    - Calls `self.slack_bot.send_message(channel_id=self.channel_id, message=message)` to post message
- Returns: "The message was sent successfully"

### `CRMManager`
**Pattern:** Task
**Purpose:** Search HubSpot CRM for existing company and contact records; create or update records with event context; establish parent/child company relationships; ensure all prospects have HubSpot IDs before outreach
**LLM:** gpt-5 (fallback: claude-sonnet-4-20250514), standard mode, temp=default, timeout=300 seconds

**Prompt Strategy:**
- First checks if companies/contacts exist via keyword search
- Creates records if not found; updates existing records to mention news event in description
- Infers parent company relationships from event context
- Runs multiple actions in parallel when efficient; works iteratively when actions depend on results
- Retries on rate limit errors (possibly with less parallelization); retries system errors at least once
- Must return summary of all CRM updates after completion
- Context: single user message with event summary and prospect JSON list
- JSON Response: `{"reasoning": "...", "actions": [{"name": "keyword_search_companies" | "add_company_record" | "update_company_record" | "add_contact_record", "args": {...}}], "summary": "..."}`

**Instance Attributes:**
- `hubspot: HubSpot` - HubSpot CRM client for API operations
- `prospects: List[TargetPersona]` - List of prospect personas being processed; hubspot_contact_id updated in-place as contacts are created

**Create Parameters:**
- `yaml_config_path: str` - Path to crm_manager.yaml
- `workflow_instance_id: UUID` - Workflow instance ID from ProspectResearch workflow
- `hubspot: HubSpot` - Passed from ProspectResearch workflow
- `prospects: List[TargetPersona]` - List of prospects for current event

#### LLM Callables

**`keyword_search_companies(keyword: str) -> str`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Docstring Args: `keyword (str): Keyword token to search for (e.g., brand acronym like 'kkr')`
- Purpose: Fuzzy search companies by keyword across name and domain using tokenized matching
- Integration usage:
    - Calls `self.hubspot.keyword_search_companies(keyword)` which uses HubSpot search API with CONTAINS_TOKEN operator
- Returns: JSON string of search results list (each item: company_id, company_name, domain, company_description, parent_company_id)
- Error Handling: Returns `f"Exception raised searching for companies with keyword {keyword}: {str(e)}"`

**`add_company_record(company_name: str, company_description: str, parent_company_id: Optional[str] = None) -> str`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Docstring Args: `company_name (str): The name of the company to add, company_description (str): The description of the company to add, parent_company_id (Optional[str]): The ID of the parent company to add`
- Purpose: Add a company to the CRM; optionally associate with parent company
- Integration usage:
    - Calls `self.hubspot.create_company(company_name, company_description)` to create record
    - If parent_company_id provided, calls `self.hubspot.associate_parent_company(parent_company_id, company_id)` to establish relationship
- Returns: `f"Successfully created record for company {company_name} with ID: {company_id}"`
- Error Handling: Returns `f"Exception raised creating company record {company_name}: {str(e)}"`

**`update_company_record(company_id: str, company_description: Optional[str] = None, parent_company_id: Optional[str] = None) -> str`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Docstring Args: `company_id (str): The ID of the company to update, company_description (Optional[str]): The updated description of the company, parent_company_id (Optional[str]): The updated ID of the parent company`
- Purpose: Update existing company record in the CRM
- Integration usage:
    - If company_description provided, adds to properties dict
    - Calls `self.hubspot.update_company(company_id, properties)` to update record
    - If parent_company_id provided, calls `self.hubspot.associate_parent_company(parent_company_id, company_id)`
- Returns: `f"Successfully updated company record {company_id}"`
- Error Handling: Returns `f"Exception raised updating company record {company_id}: {str(e)}"`

**`add_contact_record(first_name: str, last_name: str, company_id: str, job_title: str, email: Optional[str] = None, linkedin_url: Optional[str] = None) -> str`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Docstring Args: `first_name (str): The first name of the contact to add, last_name (str): The last name of the contact to add, company_id (str): The ID of the company to add the contact to, job_title (str): The job title of the contact to add, email (Optional[str]): The email of the contact to add, linkedin_url (Optional[str]): The LinkedIn URL of the contact to add`
- Purpose: Add a contact to the CRM and associate with company
- Integration usage:
    - Calls `self.hubspot.create_or_update_contact(first_name, last_name, company_id, job_title, email, linkedin_url)` to create/update contact
- Returns: `f"Successfully created record for contact {first_name} {last_name} with contact ID: {contact_id}"`
- Side Effects: Updates `self.prospects` by finding matching persona (first_name + last_name) and calling `persona.update_hubspot_contact_id(contact_id)` to populate hubspot_contact_id field
- Error Handling: Returns `f"Exception raised creating contact record {first_name} {last_name}: {str(e)}"`

### `EventSelector`
**Pattern:** Task
**Purpose:** Review news events from Exa webset against campaign-defined criteria; select qualified events that haven't been used in past 30 days; provide reasoning for selections
**LLM:** gpt-5 (fallback: claude-sonnet-4-20250514), standard mode, temp=default, timeout=300 seconds

**Prompt Strategy:**
- Evaluates each event (provided as numbered list with separators) against compelling_event_logic and target_company_logic (runtime-injected via variable substitution)
- Excludes events already selected in past 30 days (provided as list of past selection indices)
- Returns reasoning that describes selected events qualitatively without referencing indices (reader is unaware of index mapping and event descriptions)
- Refers to selections as "events" not "items"
- Context: single invocation with numbered event list and past selections
- JSON Response: `{"reasoning": "...", "selections": [0, 3, 7, ...]}`

**Instance Attributes:**
- `exa_webset: Dict` - Full Exa webset response with items array (includes enrichments)
- `today_date: str` - Today's date in Pacific timezone (YYYY-MM-DD format)

**Create Parameters:**
- `yaml_config_path: str` - Path to event_selector.yaml
- `workflow_instance_id: UUID` - Workflow instance ID from ProspectResearch workflow
- `compelling_event: str` - compelling_event logic from campaign definition (injected into system prompt)
- `target_company: str` - target_company logic from campaign definition (injected into system prompt)
- `exa_webset: Dict` - Webset response from Exa API

#### Direct Actions

**`select_events() -> Tuple[str, List[str]]`**
- Purpose: Extract event summaries from webset, invoke agent to select qualified events, save selections to JSON file
- Message Thread modification:
    - Appends user message with numbered event list (calls `_get_prompt(event_summaries)` to format)
    - Appends user message with past selections from last 30 days (calls `_get_recent_selections()`)
- Integration usage:
    - Reads from `data/selected_events.json` for past selections (calls `_get_past_selections()`)
    - Writes selected events to `data/selected_events.json` with today's date as key
- Subagent usage:
    - Calls `await self()` to invoke agent with accumulated messages
- Returns: Tuple of (reasoning string, list of selected event summaries)
- Side Effects: Updates selected_events.json with today's selections

### `Outreach`
**Pattern:** Task
**Purpose:** Evaluate prospects against targeting criteria; search web for context; enrich missing emails; draft personalized initial and follow-up messages adhering to campaign guidelines
**LLM:** gpt-5 (fallback: claude-sonnet-4-20250514), standard mode, temp=default, timeout=300 seconds

**Prompt Strategy:**
- Decides which prospects to target based on targeting_criteria (runtime-injected via variable substitution)
- Follows writing_guidelines for email personalization (runtime-injected)
- Can search web up to 3 times if helpful (not required)
- Must search for email if not provided; if confidence < 50 or not found, exclude prospect
- Must not target individuals with existing outreach phase (already in sequence)
- Must reference event and relate to specific individual; address by name in body
- Workflow: research phase returns actions only (no outreach); drafting phase returns outreach only (no actions)
- Context: single invocation with event summary and target individuals JSON list (or contact details for follow-up)
- JSON Response: `{"explanation": "...", "actions": [{"name": "search_web" | "get_past_email_activity" | "search_for_contact_info", "args": {...}}], "outreach": [{"hubspot_contact_id": "...", "to": "...", "subject": "...", "body": "..."}, ...]}`

**Instance Attributes:**
- `slack_bot: Slack` - Qurrent Slack integration for notifications
- `channel_id: str` - Slack channel ID for sending messages
- `tavily: Tavily` - Web search API client
- `hubspot: HubSpot` - HubSpot CRM client
- `hunter_io: HunterIO` - Email finder API client
- `targeting_criteria: str` - outreach_selection logic from campaign (injected into system prompt)
- `email_guidelines_definition: str` - email_guidelines logic from campaign (injected into system prompt)
- `search_attempts: int` - Counter for web searches (max 3 per workflow run)

**Create Parameters:**
- `yaml_config_path: str` - Path to outreach.yaml
- `workflow_instance_id: UUID` - Workflow instance ID from ProspectResearch workflow
- `slack_bot: Slack` - Passed from ProspectResearch workflow
- `channel_id: str` - Passed from parent workflow config
- `tavily: Tavily` - Passed from ProspectResearch workflow
- `hubspot: HubSpot` - Passed from ProspectResearch workflow
- `hunter_io: HunterIO` - Passed from ProspectResearch workflow
- `targeting_criteria: str` - outreach_selection logic from campaign definition
- `email_guidelines_definition: str` - email_guidelines logic from campaign definition

#### LLM Callables

**`search_web(query: str) -> str | list[dict]`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Docstring Args: `query (str): The search query to execute`
- Purpose: Search the web with given query (max 3 attempts per workflow run)
- Integration usage:
    - Calls `self.tavily.search(query)` which wraps TavilyClient with retry logic
- Returns: Search results list or "You've reached the maximum number of search attempts. Do not search again." if limit exceeded
- Side Effects: Increments `self.search_attempts` counter

**`get_past_email_activity(hubspot_contact_id: str) -> str`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Docstring Args: `hubspot_contact_id (str): The ID of the contact to get past email activity for`
- Purpose: Returns summary of recent communication activity for a specific contact
- Integration usage:
    - Calls `self.hubspot.get_recent_contact_emails(hubspot_contact_id)` to fetch last 5 emails
- Returns: JSON string of email list (each: id, subject, direction, from, to, sent_at, body_preview)

**`search_for_contact_info(first_name: str, last_name: str, company_domain_name: str) -> str`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Docstring Args: `first_name (str): The first name of the target persona, last_name (str): The last name of the target persona, company_domain_name (str): The domain name of the target persona's company`
- Purpose: Uses Hunter.io to find email address for target persona
- Integration usage:
    - If SLACK_CHANNEL_OVERRIDE env var is set, returns test email: "This is a test run -- use the email address: alex@qurrent.ai"
    - Otherwise, calls `self.hunter_io.email_finder(company_domain_name, first_name, last_name)` to search for email
- Returns: JSON string of Hunter.io response (email, confidence score) or "Failed to search for contact info"
- Error Handling: Catches exceptions and returns "Failed to search for contact info"

#### Direct Actions

**`draft_message(event_summary: str, target_personas: List[TargetPersona]) -> List[OutreachMessage]`**
- Purpose: Draft initial outreach messages for event-based prospecting
- Message Thread modification:
    - Resets `self.search_attempts = 0`
    - Builds target_individuals list with persona dicts plus past_email_activity from HubSpot
    - Filters to valid_target_individuals (only those with hubspot_contact_id populated)
    - Appends user message with event summary and valid individuals JSON
- Integration usage:
    - For each persona with hubspot_contact_id, calls `self.hubspot.get_contact_email_exchange_stats(persona.hubspot_contact_id)` to get past_email_activity
- Subagent usage:
    - Calls `await self()` to invoke agent with accumulated messages
    - If response includes actions, calls `await self.get_rerun_responses(timeout=300)` and uses final rerun response
- Returns: List of OutreachMessage objects (parsed from agent's outreach array) or empty list if no outreach drafted
- Side Effects: Sends Slack message if no valid prospects or no outreach drafted

**`draft_follow_up(hubspot_contact: Dict) -> Optional[OutreachMessage]`**
- Purpose: Draft follow-up email for contact in follow-up queue
- Message Thread modification:
    - Builds contact_details_str with ID, name, email, company, outreach history (subject, body, trigger)
    - Appends user message with distinct prompting based on follow_up_phase: if phase > 0, "Draft a single, short follow-up email... This is follow-up number {phase}. Be sure to reference the last email, but make this one distinct. You MUST use the exact same subject line..."; if phase == 0, "Draft an outreach message... Prior to writing and enriching, search the web for information about the contact and the company and check past email activity."
- Subagent usage:
    - Calls `await self()` to invoke agent with accumulated messages
    - If response includes actions, calls `await self.get_rerun_responses(timeout=300)` and uses final rerun response
- Returns: OutreachMessage object (first message from agent's outreach array) or None if no outreach drafted
- Side Effects: Sends Slack message if no outreach drafted

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
    SLACK_APP_TOKEN
    SLACK_CHANNEL_ID

GCP:
    GOOGLE_CLOUD_PROJECT
    GOOGLE_APPLICATION_CREDENTIALS (path to service account JSON)
    AE_SERVICE_ACCOUNT_JSON (JSON content of service account)

ENVIRONMENT:
    ENVIRONMENT (production | development)
    START_IMMEDIATELY (true | false)
    SLACK_CHANNEL_OVERRIDE (optional channel ID for test mode)

## Utils

**`prospecting.models.parse_pacific(timestamp_str: str) -> datetime`**
- Purpose: Parse timestamp string in storage format (YYYY-MM-DD HH:MM:SS) and return Pacific-timezone-aware datetime
- Implementation: Uses datetime.strptime with format STORAGE_DT_FMT ("%Y-%m-%d %H:%M:%S"), then replaces tzinfo with ZoneInfo("America/Los_Angeles")
- Dependencies: Standard library datetime, zoneinfo

**`prospecting.models.format_pacific(dt: datetime) -> str`**
- Purpose: Format datetime as Pacific timezone string for storage
- Implementation: Converts datetime to Pacific timezone with as_pacific(dt), then formats with strftime(STORAGE_DT_FMT)
- Dependencies: Standard library datetime, zoneinfo

**`prospecting.models.as_pacific(dt: datetime) -> datetime`**
- Purpose: Convert datetime to Pacific timezone
- Implementation: If naive (tzinfo is None), replaces tzinfo with PACIFIC_TZ; otherwise converts with astimezone(PACIFIC_TZ)
- Dependencies: zoneinfo.ZoneInfo

**`prospecting.tests.dump_research_prospects(results: List[Tuple[str, List[TargetPersona]]]) -> None`**
- Purpose: Serialize prospect research results to JSON file for test simulation
- Implementation: Writes to data/tests/research_prospects.json with event_summary and prospects array; each prospect converted to dict with to_storage_dict()
- Dependencies: json, os

**`prospecting.tests.load_research_prospects() -> List[Tuple[str, List[TargetPersona]]]`**
- Purpose: Load simulated prospect research results from JSON file
- Implementation: Reads data/tests/research_prospects.json; parses each item into (event_summary, List[TargetPersona]) tuple; creates TargetPersona from storage dict
- Dependencies: json, os

**`prospecting.api.slack_utils.delete_all_messages(slack_bot: Slack, channel_id: str, delay_seconds: float = 0.1) -> int`**
- Purpose: Delete all messages in Slack channel including threaded replies
- Implementation: Uses conversations_history with pagination; for each message with reply_count > 0, fetches thread with conversations_replies and deletes replies first; then deletes parent message; adds configurable delay between deletions to avoid rate limits
- Dependencies: asyncio, qurrent.Slack

**`prospecting.metrics.MetricsTracker.initialize_metrics(workflow_instance_id: UUID, recipient_emails: list) -> None`**
- Purpose: Create or update metrics JSON file for workflow with per-email counters initialized
- Implementation: Creates data/email_metrics/email_metrics_{workflow_instance_id}.json with structure {workflow_id: {email: {open_count: 0, delivered_count: 0, bounce_count: 0, events: {open: [], delivered: [], bounce: []}}}; uses atomic write with tempfile to prevent corruption; sets file permissions 664 and directory permissions 2775
- Dependencies: json, tempfile, threading.RLock

**`prospecting.metrics.MetricsTracker.find_workflow_for_email(email: str) -> Optional[str]`**
- Purpose: Search all metrics JSON files to find workflow instance ID for given recipient email
- Implementation: Iterates through data/email_metrics/*.json files; loads each and checks if lowercase email is in workflow's email keys; returns first match or None
- Dependencies: json, pathlib

**`prospecting.metrics.MetricsTracker.should_log_event(workflow_instance_id: UUID, email: str, event_type: str) -> bool`**
- Purpose: Determine if SendGrid event should be logged (deduplication)
- Implementation: Loads metrics JSON; checks events array for event_type; if "delivered" or "bounce" and events array has entries, returns False (already logged once); if "open", always returns True (allows multiple)
- Dependencies: json, threading.RLock

**`server._get_wait_seconds(hour: int) -> float`**
- Purpose: Calculate seconds to wait until next scheduled run time at specified hour in Pacific timezone
- Implementation: Gets today's date in Pacific; constructs target datetime with specified hour; if time has passed, calculates for tomorrow; returns (target - now).total_seconds()
- Dependencies: datetime, zoneinfo

**`server.time_until_follow_ups(campaign: Campaign) -> float`**
- Purpose: Calculate deterministic wait time until follow-up window (10am-2pm PT) for campaign
- Implementation: Hashes campaign.id + today's date with SHA256; uses first byte mod 4 to pick hour (10-13); uses second byte mod 60 for minute; constructs target datetime; if passed, recalculates for tomorrow with new hash; returns wait seconds
- Dependencies: hashlib, datetime, zoneinfo

## Dependencies
- `tavily-python` - Tavily web search API client
- `requests` - HTTP library for Hunter.io and RSS.app APIs
- `aiohttp` - Async HTTP library for HubSpot API client (persistent sessions)
- `httpx` - Async HTTP library for Supervisor API metrics posting
- `google-auth`, `google-api-python-client`, `google-auth-oauthlib`, `google-auth-httplib2` - Google Drive API authentication and client
- `google-cloud-storage` - GCP Cloud Storage client for optional blob storage
- `exa-py==1.14.16` - Exa API client for webset monitoring and research API
- `sendgrid` - SendGrid transactional email API client
- `pydantic>=2.5` - Data validation and models (TargetPersona, Campaign, OutreachMessage, LogicDefinition)
- `loguru` - Logging framework
- `uvloop` - High-performance event loop for asyncio
- `feedparser` - RSS feed parsing (for RSS.app integration; not actively used in current workflow)
- `trafilatura`, `requests-html` - HTML content extraction (for RSS article processing; not actively used)
- `pandas` - Data manipulation (likely for metrics analysis; not actively used in current workflow)
- `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-exporter-gcp-trace` - Observability tracing to GCP (configured but usage not visible in analyzed code)
- `lxml_html_clean`, `python-docx` - Document processing utilities

## Integrations

### Prebuilt: `exa-py.Exa`
- Required Config Section: `EXA`
- Required Keys:
    - `EXA_API_KEY: str` - Exa API authentication key

### Prebuilt: `exa-py.ResearchClient`
- Required Config Section: `EXA`
- Required Keys:
    - `EXA_API_KEY: str` - Exa API authentication key (shared with Exa client)

### Prebuilt: `qurrent.Slack`
- Required Config Section: `SLACK`
- Required Keys:
    - `SLACK_BOT_TOKEN: str` - Slack bot authentication token
    - `SLACK_APP_TOKEN: str` - Slack app-level authentication token
    - `SLACK_CHANNEL_ID: str` - Default channel ID for workflow notifications

### Custom: `HubSpot`
**Location:** `prospecting/api/hubspot.py`
**Type:** One-way (pushes data to HubSpot)

**Config Section:** `HUBSPOT`
- `HUBSPOT_API_KEY: str` - HubSpot private app API key
- `HUBSPOT_PORTAL_ID: str` - HubSpot portal/account ID

**Methods:**

**`keyword_search_companies(keyword: str, limit: int = 100) -> List[dict]`**
- Performs: Fuzzy search companies using HubSpot's CONTAINS_TOKEN operator on name and domain fields
- Behavior:
    - POST to /crm/v3/objects/companies/search with filterGroups for name and domain tokenized matching
    - Returns up to 100 results (default limit)
- Returns: List of dicts with keys: company_id, company_name, domain, company_description, parent_company_id

**`create_company(company_name: str, company_description: str) -> dict`**
- Performs: Create new company record in HubSpot
- Behavior:
    - Uses lock to prevent race conditions
    - Checks if company already exists by name (exact match) before creating
    - Sets is_demo_record="YES" property if not in production mode (ENVIRONMENT != "production")
    - POST to /crm/v3/objects/companies
    - On 409 conflict, refetches existing company
- Returns: HubSpot company object with id and properties

**`update_company(company_id: str, properties: Dict[str, str]) -> dict`**
- Performs: Update existing company properties
- Behavior:
    - Uses lock for update operations
    - GETs company first to check is_demo_record property
    - In non-production mode, only updates records with is_demo_record="YES"
    - PATCH to /crm/v3/objects/companies/{company_id}
- Returns: Updated HubSpot company object

**`associate_parent_company(parent_company_id: str, child_company_id: str) -> dict`**
- Performs: Create parent-to-child company association
- Behavior:
    - Uses lock for association operations
    - POST to /crm/v3/associations/companies/companies/batch/create with type "parent_to_child_company"
    - On 409 conflict, logs "already_exists" and continues
- Returns: API response dict or {"status": "already_exists"}

**`create_or_update_contact(first_name: str, last_name: str, company_id: str, job_title: str, email: Optional[str] = None, linkedin_url: Optional[str] = None) -> dict`**
- Performs: Create or update contact matched by first/last name; ensure company association
- Behavior:
    - Uses lock to prevent race conditions on name-based matching
    - Searches for existing contact by firstname + lastname (exact match)
    - If exists, PATCH with properties that are currently unset (only fills gaps)
    - If new, POST to /crm/v3/objects/contacts with all provided properties
    - Sets is_demo_record="YES" if not in production mode
    - On email conflict (409), drops email field and retries
    - After create/update, PUTs association to /crm/v3/objects/contacts/{contact_id}/associations/companies/{company_id}/1 unless already associated
- Returns: HubSpot contact object with id and properties

**`update_contact(contact_id: str, properties: Dict[str, Any]) -> dict`**
- Performs: Update existing contact properties
- Behavior:
    - Uses lock for update operations
    - GETs contact first to check is_demo_record property
    - In non-production mode, only updates records with is_demo_record="YES"
    - Pre-checks if desired email is already used by another contact; if so, skips email update
    - PATCH to /crm/v3/objects/contacts/{contact_id}
    - On email conflict (400/409), drops email and retries with remaining properties
    - Skips update if contact_id is missing/unknown or contact not found (404)
- Returns: Updated HubSpot contact object or empty dict if skipped

**`is_contact_demo_record(contact_id: str) -> bool`**
- Performs: Check if contact has is_demo_record="YES"
- Behavior:
    - GET to /crm/v3/objects/contacts/{contact_id}?properties=is_demo_record
    - On 404, returns False
- Returns: True if is_demo_record="YES", False otherwise

**`get_recent_contact_emails(contact_id: str, limit: int = 5, start_timestamp: Optional[int] = None, end_timestamp: Optional[int] = None) -> List[Dict[str, Optional[str]]]`**
- Performs: Fetch last N email engagements for contact with body preview
- Behavior:
    - GET to /crm/v3/objects/contacts/{contact_id}/associations/emails to list email IDs
    - Batch read emails via POST to /crm/v3/objects/emails/batch/read (chunks of 100)
    - Extracts properties: hs_email_subject, hs_email_direction, hs_email_from, hs_email_to, hs_email_sent_datetime, hs_email_text, hs_email_html
    - Cleans HTML tags from body, limits preview to 1000 chars
    - Filters by start/end timestamp (epoch milliseconds) if provided
    - Sorts by sent_at descending, returns top N
- Returns: List of dicts with keys: id, subject, direction, from, to, sent_at, body_preview

**`get_contact_email_exchange_stats(contact_id: str, start_timestamp: Optional[int] = None, end_timestamp: Optional[int] = None) -> Dict[str, Union[int, Optional[str]]]`**
- Performs: Return total email count, last exchange date, and current outreach phase for contact
- Behavior:
    - Calls get_contact_email_summary (limit 1) to get last exchange timestamp
    - GET to /crm/v3/objects/contacts/{contact_id}?properties=account_exec_outreach_phase to fetch current phase
- Returns: Dict with keys: total_exchanged (int), last_exchange_at (ISO string or None), account_exec_outreach_phase (str or None)

**`get_contacts_requiring_follow_up() -> List[dict]`**
- Performs: Query contacts due for follow-up today based on account_exec_next_outreach_date property
- Behavior:
    - Calculates today's date in Pacific timezone
    - Converts to UTC midnight boundaries (start and end of day) as epoch milliseconds
    - POST to /crm/v3/objects/contacts/search with filters: account_exec_next_outreach_date GTE start_ms AND LT end_ms
    - Retrieves properties: email, firstname, lastname, account_exec_email_subject, account_exec_email_body, account_exec_next_outreach_date, account_exec_outreach_trigger, account_exec_outreach_phase
    - For each contact, fetches associated company name via /crm/v3/objects/contacts/{contact_id}/associations/companies
- Returns: List of dicts with contact details and company_name

**`delete_demo_records() -> None`**
- Performs: Delete all contacts and companies where is_demo_record="YES"
- Behavior:
    - Uses lock for delete operations
    - Searches for demo records via POST to /crm/v3/objects/{contacts|companies}/search with filter is_demo_record EQ "YES"
    - Deletes each record via DELETE to /crm/v3/objects/{object_type}/{object_id}
    - Paginates through all results (100 per page)
- Returns: None (logs counts of deleted contacts and companies)

### Custom: `HunterIO`
**Location:** `prospecting/api/hunterio.py`
**Type:** One-way (queries Hunter.io)

**Config Section:** `HUNTER_IO`
- `HUNTER_IO_API_KEY: str` - Hunter.io API authentication key

**Methods:**

**`email_finder(domain: str, first_name: str, last_name: str) -> dict`**
- Performs: Find email address for person at company
- Behavior:
    - GET to https://api.hunter.io/v2/email-finder with params: domain, first_name, last_name, api_key
    - Raises for HTTP errors
- Returns: JSON response with data object (email, confidence score)

### Custom: `SendGrid`
**Location:** `prospecting/api/sengrid.py`
**Type:** One-way (sends emails via SendGrid)

**Config Section:** `SENDGRID`
- `SENDGRID_API_KEY: str` - SendGrid API authentication key

**Methods:**

**`send_email(outreach_message: OutreachMessage, from_email: str = "cole@qurrent.ai", from_name: str = "Cole Salquist", bcc_emails: list[str] = ["48618838@bcc.hubspot.com"], is_demo_record: bool = True) -> bool`**
- Performs: Send transactional email via SendGrid with HubSpot BCC tracking
- Behavior:
    - If is_demo_record is True, overrides recipient to "alex@qurrent.ai"
    - Appends cole_email_signature.html to message body
    - Sends as HTML content
    - BCCs 48618838@bcc.hubspot.com for HubSpot email tracking
    - Uses SendGridAPIClient.send(Mail) to transmit
    - Returns True if status code is 200/201/202, False otherwise
- Returns: Boolean success status

### Custom: `Tavily`
**Location:** `prospecting/api/tavily.py`
**Type:** One-way (queries Tavily web search)

**Config Section:** `TAVILY`
- `TAVILY_API_KEY: str` - Tavily API authentication key

**Methods:**

**`search(query: str, max_retries: int = 5, initial_backoff: float = 1.0, backoff_factor: float = 2.0, jitter: float = 0.1) -> list[dict]`**
- Performs: Web search with exponential backoff retry
- Behavior:
    - Wraps TavilyClient.search(query)
    - On exception, retries up to max_retries times
    - Backoff calculation: (initial_backoff * backoff_factor^attempt) + random jitter
    - Sleeps between retries with exponential backoff
    - Raises exception if max retries exceeded
- Returns: List of search result dicts from Tavily

### Custom: `GoogleDriveClient`
**Location:** `prospecting/api/gdrive_utils.py`
**Type:** One-way (reads from Google Drive)

**Config Section:** `GCP`
- `AE_SERVICE_ACCOUNT_JSON: str` - Service account JSON content (from Secret Manager)
- `GOOGLE_APPLICATION_CREDENTIALS: str` - Path to service account JSON file (fallback)

**Methods:**

**`list_files_in_folder(folder_id: str) -> List[Dict]`**
- Performs: List Google Docs in Drive folder
- Behavior:
    - Authenticates with service account credentials (drive.readonly scope)
    - Uses files().list() with query: '{folder_id}' in parents and trashed = false and mimeType = 'application/vnd.google-apps.document'
    - Returns files with fields: id, name, mimeType, size, modifiedTime, createdTime
- Returns: List of file metadata dicts

**`download_file_content(file_id: str) -> str`**
- Performs: Export Google Doc as plain text
- Behavior:
    - GETs file metadata to check mimeType
    - If application/vnd.google-apps.document, uses files().export_media(fileId, mimeType='text/plain')
    - Uses MediaIoBaseDownload to stream content
    - Decodes bytes as UTF-8
    - Raises ValueError for unsupported file types
- Returns: Plain text content of Google Doc

### Custom: `MetricsTracker`
**Location:** `prospecting/metrics.py`
**Type:** One-way (logs to Qurrent Supervisor API)

**Config Section:** `CUSTOMER_KEY_DEV`
- `CUSTOMER_KEY_DEV: str` - API key for Qurrent Supervisor external API

**Methods:**

**`handle_sendgrid_event(event: events.BaseEvent, config: QurrentConfig) -> None`**
- Performs: Process SendGrid webhook events and log metrics to Supervisor API
- Behavior:
    - Extracts event data (single dict or list)
    - For each event: checks event_type (open, bounce, delivered); finds workflow_instance_id for recipient email; checks deduplication via should_log_event(); if should log, POSTs to https://external.qurrent.ai/dev/metrics_data with body: {metric_id: UUID, workflow_instance_id: UUID, measure: 1.0}; records event timestamp in local JSON via record_event()
    - METRIC_MAPPINGS: {"open": "01990cd2-cc11-7902-82c0-d3d9d6f783ca", "bounce": "01990cd3-894d-705a-8295-049f6acd7fff", "delivered": "01990cd3-e918-7ae5-824e-33637e68a892"}
- Returns: None (async function)

### Custom: `SendGridWebhook`
**Location:** `server.py` (WebServer integration)
**Type:** Two-way (receives webhooks from SendGrid)

**Config Section:** None (webhook endpoint configuration)

**Methods:**

**`WebServer.route("/sendgrid-event", methods=[HTTPMethod.POST])`**
- Performs: Listen for SendGrid event webhooks on /sendgrid-event endpoint
- Behavior:
    - Starts WebServer on 0.0.0.0:8000
    - On POST /sendgrid-event: extracts JSON payload; creates SendGridWebhookEvent with workflow_instance_id=-1 and data=payload; adds event to ingress queue via config["INGRESS"].add_event(event); returns Response(status=200)
- Returns: HTTP 200 on success, 400 on invalid payload, 500 on event creation failure

**Custom Events:**
- `SendGridWebhookEvent`:
    - Event type: `"SendGridWebhook"`
    - Required: `workflow_instance_id: UUID | int`, `data: dict | list` (event payload from SendGrid webhook)
