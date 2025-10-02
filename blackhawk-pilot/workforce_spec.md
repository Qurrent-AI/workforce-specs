# Workforce Specification: GiftCardGuru

**Contributors:** alex, Alex Reents, augustfr, SamanthQurrentAI, Alex McConville

## Overview

GiftCardGuru is an AI-powered marketing co-pilot for Blackhawk Network/GiftCards.com that helps marketers create persuasive, compliant, and conversion-oriented copy across multiple channels (performance ads, blogs, email, social media). The system is designed to produce occasion-based marketing content that drives gift card purchases by targeting specific upcoming moments (Back to School, Father's Day, Teacher Appreciation, etc.).

The workflow operates as an interactive conversational system where users request specific marketing content through Microsoft Teams. The AI assistant analyzes the request, can look up specific gift card products from a daily-refreshed inventory of 400+ brands on GiftCards.com, and generates tailored marketing copy that follows strict brand guidelines and compliance requirements. The system can also generate supporting images when needed.

The system maintains brand consistency by enforcing specific voice and tone guidelines, ensuring factual accuracy, avoiding superlatives and unverifiable claims, and properly linking to canonical product URLs. It automatically validates word count requirements and will iteratively refine content until it meets specified length targets.

## Custom Instructions
*FDE-provided instructions for how this particular workforce specification should be configured*
<!--
This workforce is designed as a marketing content generation system for GiftCards.com. The agent is configured with extensive brand guidelines, compliance rules, and content formatting requirements in its system prompt. When documenting or modifying this workforce:

1. The system prompt in assistant.yaml contains critical brand identity rules (GiftCards.com spelling, voice/tone, compliance guardrails) that should not be modified without stakeholder approval
2. The product inventory is refreshed daily at 8:00 AM PST via automated web scraping - this timing is important for marketing campaign planning
3. Word count validation uses a 15% tolerance (WORD_COUNT_TOLERANCE constant) and will force rewrites if content is outside this range
4. The assistant must always look up products before linking to ensure canonical URLs are used
5. The workflow times out after 15 minutes of inactivity to manage resource usage
-->

## Path Audit

Defines the possible paths for workflow execution.

### Agent Architecture

**Core Agent Responsibilities:**
- **Functions**: The workforce employs a single LLM-powered assistant agent that handles all marketing content generation tasks
    - **Assistant Agent**: Receives user requests via Teams, interprets marketing content needs, generates compliant copy following brand guidelines, looks up product details when needed, generates supporting images, and delivers formatted content back to the user
        - **What**: Creates marketing copy (ads, blog posts, emails, social content) for specific occasions
        - **When**: Triggered by any user message in Microsoft Teams
        - **Why**: Enables marketers to rapidly produce on-brand, compliant content without manual research or brand guideline lookups
    - **Daily Scraper Task**: Runs automatically at 8:00 AM PST to refresh the product inventory
        - **What**: Scrapes GiftCards.com catalog to update product names, amounts, descriptions, URLs, and availability
        - **When**: Every day at 8:00 AM Pacific time
        - **Why**: Ensures the assistant has current product information for accurate recommendations and linking

- **User Touchpoints**: 
    - Initial request submission via Microsoft Teams message
    - Real-time status updates during action execution (e.g., "_Looking up more details about [card name]..._", "_Generating an image..._")
    - Word count validation warnings when content needs to be rewritten
    - Final delivery of completed marketing content via Teams
    - Conversation termination (user can end conversation by sending "end")

### Decision Ledger

1. **Route incoming Teams message to workflow**
    - Inputs: TeamsMessage event containing conversation_id and user message
    - Outputs: New GiftCardGuru workflow instance created and linked to conversation
    - Decision logic: Every new Teams message starts a fresh workflow instance that handles the conversation until timeout or explicit end command
    - Logic location: Internal code (handle_event function in blackhawk.py)

2. **Initialize conversation context with product inventory**
    - Inputs: Product inventory JSON file (giftcards_com_products.json), conversation_id
    - Outputs: Assistant agent instantiated with product names loaded into system prompt context
    - Decision logic: Load all product names (400+ gift cards) from JSON file and inject into the assistant's system prompt as available inventory
    - Logic location: Internal code (Assistant.create method)

3. **Parse user request for marketing content type and requirements**
    - Inputs: User message text
    - Outputs: JSON response with "response" field (generated content), optional "word_count" field (target length), optional "actions" array
    - Decision logic: LLM analyzes user request to determine content type (ad, blog, email, social), occasion, tone, length requirements, and whether additional product lookups or images are needed
    - Logic location: Internal prompt (assistant system prompt in assistant.yaml)

4. **Determine if product lookup is needed**
    - Inputs: User request mentioning specific gift card brands or requesting product recommendations
    - Outputs: Decision to invoke lookup_gift_card action or proceed without lookup
    - Decision logic: If user asks about specific cards, wants recommendations, or needs product URLs for linking, the LLM triggers lookup_gift_card action(s) for relevant products
    - Logic location: Internal prompt (assistant system prompt instructs to look up cards before linking)

5. **Look up specific gift card details**
    - Inputs: card_name (gift card product name)
    - Outputs: Product details including amounts, description, canonical URL, stock status; or "Product {card_name} not found" message
    - Decision logic: Direct dictionary lookup in loaded product inventory; if key exists return full product data, otherwise return not found message
    - Logic location: Internal code (lookup_gift_card method in assistant.py, triggered via LLM action)
    - Dependencies: Requires product inventory JSON file to be loaded during initialization

6. **Determine if image generation is needed**
    - Inputs: User request asking for visual content, graphics, or images
    - Outputs: Decision to invoke generate_image action or proceed without image
    - Decision logic: If user explicitly requests image(s) or visual content to accompany marketing copy, LLM triggers generate_image action with appropriate prompt and quantity
    - Logic location: Internal prompt (assistant determines when images add value to deliverable)

7. **Generate marketing image**
    - Inputs: prompt (description of image to generate), num_images (quantity, default 1)
    - Outputs: Public URL of generated image uploaded to Google Cloud Storage
    - Decision logic: Call OpenAI GPT-image-1 API with prompt, receive base64 image data, upload to GCS bucket as PNG, make public, return URL embedded in Teams message
    - Logic location: Internal code (generate_image method in assistant.py, triggered via LLM action)

8. **Wait for action execution and rerun agent**
    - Inputs: Actions array from initial LLM response
    - Outputs: Results from each action execution (product details, image URLs, etc.)
    - Decision logic: If actions array is present in LLM response, execute each action sequentially (lookup_gift_card or generate_image), gather results, then rerun agent with action results appended to thread
    - Logic location: Internal code (get_rerun_responses in qurrent framework, called from handle_user_input)

9. **Generate final marketing content with action results**
    - Inputs: Original user request, action results (product data, image URLs) now in message thread
    - Outputs: JSON response with completed marketing copy in "response" field
    - Decision logic: LLM synthesizes action results into final marketing content following brand guidelines (occasion-first persuasion, compliance rules, proper linking, voice/tone)
    - Logic location: Internal prompt (assistant system prompt with extensive brand and channel guidance)

10. **Format response for delivery**
    - Inputs: LLM response object (may be string or dict with multiple keys like "subject" and "body")
    - Outputs: Single formatted string for Teams message
    - Decision logic: If response is dict, format as "**key:**\nvalue" sections separated by blank lines; if string, use as-is
    - Logic location: Internal code (_stringify method in blackhawk.py)

11. **Check if word count target is specified**
    - Inputs: LLM response with "word_count" field
    - Outputs: Decision to validate word count or skip validation
    - Decision logic: If "word_count" field is present and non-empty in LLM response, proceed to word count validation; otherwise skip
    - Logic location: Internal code (handle_user_input checks response.get("word_count"))

12. **Validate content meets word count requirement**
    - Inputs: Generated content text, target word count from LLM response
    - Outputs: Approval to send content, or word count error message to rerun agent
    - Decision logic: Count words in generated text; if within ±15% of target word count, approve; if too short or too long, return error message with specific instruction to lengthen/shorten by approximate number of words
    - Logic location: Internal code (word_count_exceeded method in blackhawk.py)

13. **Rewrite content to meet word count**
    - Inputs: Word count error message (e.g., "Your response has 450 words but needs 1500. Lengthen your response by approximately 1050 more words.")
    - Outputs: Revised content meeting word count target
    - Decision logic: Send warning message to user about rewrite, append word count error to message thread, rerun assistant to generate longer/shorter version
    - Logic location: Internal code (handle_user_input returns error message to trigger rerun) + Internal prompt (assistant receives word count feedback)

14. **Deliver final content to user**
    - Inputs: Approved marketing content (word count validated if applicable)
    - Outputs: Teams message with completed content, console log of observable output
    - Decision logic: Send formatted message to Teams conversation, save full output to Qurrent console for audit/debugging
    - Logic location: Internal code (teams.send_message and save_to_console calls)

15. **Determine if conversation should continue**
    - Inputs: Current user message
    - Outputs: Decision to wait for next message, end conversation, or timeout
    - Decision logic: If user sends "end", terminate workflow with completion message; otherwise wait up to 15 minutes for next message; if 15 minutes elapse with no message, timeout and close workflow
    - Logic location: Internal code (run method while loop with timeout in handle_event)

16. **Handle timeout or completion**
    - Inputs: Workflow state (timeout exception or normal completion)
    - Outputs: Workflow closed with status "completed" or "failed", Teams conversation unlinked
    - Decision logic: On timeout after 15 minutes, send timeout notice to user and close with "completed" status; on exception, send error message and close with "failed" status; on normal end command, close with "completed" status
    - Logic location: Internal code (handle_event exception handling and finally block)

17. **Schedule and execute daily product scrape**
    - Inputs: Current time (PST), target time (8:00 AM PST)
    - Outputs: Updated product inventory JSON file
    - Decision logic: Calculate seconds until next 8:00 AM PST, sleep until then, scrape GiftCards.com catalog via GraphQL API and HTML parsing, save products to JSON
    - Logic location: Internal code (schedule_daily_scrape function and scrape_giftcards_com utility)

## Data & Formats

### Referenced Documents Inventory and Input Data

- **giftcards_com_products.json**
    - Format: JSON dictionary with product names as keys
    - Source: Daily automated scrape from GiftCards.com website
    - Intended Use: Product lookup during marketing content generation; product names injected into assistant system prompt as available inventory
    - Contents: For each gift card product:
        - `name`: Gift card product name (e.g., "Starbucks", "One4all")
        - `amounts`: Array of available denominations (e.g., [25.0, 50.0, 100.0])
        - `description`: Marketing description of the card and its uses
        - `url`: Canonical product page URL on GiftCards.com
        - `out_of_stock`: Boolean availability status

- **assistant.yaml**
    - Format: YAML configuration file
    - Source: Static configuration in repository
    - Intended Use: Defines LLM model settings and system prompt for Assistant agent
    - Contents:
        - LLM configuration (model: gemini/gemini-2.5-flash, temperature: 0, timeout: 120s, fallback: gpt-5)
        - Comprehensive system prompt with brand identity rules, voice/tone guidelines, compliance guardrails, channel-specific guidance, product selection principles, and output format requirements

- **config.yaml**
    - Format: YAML configuration file
    - Source: Generated at runtime from GCP Secret Manager secrets
    - Intended Use: Runtime configuration for integrations and API keys
    - Contents: LLM API keys, Microsoft Teams webhook URL, GCS bucket configuration, Qurrent OS settings

### Example Output Artifacts

- **Performance Ad Copy**
    - Type: Marketing copy
    - Format: Plain text or structured fields (headline, description, CTA)
    - Recipients: Marketing team via Teams
    - Contents: Ultra-concise copy with one clear benefit, occasion relevance, persona coverage, single CTA

- **Blog Post**
    - Type: Long-form marketing content
    - Format: Markdown with headings, lists, inline product links
    - Recipients: Marketing team via Teams
    - Contents: Title, introduction, ~5 occasion-specific reasons to buy, diverse recipient scenarios, product links using canonical URLs, call-to-action

- **Email Copy**
    - Type: Email marketing content
    - Format: Structured text (subject line + body) or single body
    - Recipients: Marketing team via Teams
    - Contents: Compact, skimmable email with subject line (benefit-led, no superlatives), short paragraphs, product mentions, single CTA

- **Social Media Taglines**
    - Type: Social media copy
    - Format: Plain text list (5+ one-liners)
    - Recipients: Marketing team via Teams
    - Contents: At least 5 standalone one-liners (no emojis/hashtags), each tying occasion to benefit, may include light brand-appropriate puns

- **Generated Marketing Images**
    - Type: Visual asset
    - Format: PNG image (1024x1024)
    - Recipients: Embedded in Teams message as HTML img tag
    - Contents: AI-generated image based on prompt, stored in Google Cloud Storage with public URL

- **Console Logs**
    - Type: Audit trail
    - Format: JSON observability events
    - Recipients: Qurrent OS console (for debugging/monitoring)
    - Contents: Full observable_output from each interaction, error messages, workflow status

## Integration Summary

**Integrations:**
- **Microsoft Teams (qurrent.Teams)**: Two-way integration for receiving user messages and sending responses. Links workflow instances to conversation threads. Receives TeamsMessage events to trigger workflows. Sends formatted marketing content, status updates, and warnings back to users.

- **OpenAI API**: Image generation integration via OpenAI client. Uses GPT-image-1 model to generate 1024x1024 images from text prompts. Returns base64-encoded image data that is uploaded to cloud storage.

- **Google Cloud Storage**: Artifact storage integration for generated images. Creates/retrieves GCS buckets (default: `blackhawk_{environment}`), uploads image bytes with public URLs or signed URLs (24hr expiry), organizes images under `images/` prefix.

- **Google Cloud Secret Manager**: Configuration management integration via load_secrets.py. Fetches secrets (`customer_keys`, `llm_keys`, `additional_keys`) from GCP Secret Manager at startup and assembles config.yaml with API keys and integration settings.

- **Qurrent OS Ingress**: Event routing integration. Receives TeamsMessage events from Microsoft Teams, routes to workflow instances, maintains ingress registry for deduplication/tracking.

- **Qurrent OS Console**: Observability integration. Logs observable outputs, errors, and workflow status for debugging and audit purposes.

## Directory Structure
```
blackhawk-pilot/
├── agents/
│   ├── assistant.py              # Assistant agent implementation
│   └── config/
│       └── assistant.yaml        # Agent configuration and system prompt
├── utils/
│   ├── scraper.py                # GiftCards.com product scraper
│   └── storage.py                # Google Cloud Storage utilities
├── data/
│   └── giftcards_com_products.json  # Product inventory (updated daily)
├── blackhawk.py                  # Main workflow and orchestration
├── load_secrets.py               # Secret management from GCP
├── startup.sh                    # Container entrypoint
├── requirements.txt              # Python dependencies
├── pyproject.toml                # Project metadata
├── Dockerfile                    # Container build configuration
├── docker-compose.yaml           # Local development setup
└── ingress_registry.json         # Event routing state
```

## Agents

### `Assistant`
**Pattern:** Task Agent with LLM Callables
**Purpose:** Generate marketing copy for GiftCards.com across multiple channels (ads, blogs, email, social media) following strict brand guidelines and compliance requirements. The agent interprets user requests, looks up product details when needed, generates images, and produces compliant, conversion-oriented content.

**LLM:** gemini/gemini-2.5-flash, standard mode, temp=0, timeout=120 seconds
**Fallback Model:** gpt-5

**Prompt Strategy:**
- Extensive brand identity and voice/tone guidelines embedded in system prompt
- Occasion-first persuasion framework (lead with the moment/event, tie benefits to timing)
- Strict compliance guardrails (no superlatives, no unverifiable claims, age-appropriate framing, inclusive language)
- Channel-specific formatting rules (performance ads: ultra-concise; blogs: scannable with subheads; email: compact; social: standalone one-liners)
- Product selection principles (prioritize multi-brand cards for versatility, include distinct single-brand options)
- Mandatory product lookup before linking to obtain canonical URLs
- Context: Accumulates throughout conversation (product lookups and image generation results appended to thread)
- JSON Response: `{"response": "<generated_content_string>", "word_count": "" or "<target_count>", "actions": [{"name": "lookup_gift_card", "args": {"card_name": "Starbucks"}}, {"name": "generate_image", "args": {"prompt": "...", "num_images": 1}}]}`

**Instance Attributes:**
- `teams: Teams` - Microsoft Teams integration instance for sending messages
- `conversation_id: str` - Teams conversation thread identifier
- `openai: OpenAI` - OpenAI API client for image generation
- `product_inventory: Dict[str, Dict]` - Loaded gift card product catalog (keys are product names)

**Create Parameters:**
- `yaml_config_path: str` - Path to assistant.yaml configuration file
- `workflow_instance_id: UUID` - Unique identifier for this workflow instance
- `teams: Teams` - Teams integration passed from workflow
- `conversation_id: str` - Teams conversation to send messages to
- `product_inventory_file: str` - Filename of product JSON in data/ directory (default: "giftcards_com_products.json")

#### Direct Actions

None. This agent only exposes LLM-callable actions and relies on the workflow to call its run method.

#### LLM Callables

**`lookup_gift_card(card_name: str) -> Union[str, Dict]`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Docstring Args: `card_name (str): The name of the gift card to lookup.`
- Purpose: Retrieve detailed product information (amounts, description, URL) for a specific gift card from the loaded inventory
- Integration usage:
    - Calls `self.teams.send_message()` to send status message "_Looking up more details about {card_name}..._" to user
- Returns: Full product dictionary from inventory (with keys: name, amounts, description, url, out_of_stock) if found; string "Product {card_name} not found" if not in inventory
- Manual Message Thread: Result automatically appended to thread via append_result=True
- Error Handling: No explicit try/except; returns "not found" message if key missing from dictionary

**`generate_image(prompt: str, num_images: int = 1) -> str`**
- `@llmcallable(rerun_agent=True, append_result=True)`
- Docstring Args: 
    - `prompt (str): A prompt for the image generation.`
    - `num_images (int): The number of images to generate.`
- Purpose: Generate AI images for marketing content using OpenAI API and upload to cloud storage
- Integration usage:
    - Calls `self.teams.send_message()` to send status "_Generating {num_images} image(s)..._"
    - Calls `self.openai.images.generate()` with model="gpt-image-1", n=num_images, size="1024x1024"
    - Calls `upload_bytes_to_gcs()` utility to upload image to GCS and get public URL
    - Calls `self.teams.send_message()` to send HTML img tag with public URL
- Returns: String message "The image has been generated and sent to the user. Do not respond with anything else."
- Manual Message Thread: Result automatically appended to thread via append_result=True
- Error Handling: No explicit try/except; errors would propagate to caller

## YAML Configuration
*Credentials used -- provide keys, not values*

**Secret Manager Secrets (fetched via load_secrets.py):**
- customer_keys (secret name in GCP Secret Manager)
- llm_keys (secret name in GCP Secret Manager)
- additional_keys (secret name in GCP Secret Manager)

**LLM_KEYS:**
- ANTHROPIC_API_KEY
- OPENAI_API_KEY

**MICROSOFT_TEAMS:**
- MICROSOFT_TEAMS_WEBHOOK_URL

**GOOGLE_CLOUD:**
- GOOGLE_CLOUD_PROJECT (environment variable for GCP project ID)
- GCS_BUCKET_NAME (optional; defaults to `blackhawk_{environment}`)

**QURRENT_OS:**
- QURRENT_DATA_DIR (data directory path for workflow state)
- INGRESS (Qurrent ingress configuration for event routing)

**ENVIRONMENT:**
- ENVIRONMENT (development/staging/production; affects default bucket naming)

## Utils

**`scraper.scrape_giftcards_com(file_name: str = "giftcards_com_products.json") -> None`**
- Purpose: Scrape the complete GiftCards.com product catalog and save to JSON file
- Implementation: 
    1. Fetch initial HTML from GiftCards.com /catalog/brands page with realistic browser headers
    2. Parse HTML to extract total page count from embedded JSON-LD data
    3. Iterate through all pages using GraphQL API (PLP query) to fetch product items
    4. Extract product data: name, available amounts (from giftcard_amounts), description (from short_description.html), canonical URL (from url_key), inventory availability
    5. Normalize products to standardized format and save as JSON dictionary with product names as keys
- Dependencies: 
    - `requests` for HTTP requests
    - `beautifulsoup4` (lxml_html_clean) for HTML parsing
    - `loguru` for logging

**`scraper.create_session() -> requests.Session`**
- Purpose: Create HTTP session with realistic browser headers to avoid bot detection
- Implementation: Initialize requests.Session with headers mimicking Chrome on macOS (user-agent, accept headers, sec-ch-ua, referer, etc.)
- Dependencies: `requests`

**`scraper.fetch_html(url: str, query: dict, session: requests.Session | None = None) -> str`**
- Purpose: Fetch HTML content from URL with query parameters
- Implementation: Perform GET request with session, raise on error, return response text
- Dependencies: `requests`

**`scraper.graphql_fetch_plp_page(session: requests.Session, page_index: int, page_size: int = 40, category_key: str = "brands") -> dict`**
- Purpose: Fetch one page of product data from GiftCards.com GraphQL API
- Implementation: POST to /commerce/graphql endpoint with PLP query (includes product details, variants, giftcard amounts, inventory status), parse JSON response
- Dependencies: `requests`

**`scraper.normalize_plp_items_to_products(plp_items: list[dict]) -> list[dict]`**
- Purpose: Transform raw GraphQL response items into standardized product format
- Implementation: Extract name, amounts from variants, description from short_description.html, construct canonical URL, check inventory availability
- Dependencies: `beautifulsoup4` for HTML text normalization

**`scraper.save_products_to_json(products: list[dict], file_name: str) -> None`**
- Purpose: Save products to JSON file in data/ directory as dictionary with product names as keys
- Implementation: Create data/ directory if needed, convert product list to dictionary keyed by name, write JSON with indentation
- Dependencies: `json`, `pathlib`

**`storage.upload_bytes_to_gcs(object_path: str, data: bytes, *, content_type: str = "application/octet-stream", bucket_name: Optional[str] = None, make_public: bool = True) -> str`**
- Purpose: Upload bytes to Google Cloud Storage and return public or signed URL
- Implementation: 
    1. Get or create GCS bucket (defaults to `blackhawk_{environment}`)
    2. Ensure prefix (folder) exists by creating placeholder object if needed
    3. Upload bytes as blob with specified content type
    4. Attempt to make public and return public_url; on failure (uniform bucket-level access) generate 24-hour signed URL
- Dependencies: `google-cloud-storage`

**`storage.get_or_create_bucket(bucket_name: Optional[str] = None) -> storage.Bucket`**
- Purpose: Return existing GCS bucket or create it if it doesn't exist
- Implementation: Use GCS client to lookup bucket by name; if not found, create new bucket
- Dependencies: `google-cloud-storage`

**`storage._get_environment() -> str`**
- Purpose: Get current environment name from environment variable
- Implementation: Read ENVIRONMENT env var, default to "development", return lowercase
- Dependencies: `os`

**`storage._get_default_bucket_name() -> str`**
- Purpose: Construct default GCS bucket name based on environment
- Implementation: Return GCS_BUCKET_NAME env var if set, otherwise format as `blackhawk_{environment}`
- Dependencies: `os`

## Dependencies

**Core Framework:**
- `qurrent` (version from base image 0.9) - Qurrent OS framework providing Workflow, Agent, Teams, events, decorators (@console_agent, @observable, @llmcallable)

**LLM & AI:**
- `openai` (version not pinned) - OpenAI API client for image generation (GPT-image-1 model)

**Cloud Services:**
- `google-cloud-storage` (version not pinned) - Google Cloud Storage client for artifact storage
- `google-cloud-secret-manager` (via google.cloud.secretmanager, version not pinned) - Secret Manager client for configuration management

**Web Scraping:**
- `requests` (version not pinned) - HTTP library for scraping GiftCards.com
- `beautifulsoup4` (version not pinned) - HTML parsing for product data extraction
- `lxml_html_clean` (version not pinned) - HTML sanitization and cleaning
- `brotli` (version not pinned) - Brotli compression support for HTTP responses
- `zstandard` (version not pinned) - Zstandard compression support for HTTP responses

**Data Processing:**
- `pandas` (version not pinned) - Data manipulation (potential use case not visible in analyzed code)
- `openpyxl` (version not pinned) - Excel file support (potential use case not visible in analyzed code)
- `fuzzywuzzy` (version not pinned) - Fuzzy string matching (potential use case not visible in analyzed code)

**External Services:**
- `sendgrid` (version not pinned) - Email service (potential use case not visible in analyzed code)
- `replicate` (version not pinned) - AI model hosting platform (potential use case not visible in analyzed code)

**Async & Utilities:**
- `uvloop` (version from base image) - High-performance event loop for asyncio
- `loguru` (version from base image) - Logging library
- `pyyaml` (implicit via yaml import) - YAML parsing for configuration

## Integrations

### Prebuilt: `qurrent.Teams`
- Required Config Section: `MICROSOFT_TEAMS`
- Required Keys:
    - `MICROSOFT_TEAMS_WEBHOOK_URL: string (URL)` - Webhook endpoint for receiving Teams messages and sending responses

**Key Methods Used:**
- `Teams.start(config, webhook_endpoint)` - Initialize Teams integration and start webhook listener
- `teams.send_message(conversation_id, message)` - Send formatted message to Teams conversation
- `teams.link(workflow_instance_id, conversation_id)` - Associate workflow instance with conversation for event routing
- `teams.unlink(conversation_id)` - Remove workflow association when conversation ends

**Event Types:**
- `events.TeamsMessage` - Incoming message from Teams with fields `conversation_id` and `message`

### Prebuilt: `qurrent.Workflow`
- Required Config Section: `QURRENT_OS`
- Required Keys:
    - `INGRESS: object` - Ingress configuration for event routing and workflow lifecycle

**Key Methods Used:**
- `Workflow.create(config)` - Initialize workflow instance with unique workflow_instance_id
- `workflow.ingress.get_workflow_event(workflow_instance_id)` - Wait for next event routed to this workflow
- `workflow.save_to_console(type, content)` - Log observable outputs or errors to Qurrent console
- `workflow.close(status)` - Close workflow with status ("completed" or "failed")

### Prebuilt: `qurrent.Agent`
- Required Config Section: None (configured via YAML file)
- LLM API keys required in config:
    - `ANTHROPIC_API_KEY: string` - For Claude models
    - `OPENAI_API_KEY: string` - For OpenAI/GPT models

**Key Methods Used:**
- `Agent.create(yaml_config_path, workflow_instance_id)` - Initialize agent with YAML configuration
- `agent()` - Execute agent run (LLM reasoning cycle)
- `agent.get_rerun_responses(timeout)` - Execute LLM callable actions and rerun agent with results
- `agent.message_thread.append(Message(...))` - Add messages to conversation thread
- `agent.message_thread.substitute_variables(dict)` - Replace template variables in system prompt

### Custom: `OpenAI` (via openai library)
**Location:** Imported in `agents/assistant.py`
**Type:** One-way (call external API, no webhooks)

**Config Section:** LLM API Keys
- `OPENAI_API_KEY` - OpenAI API authentication key

**Methods:**

**`openai.images.generate(model: str, prompt: str, n: int, size: str) -> ImagesResponse`**
- Performs: Generate AI images using OpenAI DALL-E/GPT-image models
- Behavior:
    - Accepts text prompt and generates n images of specified size
    - Returns ImagesResponse with data array containing b64_json encoded images
- Returns: ImagesResponse object with generated images

### Custom: Google Cloud Secret Manager (via google.cloud.secretmanager)
**Location:** `load_secrets.py`
**Type:** One-way (fetch secrets at startup)

**Config Section:** Environment Variables
- `GOOGLE_CLOUD_PROJECT: string` - GCP project ID for Secret Manager

**Methods:**

**`client.access_secret_version(request: dict) -> AccessSecretVersionResponse`**
- Performs: Fetch latest version of named secret from Secret Manager
- Behavior:
    - Requests secret path `projects/{project_id}/secrets/{secret_name}/versions/latest`
    - Returns secret payload as bytes
- Returns: AccessSecretVersionResponse with payload.data (secret content)

**Secret Names:**
- `customer_keys` - Customer-specific API keys and credentials
- `llm_keys` - LLM provider API keys (Anthropic, OpenAI)
- `additional_keys` - Other integration keys (Teams webhook, GCS, etc.)
