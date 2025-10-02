# Workforce Specification Template

**Contributors:** alex, Alex Reents, augustfr, SamanthQurrentAI, Alex McConville

## Overview
High-level executive-style background summary of the system: describe what it does and how it works.

Blackhawk Marketing Co-Pilot (workflow: GiftCardGuru) is a Microsoft Teams-enabled assistant that produces on-brand, compliant marketing copy for GiftCards.com across channels (ads, blog, email, social) and can enrich content with product-specific details and generated images. A console agent orchestrates a technical agent that follows a strict JSON-response contract and brand rules. The assistant can look up canonical product information from a locally maintained inventory (refreshed daily via a scraper) before linking to products, optionally generate images, and then deliver final content back to Teams while logging business-friendly outputs to the console for observability. The workflow enforces user-specified length targets with a tolerance and gracefully handles timeouts and errors.

## Custom Instructions
*FDE-provided instructions for how this particular workforce specification should be configured*
<!--
[Provide custom instructions here around how to understand and document this particular workforce]
-->

## Decision Audit

Documents the possible paths of workflow execution through the lens of decisions the workforce makes.

- [1] Interpret the user’s marketing request and determine deliverable
    - Inputs: User message in Teams (plain text); brand/voice/compliance rules
    - Outputs: Draft marketing copy and an optional target word count; may include a plan to perform actions (lookups or image generation)
    - Decision logic: Follow brand identity, tone, channel guidance, and JSON-output contract; select channel-appropriate style and structure and set word count if the user specifies one
    - Logic location: internal prompt (technical agent)
- [2] Decide whether links require product lookup
    - Inputs: Draft content that may reference specific gift card products; local product inventory list
    - Outputs: Inclusion or omission of product links; optional action to look up product details
    - Decision logic: Never guess URLs; when linking, first look up each product to retrieve the canonical GiftCards.com purchase URL; omit links for products not found and steer to broad multi-brand alternatives
    - Logic location: internal prompt (technical agent) and internal code (LLM-invoked action to perform lookup)
- [3] Decide whether to generate images
    - Inputs: User request indicating image needs; optional prompt and image count
    - Outputs: Action to generate one or more images and deliver them to the user
    - Decision logic: If requested, generate images based on the prompt; communicate progress and return a short confirmation after delivery
    - Logic location: internal prompt (technical agent) and internal code (LLM-invoked action for image generation)
- [4] Enforce word count requirement
    - Inputs: Final candidate response; user-specified word count (if any)
    - Outputs: Either accept as-is or trigger a rewrite instruction to meet target within ±15%
    - Decision logic: Measure length against tolerance; if too short/long, send a brief warning to the user and return a rewrite instruction that becomes the next input to the agent
    - Logic location: internal code (console agent observable)
- [5] Incorporate results of any actions
    - Inputs: Results from LLM-invoked actions (e.g., lookups, image generation)
    - Outputs: Updated content/logs reflecting action outcomes
    - Decision logic: After actions complete, gather rerun results and merge any user-visible outcomes into the message to send and into observability logs
    - Logic location: internal code (console agent observable)
- [6] Decide what to send to the user
    - Inputs: Final message string; accumulated observable output
    - Outputs: Message posted to Teams; business-context log saved to console
    - Decision logic: If there is non-empty content, send it to Teams and persist an observable output record for stakeholders
    - Logic location: internal code (console agent observable)
- [7] Decide when to end the conversation
    - Inputs: Ingress events providing subsequent user messages; sentinel text "end"
    - Outputs: Conversation termination and unlinking from the Teams thread
    - Decision logic: If the next ingress message equals "end" (case-insensitive), send a closure notice and end the workflow
    - Logic location: internal code (workflow run loop)
- [8] Notify on inactivity timeout
    - Inputs: Elapsed time since workflow start (15 minutes)
    - Outputs: Timeout notification to the user and workflow completion
    - Decision logic: If the workflow exceeds the timeout without completion, send a user-facing timeout message and close
    - Logic location: internal code (workflow wrapper)
- [9] Notify on unexpected failure
    - Inputs: Runtime exception
    - Outputs: Generic, user-friendly error message; failure recorded in console; workflow closure
    - Decision logic: Catch unhandled exceptions, inform the user without exposing internal details, and close the workflow
    - Logic location: internal code (workflow wrapper)
- [10] Refresh product inventory daily
    - Inputs: Wall clock time (8:00 AM PST); GiftCards.com product listings
    - Outputs: Updated local product inventory file for use in lookups
    - Decision logic: At the scheduled time, fetch and normalize product data from the source and persist to JSON for the assistant’s use
    - Logic location: internal code (scheduled task)

## Data & Formats

### Referenced Documents Inventory and Input Data
*Excluding mentions of specific PII, financial information, or other sensitive details*

- Gift card product inventory
    - Format: JSON
    - Source: Scraped from GiftCards.com product listings via GraphQL and HTML parsing
    - Intended Use: Power product lookups for canonical URLs, descriptions, and amount options
- Teams message events
    - Format: Plain text (message body) with metadata (conversation id)
    - Source: Microsoft Teams ingress via Qurrent OS
    - Intended Use: Primary user input that initiates and drives conversation turns
- PLP API responses (category product listings)
    - Format: JSON
    - Source: GiftCards.com GraphQL endpoint
    - Intended Use: Normalize and enrich product inventory (amounts, availability, descriptions)

### Example Output Artifacts

- User-facing response message
    - Type: Message
    - Format: Plain text (may include Markdown links)
    - Recipients: Requesting user/channel in Microsoft Teams
    - Contents: Channel-appropriate marketing copy (ads, blog, email, social) adhering to brand, tone, and compliance rules
- Generated image asset
    - Type: Image delivered via message
    - Format: PNG hosted at a public or signed URL
    - Recipients: Requesting user/channel in Microsoft Teams
    - Contents: Image generated from a user-specified prompt
- Console observable log
    - Type: Observability record
    - Format: Text entry
    - Recipients: Stakeholders via The Supervisor console
    - Contents: Business-friendly transcript of what was sent/produced

## Integration Summary

**Integrations:**
[List integrations that connect to actual services:]
- **Microsoft Teams (Qurrent Teams)**: Bi-directional messaging; links workflow instances to Teams conversations; delivers progress and final outputs.
- **GiftCards.com GraphQL + HTML**: Product listing data for inventory build/enrichment (names, URLs, amounts, availability, descriptions).
- **OpenAI Images**: Generates one or more images from a text prompt.
- **Google Cloud Storage**: Stores generated image bytes and returns a public or time-limited URL.

## Directory Structure

GiftCardGuru/

## Agents

### Console Agents

#### `assistant`
**Type:** Console Agent (method with `@console_agent` decorator)
**Purpose:** Entry point for handling user input from Teams and orchestrating technical agent responses
**Docstring:** "Main assistant agent responsible for handling user input"

**Observable Tasks:**

**`handle_user_input()`**
- `@observable` decorator
- Docstring: "Handling a request from the user"
- Purpose: Append the user message to the technical agent’s thread, invoke the agent for a JSON response, run any actions and incorporate their results, enforce word count tolerance, send the final message to Teams, and log an observable output
- Technical Agent Calls: Calls `assistant_agent()` for the main LLM turn; calls `assistant_agent.get_rerun_responses()` to accumulate results from LLM-invoked actions
- Integration Calls: Calls `teams.send_message()` to send user-visible updates and results
- Observability Output: `save_to_console(type='observable_output', content="<business-friendly transcript>")`
- Returns: Optionally returns a rewrite instruction string that becomes the next agent input when word count is out of tolerance; otherwise returns `None`

### Technical Agents

#### `Assistant`
**Type:** Technical Agent (extends `Agent` class)
**Pattern:** Task
**Purpose:** Generate brand-compliant marketing copy; optionally perform lookups for canonical product links and generate images before finalizing the response
**LLM:** gemini/gemini-2.5-flash (primary), gpt-5 (fallback), standard mode, temp=0, timeout=120s

**Prompt Strategy:**
- Role: Creative-but-precise GiftCards.com marketing writer; adhere to brand identity, tone, and compliance guardrails
- Link policy: Before inserting any product link, look up the product to fetch the canonical URL; omit links for unavailable products
- Output discipline: Return a single JSON object with keys `response` (string), `word_count` (string or empty), and optional `actions` list
- Actions are optional and mutually exclusive with responding in the same turn (do not write a response while taking actions)
- Context: Substitutes a dynamic inventory list of all active gift card names for internal reference during generation
- JSON Response: Example shape `{ "response": "...", "word_count": "", "actions": [ { "name": "...", "args": { ... } } ] }`

**Instance Attributes:**
- `teams: Teams` - messaging integration used for user-visible updates
- `conversation_id: str` - Teams conversation to post progress/results
- `openai: OpenAI` - client used for image generation
- `product_inventory: Dict[str, Dict]` - normalized product data used for lookups

**Create Parameters:**
- `yaml_config_path: str` - path to the agent configuration and prompt
- `workflow_instance_id: UUID` - current workflow instance identifier
- `teams: Teams` - Teams integration instance
- `conversation_id: str` - current Teams conversation id
- `product_inventory_file: str` - JSON filename to load as product inventory

#### Direct Actions

**`LLM turn (invocation)() -> Dict`**
- Purpose: Produce a single-turn JSON response following the configured system prompt
- Message Thread modification:
    - Appends the latest user message from the console agent
- Integration usage:
    - None directly (actions are invoked separately by the LLM)
- Returns: JSON object with `response`, optional `word_count`, and optional `actions`
- Side Effects: None beyond message-thread updates

#### LLM Callables

**`lookup_gift_card(card_name: str) -> (str | Dict)`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Docstring Args: `card_name (str): The name of the gift card to lookup.`
- Purpose: Retrieve amount options, description, and canonical GiftCards.com URL for a named product; informs the user that a lookup is in progress
- Integration usage:
    - Calls `teams.send_message()` to post a progress update
- Returns: Product dictionary if found; otherwise a short not-found message
- Manual Message Thread: Result is appended and used on the next rerun

**`generate_image(prompt: str, num_images: int = 1) -> str`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Docstring Args: `prompt (str): Prompt for the image generation`; `num_images (int): Number of images to generate`
- Purpose: Generate one or more images, upload to storage, and post them to the Teams thread
- Integration usage:
    - Calls `teams.send_message()` to report progress and then deliver the image(s)
- Subagent/Util usage:
    - Uses OpenAI Images to generate bytes; uses storage utility to upload bytes to cloud storage and obtain a URL
- Returns: A short confirmation string indicating the image(s) were delivered
- Side Effects: Image asset(s) uploaded to storage; public or signed URLs created and posted

## Happy Path Call Stack

**Note:** Clearly indicate which agents are Technical Agents (TA) vs Console Agents (CA) in the call stack.

```text
→ START EVENT: events.TeamsMessage "<user asks for specific marketing copy>"
  ├─ @console_agent: GiftCardGuru.assistant()
  │  └─ @observable: GiftCardGuru.handle_user_input()
  │     ├─ Assistant() [TA LLM turn]
  │     │  ├─ @llmcallable: Assistant.lookup_gift_card()
  │     │  │  └─ teams.send_message() → progress update
  │     │  └─ @llmcallable: Assistant.generate_image()
  │     │     ├─ OpenAI Images → image bytes
  │     │     ├─ storage.upload_bytes_to_gcs() → public/signed URL
  │     │     └─ teams.send_message() → image delivered
  │     ├─ teams.send_message() → final copy (with links if applicable)
  │     └─ save_to_console(type='observable_output')
→ INGRESS EVENT: events.TeamsMessage "end"
  └─ @console_agent: GiftCardGuru.assistant()
     └─ teams.send_message() → "Conversation ended."

→ WORKFLOW COMPLETE: On explicit "end", timeout, or after handling errors
```

## Utils

**`scraper.fetch_html(url: str, query: dict, session: requests.Session | None) -> str`**
- Purpose: Retrieve HTML content for a given URL using realistic headers
- Implementation: Requests session with browser-like headers; returns text content
- Dependencies: `requests`, `brotli`, `zstandard`

**`scraper.fetch_all_plp_items(session: requests.Session, html_text: str) -> list[dict]`**
- Purpose: Collect product listing data across pages via GiftCards.com GraphQL
- Implementation: Uses a captured GraphQL operation and paginates by reading `total_pages` hints in HTML, then POSTs per page
- Dependencies: `requests`

**`scraper.normalize_plp_items_to_products(plp_items: list[dict]) -> list[dict]`**
- Purpose: Convert PLP items into normalized products (name, amounts, description, URL, availability)
- Implementation: Extracts fields from items and composes product dictionaries
- Dependencies: `beautifulsoup4`

**`scraper.save_products_to_json(products: list[dict], file_name: str) -> None`**
- Purpose: Persist normalized products as a de-duplicated name-keyed JSON object
- Implementation: Writes to `data/<file_name>` ensuring parent directory exists
- Dependencies: `json`

**`scraper.scrape_giftcards_com(file_name: str) -> None`**
- Purpose: End-to-end scrape to refresh product inventory from GiftCards.com
- Implementation: Fetches HTML, queries PLP GraphQL pages, normalizes/merges, writes JSON
- Dependencies: `requests`, `beautifulsoup4`, `json`

**`storage.upload_bytes_to_gcs(object_path: str, data: bytes, content_type: str = "application/octet-stream", bucket_name: Optional[str] = None, make_public: bool = True) -> str`**
- Purpose: Upload bytes to Google Cloud Storage and return a public or signed URL
- Implementation: Ensures bucket and prefix exist; uploads; attempts to make public; falls back to a time-limited signed URL
- Dependencies: `google-cloud-storage`

## Integrations

### Prebuilt: `qurrent.Teams`
- Required Config Section: root config
- Required Keys:
    - `MICROSOFT_TEAMS_WEBHOOK_URL: str` - Teams webhook endpoint used to start and post messages
    - `INGRESS: object` - Provides `get_start_event()` for obtaining start events

### Custom: None
**Location:** N/A
**Type:** N/A

**Config Section:** N/A
- N/A

**Methods:**

N/A

**Custom Events:**
- N/A
