# Workforce Specification: GiftCardGuru - Marketing Co-Pilot

**Contributors:** alex, Alex Reents, augustfr, SamanthQurrentAI, Alex McConville

## Overview

GiftCardGuru is an AI-powered marketing co-pilot for Blackhawk Network's GiftCards.com brand. The workforce operates as a conversational assistant via Microsoft Teams, helping marketing professionals craft persuasive, compliant, and conversion-optimized copy for gift card campaigns across multiple marketing channels (performance ads, blog posts, email, social media). 

The system maintains a continuously updated catalog of 400+ gift card products (scraped daily from GiftCards.com) and can generate branded marketing copy that follows strict brand guidelines, compliance rules, and channel-specific best practices. The assistant can look up specific gift card details, generate promotional images using AI, and validate copy against word count requirements - automatically revising content until it meets specifications.

The workflow runs continuously in a 15-minute session, accepting iterative user input through Teams chat. A background scheduler refreshes the product inventory daily at 8:00 AM PST to ensure marketing recommendations reflect current product availability.

## Custom Instructions
*FDE-provided instructions for how this particular workforce specification should be configured*
<!--
This workforce is a production marketing co-pilot for Blackhawk Network. The assistant's brand voice and compliance guardrails are strictly defined in the system prompt and should not be loosened. When documenting this workforce, pay special attention to:
- The brand voice requirements (GiftCards.com naming, no superlatives, no emojis)
- Compliance guardrails (age-appropriate framing, factual claims only)
- Word count validation loop behavior (up to 15% tolerance)
- Product lookup mandate before linking
-->

## Decision Audit

Documents the possible paths of workflow execution through the lens of decisions the workforce makes.

- [1] Accept or Reject Incoming Teams Message
    - Inputs: Teams message event with conversation_id and message content
    - Outputs: Either starts new GiftCardGuru workflow instance or ignores message
    - Decision logic: Automatically accepts all Teams messages that match the configured ingress pattern and creates a new workflow session
    - Logic location: internal code (event handler in main loop)

- [2] Determine Response Type (Direct Response vs. Action Required)
    - Inputs: User's marketing request (e.g., "Write a blog post for Mother's Day" or "Look up Starbucks gift card")
    - Outputs: Either immediate text response or action invocation (lookup_gift_card or generate_image)
    - Decision logic: Assistant agent analyzes user request and determines if it needs to gather information via actions before responding, or can respond directly with marketing copy. Always looks up products before linking them. Generates images when user requests visual content.
    - Logic location: internal prompt (Assistant agent system prompt)

- [3] Select Marketing Channel Format
    - Inputs: User's specification of channel (ad, blog, email, social) or implied from context
    - Outputs: Copy formatted according to channel-specific guidelines (length, structure, tone, CTA placement)
    - Decision logic: Assistant matches the request to one of four channel types and applies corresponding rules: Performance Ads (ultra-concise, single CTA), Blog Posts (structured with subheads, 5+ reasons, scannable), Email (compact, benefit-led subject line), Social Taglines (5+ one-liners, may include puns). Default is concise unless blog or specific verbosity requested.
    - Logic location: internal prompt (Assistant agent system prompt sections on Channel Guidance and Verbosity Control)

- [4] Choose Gift Card Products to Recommend
    - Inputs: Occasion context from user request, product inventory with 400+ gift cards
    - Outputs: Curated list of 5-10 specific gift card products with mix of multi-brand and single-brand options
    - Decision logic: Assistant prioritizes multi-brand cards (One4all, Cheers To You, Home Sweet Home) for versatility, then adds distinct single-brand options mapped to recipient personas (gamers, outdoor enthusiasts, beauty fans, coffee lovers, etc.). Selection must logically fit the occasion. If no products fit, recommends a broad multi-brand alternative.
    - Logic location: internal prompt (Assistant agent system prompt sections on Product Selection Principles and Persona Coverage)

- [5] Lookup Gift Card Details
    - Inputs: Card name string
    - Outputs: Product details (amounts, description, canonical GiftCards.com URL) or "Product not found" message, status message sent to Teams
    - Decision logic: When Assistant decides to include a product link in copy, it must first invoke lookup_gift_card action to retrieve the canonical URL. Checks product_inventory dictionary loaded from JSON file. If found returns product data, if not found returns error message.
    - Logic location: internal code (Assistant.lookup_gift_card method), triggered by Assistant agent decision to link products

- [6] Apply Brand Voice and Compliance Rules
    - Inputs: Draft marketing copy generated by Assistant
    - Outputs: Copy that adheres to brand guidelines (GiftCards.com spelling, no superlatives, no emojis, warm but professional tone)
    - Decision logic: Assistant applies multiple compliance filters during generation: exact brand spelling (GiftCards.com with camel case and .com), no superlatives ("best", "perfect", "#1"), no unverifiable claims, age-appropriate framing for alcohol/gaming content, no stereotypes, only states features explicitly provided, uses concrete nouns and strong verbs, no hashtags or emojis or exclamation stacks.
    - Logic location: internal prompt (Assistant agent system prompt sections on Compliance & Risk Guardrails, Brand Identity & Naming, Core Voice & Tone)

- [7] Generate Promotional Images
    - Inputs: Image prompt description and number of images to generate
    - Outputs: Generated image(s) uploaded to GCS and displayed in Teams as HTML img tags, confirmation message
    - Decision logic: When user requests images or Assistant determines visual content would enhance the marketing copy, invokes generate_image action. Uses OpenAI gpt-image-1 model to create 1024x1024 images based on prompt. Uploads each image to Google Cloud Storage in images/ folder with UUID filename, makes public, and sends public URL to Teams chat embedded as img tag.
    - Logic location: internal code (Assistant.generate_image method), triggered by Assistant agent decision to create visuals

- [8] Check Word Count Requirements
    - Inputs: Generated marketing copy text, target word count specified by user (if any)
    - Outputs: Either accepts copy as meeting requirement, or feedback message with specific word adjustment needed (e.g., "add 250 more words" or "reduce by 100 words")
    - Decision logic: If user specifies word count (e.g., "1500 word blog post"), Assistant includes word_count key in JSON response. Workflow calculates actual word count and checks if it falls within 15% tolerance (±15% of target). If too short, returns instruction to lengthen by specific amount. If too long, returns instruction to shorten. If within range or no word count specified, accepts copy.
    - Logic location: internal code (GiftCardGuru.word_count_exceeded method)

- [9] Retry Copy Generation for Word Count
    - Inputs: Feedback about word count shortfall/excess, all prior conversation context
    - Outputs: Revised marketing copy attempting to meet word count target, warning message sent to Teams
    - Decision logic: When word_count_exceeded returns feedback, workflow sends warning message to Teams ("Rewriting response to meet N ± 15% word count requirement"), then returns feedback to Assistant agent as new user message. Assistant reruns with full context including the word count instruction. This loops until word count is met or Assistant gives up (sets word_count to empty string after many failed attempts).
    - Logic location: internal code (GiftCardGuru.handle_user_input main loop) and internal prompt (Assistant agent receives word count feedback as user message)

- [10] Execute LLM-Invoked Actions
    - Inputs: Actions array from Assistant's JSON response containing action names and arguments
    - Outputs: Action results appended to message thread, new Agent execution with updated context
    - Decision logic: When Assistant's response includes actions array, workflow calls assistant_agent.get_rerun_responses which executes each action (lookup_gift_card or generate_image), appends results to message thread (via @llmcallable with rerun_agent=True), and reruns the Assistant with updated context. Assistant then generates final response incorporating action results.
    - Logic location: internal code (GiftCardGuru.handle_user_input checking for response.get("actions")), coordinated with internal prompt (Assistant agent system prompt specifying JSON format with optional actions array)

- [11] Send Response to Teams
    - Inputs: Final marketing copy response (potentially including multiple pieces from action reruns), conversation_id
    - Outputs: Message posted to Teams chat, saved to console observable output
    - Decision logic: Formats response (if dict with multiple keys, formats as "**key:**\nvalue" for each key; otherwise treats as string). Sends non-empty responses via Teams webhook. Accumulates all response content (including intermediate action responses) as observable_output for console logging.
    - Logic location: internal code (GiftCardGuru._stringify formatting, Teams.send_message, save_to_console calls)

- [12] Continue or End Conversation
    - Inputs: User's next message in ongoing conversation or explicit "end" command
    - Outputs: Either processes next request (loops back to decision 2) or ends workflow with goodbye message
    - Decision logic: After sending response, workflow loops waiting for next Teams message via ingress.get_workflow_event. If user sends "end" (case-insensitive), sends "Conversation ended." message and terminates workflow. Otherwise treats new message as next request and continues conversation. Workflow automatically times out after 15 minutes of inactivity.
    - Logic location: internal code (GiftCardGuru.run main loop checking for "end" message)

- [13] Handle Workflow Timeout
    - Inputs: 15-minute inactivity timer expiration
    - Outputs: Timeout notification message to Teams, workflow closed with "completed" status
    - Decision logic: Workflow execution wrapped in asyncio.wait_for with 15-minute timeout (900 seconds). If no user messages received within timeout period, raises TimeoutError. Error handler sends "The workflow has ended after 15 minutes of inactivity." message to Teams and closes workflow gracefully with completed status.
    - Logic location: internal code (handle_event timeout wrapper and exception handling)

- [14] Handle Workflow Errors
    - Inputs: Unexpected exceptions during workflow execution
    - Outputs: Generic error message to Teams, error logged to console, workflow closed with "failed" status
    - Decision logic: All workflow execution wrapped in try-except. On any unhandled exception, sends user-friendly message "The workflow failed unexpectedly. The Qurrent team has been notified. In the meantime, please try again." to Teams, logs full error with traceback to console, closes workflow with failed status, and unlinks Teams conversation.
    - Logic location: internal code (handle_event exception handling)

- [15] Schedule Daily Product Scrape
    - Inputs: Current time in PST timezone
    - Outputs: Updated product inventory JSON file, next scheduled scrape time
    - Decision logic: Background task calculates seconds until next 8:00 AM PST. If current time is already past 8:00 AM today, schedules for 8:00 AM tomorrow. Sleeps until target time, then executes scrape_giftcards_com utility to fetch latest products from GiftCards.com and save to giftcards_com_products.json. On completion or error, continues loop to schedule next day's scrape.
    - Logic location: internal code (schedule_daily_scrape function running as spawned background task)

- [16] Scrape GiftCards.com Product Catalog
    - Inputs: GiftCards.com brands page URL
    - Outputs: JSON file containing all active products with names, amounts, descriptions, URLs, and stock status
    - Decision logic: Creates HTTP session with realistic browser headers, fetches HTML from brands listing page, parses initial page to determine total pages, then makes GraphQL requests to fetch all product pages (40 items per page). For each product, extracts name, available amounts, description, URL, and inventory status. Normalizes data and saves as dictionary with product names as keys to giftcards_com_products.json in data/ directory.
    - Logic location: internal code (scrape_giftcards_com utility function in utils/scraper.py)

## Data & Formats

### Referenced Documents Inventory and Input Data

- **Product Inventory JSON (giftcards_com_products.json)**
    - Format: JSON dictionary with product names as keys
    - Source: Daily automated scrape from GiftCards.com public website
    - Intended Use: Loaded into Assistant agent on creation, product names list substituted into system prompt, individual products looked up during action execution
    - Contents: Each product contains:
        - name (string): Gift card product name
        - amounts (array of floats): Available denomination amounts in USD
        - description (string): Product description for marketing context
        - url (string): Canonical GiftCards.com product page URL
        - out_of_stock (boolean): Inventory availability status

- **Assistant Configuration (agents/config/assistant.yaml)**
    - Format: YAML
    - Source: Version-controlled configuration file
    - Intended Use: Defines LLM settings and complete system prompt for Assistant agent
    - Contents:
        - LLM model configuration (gemini/gemini-2.5-flash primary, gpt-5 fallback, temperature 0, 120s timeout)
        - Comprehensive system prompt covering brand identity, voice/tone, compliance rules, channel guidance, product selection principles, linking requirements, output format requirements

- **Configuration Secrets (config.yaml)**
    - Format: YAML (generated at runtime from GCP Secret Manager)
    - Source: Three secrets fetched from GCP: customer_keys, llm_keys, additional_keys
    - Intended Use: Provides API keys and configuration for integrations
    - Contents: API keys for Anthropic, OpenAI, Microsoft Teams webhook URL, GCS bucket configuration (keys visible, values excluded per security requirements)

- **Ingress Registry (ingress_registry.json)**
    - Format: JSON
    - Source: Qurrent OS workflow registration
    - Intended Use: Maps Teams conversation IDs to workflow instances for message routing

- **GCS Credentials (gha-creds-*.json)**
    - Format: JSON service account key
    - Source: GitHub Actions or deployment environment
    - Intended Use: Authenticates Google Cloud Storage operations for image uploads

### Example Output Artifacts

- **Marketing Copy (Text)**
    - Type: Conversational message response
    - Format: Plain text or light Markdown (headings, lists when requested)
    - Recipients: Marketing professional via Teams chat
    - Contents: Occasion-specific gift card marketing copy following channel guidelines (ads: ultra-concise with single CTA; blogs: structured with title, intro, 5+ reasons, scannable subheads, multiple product links; email: compact with benefit-led subject line; social: 5+ standalone one-liners). Always uses exact "GiftCards.com" spelling, no superlatives, warm but professional tone, concrete benefits tied to the occasion.

- **Product Recommendations (Structured)**
    - Type: Curated selection embedded in marketing copy
    - Format: Text with Markdown links [Product Name](URL)
    - Recipients: Marketing professional via Teams chat
    - Contents: Mix of 5-10 multi-brand and single-brand gift cards chosen for occasion fit. Multi-brand cards (One4all, Cheers To You, Home Sweet Home, Fun & Fabulous) recommended for versatility. Single-brand cards cover distinct personas (Starbucks for coffee, Xbox for gamers, REI for outdoors, Ulta Beauty for beauty fans, DoorDash for dining). Each product link uses canonical URL retrieved via lookup_gift_card action.

- **Promotional Images (Visual)**
    - Type: AI-generated marketing visual
    - Format: PNG image (1024x1024 pixels)
    - Recipients: Marketing professional via Teams chat (embedded as img tag)
    - Contents: OpenAI-generated image based on user-provided prompt or Assistant-crafted prompt. Uploaded to Google Cloud Storage with public URL, displayed inline in Teams message.

- **Word Count Feedback (Validation Message)**
    - Type: Iterative revision instruction
    - Format: Plain text message
    - Recipients: Internal to Assistant agent (appended as user message), user sees warning message in Teams
    - Contents: Specific instruction like "Your response has 850 words but needs 1500. Lengthen your response by approximately 650 more words." Used to guide Assistant's next revision attempt.

- **Status Updates (Progress Indicators)**
    - Type: Ephemeral notification
    - Format: Italic text in Teams (e.g., "_Looking up more details about Starbucks..._" or "_Generating an image..._")
    - Recipients: Marketing professional via Teams chat
    - Contents: Real-time updates when actions are executing to provide feedback that the system is working

- **Observable Output (Audit Log)**
    - Type: Workflow execution log
    - Format: Text content saved to Qurrent console
    - Recipients: Workflow operators/administrators via Qurrent dashboard
    - Contents: Complete transcript of all responses sent to user, including intermediate action results and word count warnings. Used for debugging and quality assurance.

## Integration Summary

**Integrations:**
- **Microsoft Teams (Prebuilt: qurrent.Teams)**: Two-way conversational interface enabling marketing professionals to send requests and receive marketing copy, status updates, and generated images. Links workflow instances to conversation IDs, sends messages via webhook, receives messages via ingress events (TeamsMessage). Supports rich formatting including Markdown links and embedded HTML images.

- **Google Cloud Storage (Custom: google-cloud-storage library)**: One-way storage for generated promotional images. Creates/manages GCS buckets (blackhawk_{environment}), uploads image bytes with public access, returns public URLs for embedding in Teams messages. Includes folder structure support (images/ prefix).

- **OpenAI Images API (Custom: openai.OpenAI.images.generate)**: One-way image generation service. Uses gpt-image-1 model to create 1024x1024 images from text prompts, returns base64-encoded PNG data. Invoked by Assistant agent via generate_image action.

- **GiftCards.com Website (Custom: HTTP scraping via requests/BeautifulSoup)**: One-way data source for product catalog. Daily scrape fetches HTML from brands page, extracts structured JSON-LD and GraphQL data to build comprehensive product inventory. Parses product names, amounts, descriptions, URLs, and stock status. No authentication required (public website).

- **GCP Secret Manager (Custom: google.cloud.secretmanager)**: One-way secret retrieval at startup. Fetches three secrets (customer_keys, llm_keys, additional_keys) from configured GCP project using Application Default Credentials. Secrets parsed as YAML and written to config.yaml for Qurrent OS configuration loading. Used only during initialization.

## Directory Structure
```
blackhawk-pilot/
├── agents/
│   ├── assistant.py          # Assistant agent implementation (Task Agent pattern)
│   └── config/
│       └── assistant.yaml     # LLM config and comprehensive system prompt
├── utils/
│   ├── scraper.py            # GiftCards.com product catalog scraper
│   └── storage.py            # GCS upload utilities for image storage
├── data/
│   └── giftcards_com_products.json  # Product inventory (400+ gift cards)
├── blackhawk.py              # Main workflow orchestration and event handling
├── load_secrets.py           # GCP Secret Manager integration for config
├── requirements.txt          # Python dependencies
├── pyproject.toml            # Project metadata
├── docker-compose.yaml       # Local development container config
├── Dockerfile                # Production container definition
├── startup.sh                # Container entrypoint (loads secrets, runs workflow)
├── ingress_registry.json     # Workflow-to-Teams conversation mapping
└── README.md                 # Basic setup instructions
```

## Agents

### `Assistant`
**Pattern:** Task Agent
**Purpose:** Generates marketing copy for gift card campaigns across multiple channels (ads, blogs, email, social). Maintains strict brand voice, compliance guardrails, and channel-specific formatting. Can lookup product details and generate promotional images on demand. Operates in thinking-disabled mode for direct text generation without visible reasoning.

**LLM:** gemini/gemini-2.5-flash (primary), gpt-5 (fallback), temperature=0, timeout=120 seconds, standard mode (no extended thinking)

**Prompt Strategy:**
- Extensive system prompt (200+ lines) covering brand identity, voice/tone, compliance rules, channel guidance, product selection principles, and output format requirements
- Key rules: Always spell brand as "GiftCards.com", no superlatives, no emojis/hashtags, warm but professional tone, occasion-first persuasion, concrete benefits over generic claims
- Compliance: Age-appropriate framing, no unverifiable claims, only state provided features, inclusive and respectful language
- Channel formats: Ultra-concise for ads, structured/scannable for blogs, compact for email, 5+ one-liners for social
- Product linking: MUST invoke lookup_gift_card action before inserting any product URL, use Markdown link syntax only
- Context: Accumulates across conversation turns within 15-minute session
- JSON Response: `{"response": "<marketing_copy_string>", "word_count": "<user_specified_count_or_empty>", "actions": [{"name": "lookup_gift_card|generate_image", "args": {...}}]}`
- Self-review checklist: Occasion drives angle, concrete reasons, balanced product mix (multi-brand + single-brand), facts match brief, tone/mechanics comply, single CTA

**Instance Attributes:**
- `teams: Teams` - Microsoft Teams integration for sending status updates
- `conversation_id: str` - Teams conversation ID for routing messages
- `openai: OpenAI` - OpenAI client for image generation API
- `product_inventory: Dict[str, Dict]` - In-memory product catalog loaded from JSON (product name → product details)

**Create Parameters:**
- `yaml_config_path: str` - Path to assistant.yaml configuration ("./agents/config/assistant.yaml")
- `workflow_instance_id: UUID` - Unique ID of parent GiftCardGuru workflow instance
- `teams: Teams` - Shared Teams integration instance
- `conversation_id: str` - Teams conversation ID for this session
- `product_inventory_file: str` - JSON filename in data/ directory ("giftcards_com_products.json")

#### Direct Actions

None. Assistant agent is invoked directly by workflow via `await self.assistant_agent()` which triggers LLM execution. Does not have workflow-callable action methods.

#### LLM Callables

**`lookup_gift_card(card_name: str) -> Union[str, Dict]`**
- `@llmcallable(rerun_agent=True, append_result=True)` - Results automatically appended to message thread, agent reruns with updated context
- Docstring Args: `card_name (str): The name of the gift card to lookup.`
- Purpose: Retrieves detailed product information (amounts, description, canonical URL) for a specific gift card to enable accurate product linking in marketing copy
- Integration usage:
    - Calls `self.teams.send_message(self.conversation_id, ...)` to send status message "_Looking up more details about {card_name}..._"
- Returns: Product dictionary from inventory with keys {name, amounts, description, url, out_of_stock}, or error string "Product {card_name} not found" if not in inventory
- Manual Message Thread: None (append_result=True handles automatically)
- Error Handling: No explicit try/except, returns "Product not found" string when dict lookup fails

**`generate_image(prompt: str, num_images: int = 1) -> str`**
- `@llmcallable(rerun_agent=True, append_result=True)` - Results automatically appended to message thread, agent reruns with updated context
- Docstring Args: `prompt (str): A prompt for the image generation. num_images (int): The number of images to generate.`
- Purpose: Creates promotional images using OpenAI's image generation API and uploads them to GCS for display in Teams
- Integration usage:
    - Calls `self.teams.send_message(self.conversation_id, ...)` to send progress message "_Generating an image..._" or "_Generating {num_images} images..._"
    - Calls `self.openai.images.generate(model="gpt-image-1", prompt=prompt, n=num_images, size="1024x1024")` to generate images, returns base64 JSON response
    - Calls `upload_bytes_to_gcs(object_path=f"images/{uuid.uuid4()}.png", data=image_bytes, content_type="image/png")` from utils/storage to upload and get public URL
    - Calls `self.teams.send_message(self.conversation_id, ...)` to send HTML img tag with public URL
- Returns: String "The image has been generated and sent to the user. Do not respond wth anything else." to inform LLM the task is complete and suppress further output
- Manual Message Thread: None (append_result=True handles automatically)
- Error Handling: None explicit, would propagate exceptions to workflow error handler

## YAML Configuration

### Credentials used -- provide keys, not values

**CUSTOMER_KEY_DEV** - Retrieved from GCP Secret Manager secret "customer_keys"

**LLM_KEYS** - Retrieved from GCP Secret Manager secret "llm_keys":
- ANTHROPIC_API_KEY
- OPENAI_API_KEY

**ADDITIONAL_KEYS** - Retrieved from GCP Secret Manager secret "additional_keys":
- MICROSOFT_TEAMS_WEBHOOK_URL - Webhook endpoint for sending Teams messages
- GCS_BUCKET_NAME - Google Cloud Storage bucket name (default: blackhawk_{environment})
- GOOGLE_CLOUD_PROJECT - GCP project ID for Secret Manager and GCS operations
- ENVIRONMENT - Deployment environment (development/production)

**INGRESS** - Qurrent OS ingress configuration for receiving Teams events (configured automatically)

## Utils

**`utils/scraper.scrape_giftcards_com(file_name: str) -> None`**
- Purpose: Scrapes complete product catalog from GiftCards.com and saves to JSON file
- Implementation: Creates HTTP session with browser headers, fetches brands page HTML, parses initial page to determine total pages from embedded JSON, makes GraphQL POST requests to fetch all product pages (40 items per page), extracts product data from JSON responses (name, amounts from variants.product.giftcard_amounts, description from short_description.html, url from url_key, out_of_stock from !has_inventory), normalizes to list of dicts, converts to dict with product names as keys, writes to data/{file_name}
- Dependencies: requests, beautifulsoup4, brotli, zstandard (for decoding compressed responses)

**`utils/scraper.fetch_html(url: str, query: dict, session: requests.Session | None) -> str`**
- Purpose: HTTP GET request with realistic browser headers
- Implementation: Creates/uses session with headers (accept, user-agent, referer, sec-ch-ua, etc.), performs GET with params and 30s timeout, returns decoded HTML text
- Dependencies: requests

**`utils/scraper.extract_plp_items(html_text: str) -> list[dict]`**
- Purpose: Extracts product items from embedded PLP (Product Listing Page) JSON in HTML
- Implementation: Uses regex to find "products": { patterns, extracts balanced JSON objects, parses as JSON, collects items arrays from each products object
- Dependencies: json, re, beautifulsoup4

**`utils/scraper.graphql_fetch_plp_page(session: requests.Session, page_index: int, page_size: int, category_key: str) -> dict`**
- Purpose: Fetches single page of products via GiftCards.com GraphQL API
- Implementation: POST to https://www.giftcards.com/commerce/graphql with PLP query, variables {categoryKey: "brands", pageSize: "40", pageIndex: N}, GraphQL-specific headers (store, operation-type, caller-id, x-datadome-clientid), returns parsed JSON response
- Dependencies: requests

**`utils/scraper.normalize_plp_items_to_products(plp_items: list[dict]) -> list[dict]`**
- Purpose: Transforms GraphQL response items into normalized product dictionaries
- Implementation: For each item, constructs URL from url_key, extracts description from short_description.html using BeautifulSoup, extracts amounts from variants[].product.giftcard_amounts[], determines out_of_stock from !check_inventory_availability, returns list with standardized keys
- Dependencies: beautifulsoup4

**`utils/scraper.save_products_to_json(products: list[dict], file_name: str) -> None`**
- Purpose: Saves product list to JSON file as name-keyed dictionary
- Implementation: Creates data/ directory if needed, converts list to dict using product name as key (strips whitespace, skips products without names), writes to data/{file_name} with indent=2 and ensure_ascii=False for readability
- Dependencies: json, pathlib

**`utils/storage.upload_bytes_to_gcs(object_path: str, data: bytes, content_type: str, bucket_name: Optional[str], make_public: bool) -> str`**
- Purpose: Uploads bytes to Google Cloud Storage and returns public or signed URL
- Implementation: Gets or creates bucket (defaults to blackhawk_{environment}), ensures prefix exists if object_path contains /, uploads data to blob with specified content_type, attempts to make_public if flag set (returns public_url on success), falls back to generate_signed_url (24 hours) if ACLs restricted
- Dependencies: google-cloud-storage==2.x

**`utils/storage.get_or_create_bucket(bucket_name: Optional[str]) -> storage.Bucket`**
- Purpose: Returns existing GCS bucket or creates it if missing
- Implementation: Creates storage.Client, looks up bucket by name (defaults to GCS_BUCKET_NAME env var or blackhawk_{environment}), returns if exists, otherwise creates new bucket with default settings
- Dependencies: google-cloud-storage==2.x

**`load_secrets.fetch_secret(project_id: str, secret_name: str) -> str`**
- Purpose: Fetches latest version of secret from GCP Secret Manager
- Implementation: Creates SecretManagerServiceClient, accesses secret at projects/{project_id}/secrets/{secret_name}/versions/latest using Application Default Credentials, decodes UTF-8 payload, returns string content
- Dependencies: google-cloud-secretmanager

**`load_secrets.parse_and_export_yaml(yaml_content: str) -> Dict[str, str]`**
- Purpose: Parses YAML string and exports key-value pairs as environment variables
- Implementation: Attempts yaml.safe_load, flattens dict to export simple types as env vars, also parses line-by-line for "key: value" format as fallback, logs each exported variable, returns dict of exported vars
- Dependencies: pyyaml

## Dependencies

- `qurrent>=0.9` - Qurrent OS framework (Workflow, Agent, Teams, events, decorators)
- `uvloop` - High-performance event loop for asyncio
- `loguru` - Structured logging
- `openai` - OpenAI API client for image generation (gpt-image-1 model)
- `google-cloud-storage` - GCS client for uploading generated images
- `google-cloud-secretmanager` - Secret Manager client for loading configuration
- `pyyaml` - YAML parsing for configuration files
- `requests` - HTTP client for web scraping
- `beautifulsoup4` - HTML parsing for product catalog scraping
- `brotli` - Brotli compression support for HTTP responses
- `zstandard` - Zstandard compression support for HTTP responses
- `lxml_html_clean` - HTML sanitization utilities
- `fuzzywuzzy` - Fuzzy string matching (installed but not actively used in current code)
- `sendgrid` - Email service client (installed but not actively used in current code)
- `replicate` - Replicate AI API client (installed but not actively used in current code)
- `pandas` - Data manipulation library (installed but not actively used in current code)
- `openpyxl` - Excel file support for pandas (installed but not actively used in current code)

## Integrations

### Prebuilt: `qurrent.Teams`
- Required Config Section: `MICROSOFT_TEAMS`
- Required Keys:
    - `MICROSOFT_TEAMS_WEBHOOK_URL: string (HTTPS URL)` - Webhook endpoint for posting messages to Teams channel

**Methods Used:**
- `Teams.start(qconfig, webhook_endpoint)` - Initializes Teams integration with webhook URL
- `teams.link(workflow_instance_id: UUID, conversation_id: str)` - Associates workflow instance with Teams conversation for message routing
- `teams.unlink(conversation_id: str)` - Removes workflow-conversation association when session ends
- `teams.send_message(conversation_id: str, message: str)` - Posts message to specified Teams conversation

### Custom: Google Cloud Storage (via google-cloud-storage library)
**Location:** `utils/storage.py`
**Type:** One-way (write-only)

**Config Section:** Environment Variables
- `GCS_BUCKET_NAME: string` - Bucket name (defaults to blackhawk_{environment} if not set)
- `GOOGLE_CLOUD_PROJECT: string` - GCP project ID for authentication
- `ENVIRONMENT: string` - Deployment environment (development/production/etc)

**Authentication:** Uses Application Default Credentials (ADC) from environment. In container deployment, expects service account credentials JSON at path specified by GOOGLE_APPLICATION_CREDENTIALS env var or via GCP metadata service.

**Methods:**

**`upload_bytes_to_gcs(object_path: str, data: bytes, content_type: str = "application/octet-stream", bucket_name: Optional[str] = None, make_public: bool = True) -> str`**
- Performs: Uploads byte data to GCS at specified path, optionally makes public, returns URL
- Behavior:
    - Gets or creates bucket using bucket_name or default
    - Ensures parent prefix exists as zero-byte directory placeholder if object_path contains /
    - Uploads data to blob with specified content_type
    - Attempts blob.make_public() if make_public=True
    - Returns blob.public_url if public access succeeds
    - Falls back to blob.generate_signed_url(24 hours) if public ACLs restricted
- Returns: String URL (public or signed) for accessing the uploaded object

**`get_or_create_bucket(bucket_name: Optional[str] = None) -> storage.Bucket`**
- Performs: Returns existing bucket or creates new one
- Behavior:
    - Uses bucket_name param or calls _get_default_bucket_name() to compute blackhawk_{environment}
    - Calls client.lookup_bucket() to check existence
    - Returns existing bucket if found
    - Creates new bucket with client.create_bucket() if not found
- Returns: storage.Bucket object

### Custom: OpenAI Images API (via openai library)
**Location:** `agents/assistant.py` (Assistant.generate_image method)
**Type:** One-way (request-response)

**Config Section:** LLM_KEYS
- `OPENAI_API_KEY: string` - API key for OpenAI service

**Authentication:** OpenAI client instantiated without explicit key parameter, automatically reads OPENAI_API_KEY from environment

**Methods:**

**`openai.images.generate(model: str, prompt: str, n: int, size: str) -> ImagesResponse`**
- Performs: Generates images from text prompt using OpenAI DALL-E style models
- Parameters:
    - model: "gpt-image-1" (OpenAI's image generation model identifier)
    - prompt: Text description of desired image
    - n: Number of images to generate (typically 1)
    - size: Image dimensions ("1024x1024")
- Returns: ImagesResponse object with data[].b64_json containing base64-encoded PNG images

### Custom: GiftCards.com Web Scraper (via requests/BeautifulSoup)
**Location:** `utils/scraper.py`
**Type:** One-way (read-only)

**Config Section:** None (uses public website, no authentication)

**Data Output:** Writes to data/giftcards_com_products.json

**Methods:**

**`scrape_giftcards_com(file_name: str = "giftcards_com_products.json") -> None`**
- Performs: Complete product catalog scrape workflow
- Behavior:
    - Creates HTTP session with realistic browser headers (user-agent, sec-ch-ua, referer, etc.)
    - Fetches https://www.giftcards.com/us/en/catalog/brands with query param srsltid
    - Parses HTML to determine total_pages from embedded PLP JSON
    - Loops page_index from 1 to total_pages, makes GraphQL POST to /commerce/graphql for each page
    - Aggregates all product items from GraphQL responses
    - Normalizes items to standardized product dicts (name, amounts, description, url, out_of_stock)
    - Converts list to dict with product names as keys
    - Writes to data/{file_name} as formatted JSON (indent=2, UTF-8)
- Error Handling: Catches exceptions per-page (logs error, continues to next page), catches top-level exception (logs error, scrape fails)

**`graphql_fetch_plp_page(session: requests.Session, page_index: int, page_size: int = 40, category_key: str = "brands") -> dict`**
- Performs: Single GraphQL query for one page of products
- GraphQL Query: PLP query requesting categories, products, variants, giftcard_amounts, inventory, descriptions, sales_rules
- Headers: store: "gift_cards_us_en", operation-type: "bhn-gift_cards_us_en--category-getPLPData", caller-id: "UI-gift_cards_us_en-1.1.0-Andor-WebApp-GC", x-datadome-clientid: (anti-bot token)
- Returns: Parsed JSON with nested structure data.categories.items[0].products.items[] containing product objects

### Custom: GCP Secret Manager (via google-cloud-secretmanager library)
**Location:** `load_secrets.py`
**Type:** One-way (read-only, startup-only)

**Config Section:** Environment Variables
- `GOOGLE_CLOUD_PROJECT: string` - GCP project ID containing secrets

**Authentication:** Uses Application Default Credentials (ADC)

**Secrets Fetched:**
- customer_keys - Customer-specific configuration keys
- llm_keys - LLM provider API keys (ANTHROPIC_API_KEY, OPENAI_API_KEY)
- additional_keys - Other service keys (Teams webhook, GCS bucket name)

**Methods:**

**`fetch_secret(project_id: str, secret_name: str) -> str`**
- Performs: Retrieves latest version of named secret
- Behavior:
    - Creates SecretManagerServiceClient using ADC
    - Accesses projects/{project_id}/secrets/{secret_name}/versions/latest
    - Decodes payload as UTF-8 string
    - Logs success/failure
- Returns: Secret content as string (expected to be YAML format)

**`parse_and_export_yaml(yaml_content: str) -> Dict[str, str]`**
- Performs: Parses YAML string and exports as environment variables
- Behavior:
    - Attempts yaml.safe_load() to parse as structured YAML
    - Flattens dict, exports simple types (str/int/float/bool) as os.environ entries
    - Falls back to line-by-line "key: value" parsing if YAML parse fails
    - Logs each exported variable name (not value)
- Returns: Dictionary of exported variable names and values

**Script Execution (load_secrets.py main()):**
- Resets config.yaml to empty file
- Fetches customer_keys, llm_keys, additional_keys in sequence
- For each secret: fetches content, parses/exports as env vars, appends raw content to config.yaml
- Exits with error code 1 if GOOGLE_CLOUD_PROJECT not set or any secret fetch fails
- Called by startup.sh before running blackhawk.py

## Feasibility & Consistency Analysis

### Call Stack Validation

The workflow execution follows a valid call chain:

1. **Startup**: `startup.sh` → `load_secrets.py` (fetches secrets, creates config.yaml) → `blackhawk.py` main()
2. **Initialization**: `main()` creates QurrentConfig from config.yaml → `Teams.start()` → spawns `schedule_daily_scrape()` background task → enters event loop
3. **Event Handling**: Ingress receives TeamsMessage event → `handle_event()` spawned as task → `GiftCardGuru.create()` loads Assistant agent with product inventory → `blackhawk_workflow.run()` starts conversation loop
4. **Conversation Flow**: User message → `assistant()` console agent wrapper → `handle_user_input()` appends to thread → `assistant_agent()` LLM call → returns JSON response
5. **Action Execution**: If actions present → `assistant_agent.get_rerun_responses()` executes each action (@llmcallable methods) → reruns agent with results → final response
6. **Word Count Loop**: `word_count_exceeded()` checks if needed → if fails, returns feedback → feedback appended as user message → loops back to step 4
7. **Response Delivery**: `_stringify()` formats response → `teams.send_message()` posts to Teams → `save_to_console()` logs → loops back to wait for next message
8. **Termination**: User sends "end" → goodbye message → workflow.close("completed") → teams.unlink()

All method signatures match call sites. Agent returns are correctly consumed (JSON dict with "response", "word_count", "actions" keys).

### Input/Output Continuity

- **Product Data Flow**: scraper writes JSON → Assistant.create() reads JSON into product_inventory dict → lookup_gift_card() accesses dict by name → returns product dict to LLM → LLM uses URL in response
- **Action Results**: @llmcallable methods return strings/dicts → automatically appended to message_thread by decorator → next LLM call sees results in context
- **Word Count Feedback**: word_count_exceeded() returns string → appended as user message → Assistant receives in next turn with full context
- **Image Upload**: generate_image() receives base64 from OpenAI → decodes to bytes → passes to upload_bytes_to_gcs() → returns URL string → sends to Teams → returns completion message to LLM
- **Configuration**: load_secrets appends YAML to config.yaml → QurrentConfig.from_file() loads → Teams initialized with webhook URL → Assistant gets Teams instance via create() parameter

No mismatches found. File IDs not used (everything uses content directly). All data shapes consistent.

### Approval Gates & External Sends

- **No Approval Gates**: Workflow sends all Assistant responses directly to Teams without human approval. Status messages and final copy posted immediately.
- **External Sends**: All Teams messages sent via `teams.send_message()` which POSTs to webhook URL. No batching or confirmation prompts. Images embedded directly in messages.
- **Storage Writes**: Generated images automatically uploaded to GCS and made public without confirmation.
- **Audit Trail**: All responses logged to console via `save_to_console(type="observable_output")` for later review.

### Potential Issues & Gaps

**Strengths:**
- Clean separation between orchestration (GiftCardGuru) and task execution (Assistant)
- Comprehensive system prompt with extensive brand/compliance rules
- Word count validation loop ensures quality control
- Product lookup mandate prevents broken links
- Timeout and error handling prevent zombie workflows
- Daily scraper keeps data fresh

**Potential Concerns:**
1. **No Action Result Validation**: If lookup_gift_card returns "Product not found", LLM sees error message but may still attempt to use invalid data. No explicit error recovery flow.
2. **Image Generation Failures**: No try/except in generate_image(). OpenAI API failures would propagate to workflow error handler, sending generic error message. User wouldn't know specific issue.
3. **Word Count Loop Could Hang**: No explicit limit on word count retries. If Assistant repeatedly fails to meet count, loops until timeout (15 min). Sets word_count to empty string "after many attempts" but "many" is not defined programmatically.
4. **Scraper Resilience**: Daily scraper catches per-page errors but has no retry logic. If all GraphQL pages fail, products file unchanged from previous day. No alert on stale data.
5. **No Rate Limiting**: High-frequency user messages could trigger many concurrent LLM calls and image generations. No throttling or queue management.
6. **Product Inventory Substitution**: System prompt includes `{product_inventory}` variable with product names list. If inventory very large (400+ products), prompt could become very long and expensive. Current implementation loads all names as space-separated string.
7. **Unused Dependencies**: Several packages installed but not imported/used in code (fuzzywuzzy, sendgrid, replicate, pandas, openpyxl). May indicate planned features or legacy cruft.

**Data Completeness:**
All required data present for happy path. Product inventory exists and is refreshed daily. API keys loaded from secrets. Teams webhook configured. No identified gaps in critical data flows.

---

*This specification documents the GiftCardGuru workforce as implemented in commit history through the analyzed codebase. No logic has been invented or assumed beyond what is explicitly present in code and configuration.*
