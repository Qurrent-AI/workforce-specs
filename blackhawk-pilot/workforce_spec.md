# Workforce Specification: GiftCardGuru - Blackhawk Marketing Co-Pilot

**Contributors:** alex, Alex Reents, augustfr, SamanthQurrentAI, Alex McConville

## Overview

GiftCardGuru is an AI-powered marketing assistant for GiftCards.com (operated by Blackhawk Network). The system helps marketing teams rapidly create persuasive, compliant, brand-consistent marketing copy across multiple channels—performance ads, blog posts, emails, social media taglines, and internal product selection notes—for specific gift-giving occasions (holidays, life events, celebrations). 

Users interact with the assistant via Microsoft Teams, providing a brief describing the occasion, target audience, and desired content format. The assistant generates occasion-specific copy that follows strict brand voice guidelines, includes concrete product recommendations with accurate purchase links, and meets specified word count requirements. When product details are needed, the assistant dynamically looks up gift card information from a continuously updated inventory. For visual content requests, the system generates custom images via AI and uploads them to cloud storage for immediate use in campaigns.

Behind the scenes, a daily automated scraper keeps the product catalog current by fetching the latest gift card offerings, amounts, descriptions, and availability from GiftCards.com. This ensures marketing copy always references accurate, in-stock products with valid purchase URLs.

The workflow is designed for marketing professionals who need to produce high-volume, on-brand content quickly while maintaining factual accuracy, regulatory compliance, and conversion-oriented messaging.

## Custom Instructions
*FDE-provided instructions for how this particular workforce specification should be configured*
<!--
[Provide custom instructions here around how to understand and document this particular workforce]
-->

## Path Audit

### Agent Architecture

**Core Agent Responsibilities:**

- **Marketing Copy Generation (Assistant Agent)**: 
    - **What**: Generates persuasive, compliant marketing copy tailored to specific gift-giving occasions across various content formats (ads, blogs, emails, social media, internal notes)
    - **When**: Activated upon user message from Teams; runs continuously in a conversational loop until user sends "end"
    - **Why**: Enables marketing teams to rapidly produce high-quality, on-brand content that drives gift card purchases by matching products to occasions and personas

- **Product Information Lookup (Assistant Agent - Action)**: 
    - **What**: Retrieves detailed gift card product information including amounts, descriptions, and canonical purchase URLs
    - **When**: Invoked by the LLM when copy requires specific product links or details
    - **Why**: Ensures marketing copy contains accurate product information and valid URLs, preventing broken links or incorrect claims

- **Image Generation (Assistant Agent - Action)**: 
    - **What**: Creates custom marketing images based on natural language prompts and uploads them to cloud storage
    - **When**: Invoked by the LLM when visual content is needed for campaigns
    - **Why**: Provides on-demand visual assets to complement written copy in marketing campaigns

- **Word Count Validation (Workflow)**: 
    - **What**: Checks if generated content meets user-specified word count requirements (±15% tolerance)
    - **When**: After Assistant agent completes response generation and all rerun actions finish
    - **Why**: Ensures content meets platform-specific length requirements for ads, blog posts, etc.; automatically requests regeneration if out of tolerance

- **Daily Product Catalog Refresh (Background Process)**: 
    - **What**: Scrapes GiftCards.com to update product inventory with current offerings, pricing, descriptions, and availability
    - **When**: Automatically runs every morning at 8:00 AM PST
    - **Why**: Keeps the assistant's product knowledge current, preventing marketing copy from referencing discontinued products or outdated information

**User Touchpoints:**
- **Initial Message**: User provides marketing brief via Teams message (occasion, content type, word count, constraints)
- **Conversational Loop**: User can provide feedback or revisions; assistant iterates until user types "end" or workflow times out (15 minutes)
- **Implicit Approval**: User receives final copy via Teams for review and use; no formal approval gate within workflow

### Decision Ledger

1. **Initiate Conversation**
   - Inputs: Teams message event with conversation ID and user message
   - Outputs: Workflow instance created and linked to Teams conversation; user message processed
   - Decision logic: When a Teams message arrives, create a new GiftCardGuru workflow instance and link it to the conversation. Begin processing the user's message.
   - Logic location: Internal code in `handle_event` function and `GiftCardGuru.run` method
   
2. **Determine Content Strategy**
   - Inputs: User's marketing brief (occasion, channel, constraints, word count)
   - Outputs: Internal strategy for content approach including occasion angle, personas, product mix, tone
   - Decision logic: LLM analyzes the brief against comprehensive brand guidelines to determine the optimal persuasive approach: identifying the occasion moment, mapping to giver/recipient personas, selecting compliance guardrails, and planning multi-brand vs single-brand product recommendations
   - Logic location: Internal prompt in Assistant agent system prompt (lines 12-170 of assistant.yaml)

3. **Decide Whether to Lookup Product Information**
   - Inputs: Current draft content; identified product names requiring URLs or detailed information
   - Outputs: Decision to invoke `lookup_gift_card` action for specific products, or proceed without lookup
   - Decision logic: Before inserting any product link, the assistant must first look up the card to retrieve the canonical URL. If a product is mentioned that requires linking, look it up. If the product cannot be found, prefer a broad multi-brand alternative.
   - Logic location: Internal prompt in Assistant agent system prompt (lines 146-150 of assistant.yaml); LLM-invoked action

4. **Retrieve Product Details**
   - Inputs: Gift card name
   - Outputs: Product amounts, descriptions, purchase URL; or "Product not found" message
   - Decision logic: Search the loaded product inventory dictionary by card name. If found, return the product data. If not found, return a not-found message.
   - Logic location: Internal code in `Assistant.lookup_gift_card` method

5. **Decide Whether to Generate Image**
   - Inputs: User request for visual content; image requirements in brief
   - Outputs: Decision to invoke `generate_image` action with prompt and count, or skip image generation
   - Decision logic: If the user's request explicitly requires or implies the need for visual assets (graphics, images for social media, etc.), invoke image generation with appropriate prompt
   - Logic location: Internal prompt in Assistant agent (implicit in task understanding); LLM-invoked action

6. **Generate and Upload Image**
   - Inputs: Image generation prompt, number of images requested
   - Outputs: Generated image(s) uploaded to Google Cloud Storage; public URL(s) returned; image embedded in Teams message
   - Decision logic: Use OpenAI image generation API to create image(s), upload bytes to GCS bucket, attempt to make public (fallback to signed URL if restricted), send embedded image HTML to Teams conversation
   - Logic location: Internal code in `Assistant.generate_image` method

7. **Produce Initial Marketing Copy**
   - Inputs: Brief, product inventory context, brand guidelines, previous conversation messages
   - Outputs: JSON with "response" (string content), optional "word_count" (target), optional "actions" (list of actions to invoke)
   - Decision logic: Generate marketing copy following extensive brand voice, compliance, and persuasion rules. Return structured JSON. If actions are specified, do not write response content yet (actions are taken first). If no actions, provide complete content in response field.
   - Logic location: Internal prompt in Assistant agent system prompt; LLM reasoning

8. **Determine Word Count Target**
   - Inputs: User-specified word count requirement in brief
   - Outputs: "word_count" field set to user-specified number, or empty string if not specified
   - Decision logic: If the user explicitly specifies a word count requirement (e.g., "1500 word blog post"), set the word_count field to that number. If no word count is specified, leave it empty. If struggling to meet word count after multiple attempts, clear word_count and explain to user.
   - Logic location: Internal prompt in Assistant agent system prompt (lines 184-185 of assistant.yaml)

9. **Execute Rerun Actions**
   - Inputs: Actions array from assistant response
   - Outputs: Rerun results from each action execution; updated response content
   - Decision logic: If the assistant's JSON response includes an "actions" array, execute each action (lookup_gift_card, generate_image), collect results, trigger agent rerun to incorporate results, wait up to 120 seconds for rerun completion
   - Logic location: Internal code in `GiftCardGuru.handle_user_input` method (lines 107-118)

10. **Validate Word Count Compliance**
    - Inputs: Final message text, target word count from assistant response
    - Outputs: Word count validation message if out of tolerance, or None if compliant
    - Decision logic: If a word count target is specified, count words in the text. Calculate ±15% tolerance bounds. If actual word count is below lower bound, return message instructing to lengthen by specific amount. If above upper bound, return message to shorten. If within tolerance, return None.
    - Logic location: Internal code in `GiftCardGuru.word_count_exceeded` method (lines 60-81)

11. **Handle Word Count Failure**
    - Inputs: Word count validation failure message
    - Outputs: Warning message sent to Teams; validation message returned to assistant for rewrite
    - Decision logic: When word count validation fails, send a warning message to the user in Teams ("Rewriting response to meet X ± 15% word count requirement..."). Return the validation message to the assistant's input loop, triggering regeneration.
    - Logic location: Internal code in `GiftCardGuru.handle_user_input` method (lines 121-134)

12. **Send Response to User**
    - Inputs: Final validated message content
    - Outputs: Message sent to Teams conversation; content logged to console
    - Decision logic: If the message has content (length > 0), send it to the Teams conversation. Always log the observable output to the workflow console.
    - Logic location: Internal code in `GiftCardGuru.handle_user_input` method (lines 136-142)

13. **Continue or End Conversation**
    - Inputs: Next Teams message event
    - Outputs: Process next user input, or end workflow if "end" message received
    - Decision logic: Wait for next workflow event. If user message is "end", send "Conversation ended" and terminate workflow. Otherwise, process the new user input starting from step 2.
    - Logic location: Internal code in `GiftCardGuru.run` method (lines 148-164)

14. **Handle Timeout**
    - Inputs: 15-minute timeout expiration
    - Outputs: Timeout message sent to Teams; workflow closed with "completed" status
    - Decision logic: If no activity for 15 minutes, send timeout notification to Teams, close workflow with completed status, unlink from Teams conversation
    - Logic location: Internal code in `handle_event` function (lines 184-190)

15. **Handle Workflow Errors**
    - Inputs: Unhandled exception during workflow execution
    - Outputs: Error message sent to Teams; error logged to console; workflow closed with "failed" status
    - Decision logic: On any exception, send generic error message to user, log error details to workflow console, close workflow as failed, unlink from Teams
    - Logic location: Internal code in `handle_event` function (lines 191-196)

16. **Schedule Daily Product Scrape**
    - Inputs: Current time in PST timezone
    - Outputs: Daily scrape triggered at 8:00 AM PST; product inventory JSON updated
    - Decision logic: Calculate seconds until next 8:00 AM PST. Sleep until that time. Execute scrape. Repeat daily. On error, wait 60 seconds and retry scheduling.
    - Logic location: Internal code in `schedule_daily_scrape` function (lines 203-233)

17. **Execute Product Scrape**
    - Inputs: GiftCards.com brands catalog URL
    - Outputs: Updated `giftcards_com_products.json` file with current products, amounts, descriptions, URLs, availability
    - Decision logic: Fetch HTML from GiftCards.com brands page. Use session to fetch all PLP (product listing page) data via GraphQL across multiple pages. Normalize items into product format. Extract amounts from variants, descriptions from HTML, availability from inventory flags. Save as JSON dictionary keyed by product name.
    - Logic location: Internal code in `scraper.py` module

## Data & Formats

### Referenced Documents Inventory and Input Data

- **Product Inventory File (giftcards_com_products.json)**
    - Format: JSON dictionary with product names as keys
    - Source: Daily automated scrape from GiftCards.com catalog
    - Intended Use: Loaded at Assistant agent creation; provides product names for LLM context and detailed product data for lookups
    - Structure: Each product entry contains: name (string), amounts (array of floats), description (string), url (string), out_of_stock (boolean)
    - Example products: "Giftcards.com" multi-brand card, Visa/Mastercard virtual accounts, single-brand cards (Saks Fifth Avenue, Starbucks, Amazon, etc.), themed multi-brand cards (Fun & Fabulous, One4all, etc.)

- **User Marketing Brief (Teams Message)**
    - Format: Natural language text
    - Source: User input via Microsoft Teams conversation
    - Intended Use: Initial input to Assistant agent; defines occasion, content format, channel, constraints, word count, persona requirements
    - Example topics: Back to School campaigns, Father's Day promotions, seasonal occasions, corporate gifting, event-specific content

- **Brand Guidelines (System Prompt)**
    - Format: Embedded prompt instructions
    - Source: Hard-coded in assistant.yaml configuration
    - Intended Use: Governs all content generation decisions; defines brand voice, compliance rules, channel-specific formatting, product selection principles
    - Key constraints: No superlatives, no emojis/hashtags, "GiftCards.com" exact spelling, warm-but-professional tone, factual accuracy, age-appropriate framing, inclusive language

### Example Output Artifacts

- **Marketing Copy (Teams Message)**
    - Type: Text content
    - Format: Plain text or Markdown-formatted text (depending on channel requirements)
    - Recipients: User in Teams conversation
    - Contents: 
        - Performance ads: Ultra-concise, benefit-driven, single CTA
        - Blog posts: Structured with title, intro, scannable subheads, numbered/bulleted benefits, 5+ occasion-specific reasons, product recommendations with links, early and end CTAs
        - Email: Compact subject line + body, direct, skimmable, one CTA
        - Social taglines: 5+ standalone one-liners, no hashtags/emojis
        - Internal selection notes: Product rankings by occasion fit with rationale
    - All content includes: Occasion framing, persona coverage, compliant claims, product links (when applicable)

- **Generated Marketing Images**
    - Type: Image file
    - Format: PNG (1024x1024)
    - Recipients: Uploaded to Google Cloud Storage; embedded in Teams message; URL available for marketing use
    - Contents: AI-generated images based on marketing campaign prompts; suitable for social media graphics, ad visuals, etc.
    - Storage location: GCS bucket at `blackhawk_{environment}/images/{uuid}.png`

- **Observable Workflow Logs (Console)**
    - Type: Workflow execution logs
    - Format: JSON events logged to Qurrent console
    - Recipients: Workflow monitoring/debugging
    - Contents: Observable outputs (user-facing messages), error messages, execution metadata

## Integration Summary

**Integrations:**

- **Microsoft Teams**: Provides two-way conversational interface for users to request marketing copy and receive results. Workflow links to conversation ID, sends/receives messages, supports HTML formatting for embedded images.

- **OpenAI API**: Generates custom marketing images via GPT-Image-1 model (1024x1024 PNG format). Returns base64-encoded images for upload and use.

- **Google Cloud Storage**: Stores generated marketing images with public URLs (or signed URLs if ACLs restricted). Automatically creates buckets and folder structures as needed.

- **Google Cloud Secret Manager**: Provides runtime configuration and API keys (customer keys, LLM keys, additional keys). Loaded at startup via `load_secrets.py`.

- **GiftCards.com Public Website**: Scraped daily via HTTPS requests and GraphQL API to maintain current product inventory. No authentication required for public catalog data.

## Directory Structure
```
blackhawk-pilot/
├── agents/
│   ├── assistant.py
│   └── config/
│       └── assistant.yaml
├── utils/
│   ├── scraper.py
│   └── storage.py
├── data/
│   └── giftcards_com_products.json
├── blackhawk.py
├── load_secrets.py
├── startup.sh
├── Dockerfile
├── docker-compose.yaml
├── requirements.txt
├── pyproject.toml
└── ingress_registry.json
```

## Agents

### `Assistant`
**Pattern:** Task Agent  
**Purpose:** Generates persuasive, compliant marketing copy for gift card campaigns across multiple content formats. Responds to user briefs with occasion-driven content that follows strict brand guidelines, incorporates accurate product information via lookups, and produces visual assets when needed.

**LLM:** gemini/gemini-2.5-flash, standard mode, temp=0, timeout=120s  
**Fallback LLM:** gpt-5

**Prompt Strategy:**
- Task-oriented approach: receives user brief, produces structured JSON with copy and optional actions
- Extensive brand voice guidelines emphasizing warm-but-professional tone, compliance (no superlatives, no unverifiable claims), occasion-first persuasion
- Channel-specific formatting rules for ads, blogs, emails, social content
- Product selection principles prioritizing multi-brand cards for versatility, single-brand cards for persona coverage
- Mandate to look up products before linking to ensure URL accuracy
- Word count awareness: set "word_count" field when user specifies length requirement
- Context: accumulates throughout conversation
- JSON Response: `{"response": "<string content>", "word_count": "<number or empty>", "actions": [{"name": "lookup_gift_card", "args": {"card_name": "..."}}, {"name": "generate_image", "args": {"prompt": "...", "num_images": 1}}]}`

**Instance Attributes:**
- `teams: Teams` - Microsoft Teams integration instance for sending messages
- `conversation_id: str` - Teams conversation identifier for message routing
- `openai: OpenAI` - OpenAI client for image generation API calls
- `product_inventory: Dict[str, Dict]` - Loaded product catalog keyed by product name; contains amounts, descriptions, URLs, availability

**Create Parameters:**
- `yaml_config_path: str` - Path to agent YAML configuration ("./agents/config/assistant.yaml")
- `workflow_instance_id: UUID` - Parent workflow instance identifier
- `teams: Teams` - Teams integration instance (passed from workflow)
- `conversation_id: str` - Teams conversation ID (passed from workflow)
- `product_inventory_file: str` - Filename of product JSON in data directory ("giftcards_com_products.json")

#### Direct Actions

None. This agent does not define direct actions called from code; all agent execution is via the workflow calling the agent as `await self.assistant_agent()`.

#### LLM Callables

**`lookup_gift_card(card_name: str) -> Union[str, Dict]`**
- `@llmcallable(rerun_agent=True)`
- Docstring Args: `card_name (str): The name of the gift card to lookup.`
- Purpose: Retrieves detailed product information (amounts, description, purchase URL) for a specific gift card; ensures marketing copy uses accurate, canonical URLs
- Integration usage:
    - Calls `self.teams.send_message()` to notify user of lookup in progress ("_Looking up more details about {card_name}..._")
- Returns: Product dictionary `{"name": str, "amounts": [float], "description": str, "url": str, "out_of_stock": bool}` if found; otherwise string "Product {card_name} not found"
- Manual Message Thread: Result automatically appended to thread by `@llmcallable` decorator
- Error Handling: Returns "Product not found" string if card_name key doesn't exist in inventory

**`generate_image(prompt: str, num_images: int = 1) -> str`**
- `@llmcallable(rerun_agent=True)`
- Docstring Args: `prompt (str): A prompt for the image generation.`, `num_images (int): The number of images to generate.`
- Purpose: Creates custom marketing images for campaigns; uploads to cloud storage and embeds in Teams conversation
- Integration usage:
    - Calls `self.teams.send_message()` to notify user of generation in progress ("_Generating {num_images} image(s)..._")
    - Calls `self.openai.images.generate()` with model="gpt-image-1", size="1024x1024", returns base64 PNG
    - Calls `upload_bytes_to_gcs()` to store image in GCS bucket with public URL
    - Calls `self.teams.send_message()` to embed image HTML in conversation (`<img src='...' style='max-width: 100%; height: auto;'>`)
- Returns: String "The image has been generated and sent to the user. Do not respond with anything else."
- Manual Message Thread: Result automatically appended to thread by `@llmcallable` decorator
- Error Handling: No explicit try/except; errors propagate to caller

## YAML Configuration
*Credentials used -- provide keys, not values*

### Secret Manager Secrets (loaded at startup)
```
customer_keys:
    CUSTOMER_KEY_DEV

llm_keys:
    ANTHROPIC_API_KEY
    OPENAI_API_KEY

additional_keys:
    (Additional integration credentials as needed)
```

### Environment Variables
```
GOOGLE_CLOUD_PROJECT: GCP project ID
ENVIRONMENT: development/production (defaults to development)
GCS_BUCKET_NAME: Optional override for storage bucket (defaults to blackhawk_{environment})
```

### Microsoft Teams Integration
```
MICROSOFT_TEAMS_WEBHOOK_URL: Webhook endpoint for Teams bot
```

### Ingress Configuration
```
INGRESS: Qurrent OS ingress configuration for workflow event routing
```

## Utils

**`scraper.scrape_giftcards_com(file_name: str) -> None`** (async)
- Purpose: Fetches current gift card product catalog from GiftCards.com and saves to JSON file
- Implementation: 
    - Creates authenticated HTTP session with realistic browser headers to avoid bot detection
    - Fetches initial HTML from GiftCards.com brands page
    - Extracts pagination info from embedded JSON-LD data
    - Iterates through all product listing pages via GraphQL API calls
    - Parses each product's variants to extract gift card amounts from product metadata
    - Checks inventory availability across variants
    - Normalizes HTML descriptions to plain text
    - Builds product dictionary keyed by product name
    - Saves to `data/{file_name}` as formatted JSON
- Dependencies: `requests`, `beautifulsoup4`, `lxml_html_clean`, `brotli`, `zstandard`

**`storage.upload_bytes_to_gcs(object_path: str, data: bytes, content_type: str, bucket_name: Optional[str], make_public: bool) -> str`**
- Purpose: Uploads binary data to Google Cloud Storage and returns a URL
- Implementation:
    - Resolves bucket name (uses environment-based default if not specified)
    - Creates bucket if it doesn't exist
    - Ensures folder prefix exists by creating placeholder objects with trailing slashes
    - Uploads data bytes with specified content type
    - Attempts to make object public and return public URL
    - Falls back to 24-hour signed URL if public ACLs are restricted
- Dependencies: `google-cloud-storage`

**`storage.get_or_create_bucket(bucket_name: Optional[str]) -> storage.Bucket`**
- Purpose: Returns existing GCS bucket or creates it if missing
- Implementation: Uses `storage.Client()` to lookup bucket; creates with default settings if not found
- Dependencies: `google-cloud-storage`

**`load_secrets.fetch_secret(project_id: str, secret_name: str) -> str`**
- Purpose: Retrieves secret from Google Cloud Secret Manager
- Implementation: Uses Application Default Credentials to access Secret Manager API; fetches latest version; decodes UTF-8 payload
- Dependencies: `google-cloud-secretmanager`

**`load_secrets.parse_and_export_yaml(yaml_content: str) -> Dict[str, str]`**
- Purpose: Parses YAML secret content and exports key-value pairs as environment variables
- Implementation: Attempts structured YAML parsing with fallback to line-by-line parsing; sets os.environ for each key-value pair
- Dependencies: `pyyaml`

## Dependencies

- `qurrent-os==0.9` - Qurrent OS framework for agent workflows, Teams integration, event handling, observability (base Docker image)
- `requests` - HTTP client for web scraping GiftCards.com catalog
- `beautifulsoup4` - HTML parsing for extracting product data from scraped pages
- `lxml_html_clean` - HTML sanitization for description text normalization
- `brotli` - Decompression support for Brotli-encoded HTTP responses
- `zstandard` - Decompression support for Zstandard-encoded HTTP responses
- `google-cloud-storage` - Google Cloud Storage client for uploading generated images
- `google-cloud-secretmanager` - Google Cloud Secret Manager client for loading runtime configuration
- `openai` - OpenAI API client for image generation (gpt-image-1 model)
- `pyyaml` - YAML parsing for secret configuration
- `loguru` - Structured logging
- `uvloop` - High-performance event loop for async execution
- `sendgrid` - Email service integration (installed but not actively used in current implementation)
- `replicate` - Replicate API client (installed but not actively used in current implementation)
- `pandas` - Data manipulation (installed but not actively used in current implementation)
- `openpyxl` - Excel file support (installed but not actively used in current implementation)
- `fuzzywuzzy` - Fuzzy string matching (installed but not actively used in current implementation)

## Integrations

### Prebuilt: `qurrent.Teams`
- Required Config Section: `MICROSOFT_TEAMS_WEBHOOK_URL`
- Required Keys:
    - `MICROSOFT_TEAMS_WEBHOOK_URL: string` - Webhook endpoint for sending/receiving Teams messages

**Methods Used:**
- `send_message(conversation_id: str, content: str) -> None`: Sends formatted text or HTML message to Teams conversation
- `link(workflow_instance_id: UUID, conversation_id: str) -> None`: Associates workflow with Teams conversation for event routing
- `unlink(conversation_id: str) -> None`: Disassociates workflow from conversation on completion/failure

### Prebuilt: `qurrent.Ingress`
- Required Config Section: `INGRESS`
- Required Keys: (Configuration structure defined by Qurrent OS framework)

**Methods Used:**
- `get_start_event(use_snapshots: bool) -> Tuple[Event, Any]`: Retrieves initial workflow trigger event from ingress queue
- `get_workflow_event(workflow_instance_id: UUID) -> Event`: Waits for next event targeted at specific workflow instance (for conversational loop)

### Custom: `OpenAI` (standard library client)
**Location:** Instantiated directly in `agents/assistant.py`
**Type:** One-way (assistant calls OpenAI API)

**Config Section:** `llm_keys`
- `OPENAI_API_KEY: string` - OpenAI API authentication key (loaded from Secret Manager)

**Methods Used:**

**`images.generate(model: str, prompt: str, n: int, size: str) -> ImageResponse`**
- Performs: Generates AI images based on natural language prompt
- Behavior:
    - Uses gpt-image-1 model
    - Returns base64-encoded PNG images in 1024x1024 resolution
    - Response includes `data[0].b64_json` field with image bytes
- Returns: OpenAI ImageResponse object with base64-encoded image data

### Custom: `GiftCards.com Public API/Website`
**Location:** `utils/scraper.py`
**Type:** One-way (workforce scrapes public data)

**No Authentication Required** - Public catalog data

**Endpoints Used:**

**`GET https://www.giftcards.com/us/en/catalog/brands`**
- Performs: Fetches HTML page with embedded product catalog data
- Sample Data: HTML with JSON-LD structured data and embedded JavaScript product objects
- Behavior:
    - Returns HTML with initial page of products
    - Contains pagination metadata (total_pages) for GraphQL queries
- Returns: HTML text with embedded JSON

**`POST https://www.giftcards.com/commerce/graphql`**
- Performs: Retrieves paginated product listing data via GraphQL
- Sample Data: `data/giftcards_com_products.json` - Product catalog with names, amounts, descriptions, URLs, availability
- Behavior:
    - Accepts PLP (Product Listing Page) query with pagination parameters
    - Returns structured product data with variants, amounts, inventory status
    - Requires realistic browser headers and anti-bot client ID for successful requests
    - Multiple requests made to fetch all pages (40 products per page)
- Returns: JSON with categories.items[].products.items[] array of product objects

### Custom: `Google Cloud Storage`
**Location:** `utils/storage.py`
**Type:** One-way (workforce uploads images)

**Config Section:** Environment variables
- `GCS_BUCKET_NAME: optional string` - Override for storage bucket name (defaults to `blackhawk_{environment}`)
- `ENVIRONMENT: string` - Environment name for default bucket naming (defaults to "development")

**Authentication:** Uses Application Default Credentials (ADC) via Google Cloud SDK

**Methods Implemented:**

**`upload_bytes_to_gcs(object_path: str, data: bytes, content_type: str, bucket_name: Optional[str], make_public: bool) -> str`**
- Performs: Uploads binary data to GCS bucket and returns URL
- Behavior:
    - Creates bucket if it doesn't exist
    - Uploads with specified content type
    - Attempts to make public; falls back to 24-hour signed URL if ACLs restricted
- Returns: Public URL string or signed URL string

**`get_or_create_bucket(bucket_name: Optional[str]) -> storage.Bucket`**
- Performs: Returns bucket object, creating if necessary
- Behavior:
    - Looks up bucket by name
    - Creates with default settings if not found
- Returns: Google Cloud Storage Bucket object

### Custom: `Google Cloud Secret Manager`
**Location:** `load_secrets.py`
**Type:** One-way (workforce reads secrets at startup)

**Config Section:** Environment variables
- `GOOGLE_CLOUD_PROJECT: string` - GCP project ID for Secret Manager access

**Authentication:** Uses Application Default Credentials (ADC) via Google Cloud SDK

**Secrets Retrieved:**
- `customer_keys` - Customer-specific API keys and credentials (including CUSTOMER_KEY_DEV)
- `llm_keys` - LLM provider API keys (ANTHROPIC_API_KEY, OPENAI_API_KEY)
- `additional_keys` - Additional integration credentials

**Methods Implemented:**

**`fetch_secret(project_id: str, secret_name: str) -> str`**
- Performs: Retrieves latest version of named secret from Secret Manager
- Behavior:
    - Uses ADC authentication
    - Accesses `projects/{project_id}/secrets/{secret_name}/versions/latest`
    - Decodes UTF-8 payload
- Returns: Secret content as string (typically YAML format)

**`parse_and_export_yaml(yaml_content: str) -> Dict[str, str]`**
- Performs: Parses YAML secret content and sets environment variables
- Behavior:
    - Attempts structured YAML parsing
    - Falls back to line-by-line key:value parsing
    - Sets `os.environ[key] = value` for each entry
    - Appends to `config.yaml` file for Qurrent OS configuration loading
- Returns: Dictionary of exported key-value pairs
