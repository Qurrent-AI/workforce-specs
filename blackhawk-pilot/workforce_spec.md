# Workforce Specification: GiftCardGuru

**Contributors:** alex, Alex Reents, augustfr, SamanthQurrentAI, Alex McConville

## Overview

GiftCardGuru is an AI-powered marketing co-pilot for Blackhawk Network's GiftCards.com brand. The system assists marketing teams in crafting persuasive, compliant, and conversion-oriented copy across multiple channels—including performance ads, blog posts, emails, social media taglines, and internal product selection notes. The workforce operates as an interactive assistant that responds to user requests via Microsoft Teams, generating marketing content tailored to specific occasions (e.g., Back to School, Father's Day, Teacher Appreciation) while maintaining strict brand guidelines and compliance standards.

The system maintains an up-to-date inventory of available gift card products by scraping GiftCards.com daily at 8:00 AM PST. When users request marketing copy, the assistant can look up specific gift card details (amounts, descriptions, purchase URLs) and generate custom images using AI image generation. The assistant enforces brand voice, compliance guardrails (no superlatives, only verified claims, age-appropriate framing), and can automatically adjust content to meet specified word count requirements.

## Custom Instructions
*FDE-provided instructions for how this particular workforce specification should be configured*
<!--
This workforce implements a sophisticated marketing copywriter with extensive brand guidelines embedded in the system prompt. The assistant is designed to be autonomous—completing tasks end-to-end without requesting additional information from users unless absolutely necessary. When documenting decisions, focus on the marketing logic and content strategy decisions rather than technical implementation details.
-->

## Decision Audit

Documents the possible paths of workflow execution through the lens of decisions the workforce makes.

- [1] Accept or reject incoming Teams message
    - Inputs: Teams message event with conversation ID and message content
    - Outputs: Workflow creation and execution, or timeout/error handling
    - Decision logic: Accept all incoming Teams messages and create a new GiftCardGuru workflow instance. If workflow exceeds 15 minutes of inactivity, end the conversation. If message content is "end" (case-insensitive), terminate the conversation gracefully.
    - Logic location: internal code

- [2] Determine content type and channel for marketing copy
    - Inputs: User's natural language request describing desired marketing content
    - Outputs: Marketing copy formatted for the appropriate channel (ad, blog, email, social, or internal selection/ranking)
    - Decision logic: The assistant analyzes the user's request to determine what type of marketing content to create. Based on channel-specific guidelines embedded in the system prompt: Performance ads are ultra-concise with one clear benefit; blog posts are structured with scannable subheads and 5+ occasion-specific reasons; emails are compact and skimmable with benefit-led subject lines; social taglines provide at least 5 one-liners suitable for graphics; internal selection/ranking ranks products by occasion fit and breadth of appeal.
    - Logic location: internal prompt (system_prompt in assistant.yaml)

- [3] Identify occasion and target personas
    - Inputs: User's content request including occasion details (e.g., "Back to School", "Father's Day") and any persona hints
    - Outputs: Marketing angle focused on the specific occasion with persona-appropriate messaging
    - Decision logic: The assistant leads with the occasion (what's happening, why it matters now) and ties benefits to that moment—timing flexibility, gift-giving logistics, budget control, choice. Considers both givers and recipients across diverse personas: parents, students, teachers, grads, gamers, outdoor enthusiasts, home improvers, beauty fans, movie lovers, coffee enthusiasts, co-workers, and hosts. Scenarios are made specific (e.g., "lists aren't final," "host thank-you," "dorm setup").
    - Logic location: internal prompt

- [4] Select which gift cards to feature
    - Inputs: User's occasion and content requirements; available product inventory loaded from giftcards_com_products.json
    - Outputs: Selection of specific gift card products to mention/link in the copy
    - Decision logic: The assistant prioritizes multi-brand cards (e.g., One4all, Cheers To You, Home Sweet Home, Fun & Fabulous) for versatility, then includes distinct single-brand options to cover different personas. Matches products only when the logic is strong for the occasion. For charity-themed cards, reflects only the stated donation mechanism. If nothing fits the occasion, recommends a broad multi-brand option.
    - Logic location: internal prompt

- [5] Decide whether to look up gift card details
    - Inputs: Draft marketing copy that references specific gift card products
    - Outputs: Action to invoke `lookup_gift_card` for retrieving canonical URLs, amounts, and descriptions
    - Decision logic: Before inserting any product link, the assistant must first look up the card using the lookup action to retrieve the canonical GiftCards.com purchase URL. The assistant is instructed never to guess or invent URLs. If a product cannot be found via lookup, the assistant omits the link for that brand and prefers a broad multi-brand alternative. This is an LLM-invoked action.
    - Logic location: internal prompt

- [6] Decide whether to generate custom images
    - Inputs: User request that implies or explicitly asks for visual content
    - Outputs: Action to invoke `generate_image` with a specific prompt and number of images
    - Decision logic: When the user's request suggests a need for visual assets or explicitly asks for image generation, the assistant generates images using OpenAI's image generation model. The assistant crafts an appropriate prompt based on the marketing context and occasion. This is an LLM-invoked action.
    - Logic location: internal prompt

- [7] Apply brand voice and compliance filters
    - Inputs: Draft marketing copy
    - Outputs: Copy that conforms to GiftCards.com brand identity, voice, tone, and compliance guardrails
    - Decision logic: The assistant applies multiple brand rules: Always writes brand as "GiftCards.com" (exact casing); maintains warm, savvy, practical, lightly playful tone without being snarky or cutesy; uses conversational, crisp language with strong verbs and short sentences; avoids first person, emojis, hashtags, and exclamation stacks. Compliance guardrails prohibit superlatives (e.g., "best," "perfect"), unverifiable claims, and only state features that are explicitly provided. Age-appropriate framing is required—no glamorizing alcohol, no implying suitability for minors. Content must be inclusive and respectful without stereotypes.
    - Logic location: internal prompt

- [8] Structure content according to channel best practices
    - Inputs: Determined channel type (ad, blog, email, social) and draft content
    - Outputs: Content formatted and structured according to channel-specific guidelines
    - Decision logic: Performance ads: ultra-concise, land one clear benefit + occasion relevance, persona coverage via multiple crisp variants, one short CTA. Blog posts: focused title, tight intro, scannable subheads, numbered/bulleted benefits, diverse recipient scenarios, early and end CTAs, integrate card names/descriptions in original words, ~5 occasion-specific reasons. Email: compact, direct, skimmable, one idea per line, one CTA, concrete benefit-led subject lines. Social taglines: at least 5 one-liners where each stands alone, a couple may use light brand-fit puns, tie to occasion and clear benefit, no hashtags or emojis.
    - Logic location: internal prompt

- [9] Verify and format product links
    - Inputs: Gift card product names and lookup results containing canonical URLs
    - Outputs: Properly formatted Markdown links in the copy
    - Decision logic: Use Markdown link syntax only: `[Brand or Product Name](https://...)`. Never show bare URLs. Link only to official GiftCards.com product pages returned by lookup—no category/search pages, no tracking params/UTMs. Link specific brands/products only; do not hyperlink generic nouns. For multiple links in one line, separate with commas and optional "or". Ensure HTTPS and that anchor text matches the destination brand/product.
    - Logic location: internal prompt

- [10] Determine if specified word count is met
    - Inputs: Generated marketing copy text and user-specified target word count (if provided)
    - Outputs: Word count validation result; if target is not met within tolerance, a message instructing the assistant to lengthen or shorten the response
    - Decision logic: If the user specifies a word count, the assistant sets the "word_count" key in its JSON response. The workflow checks if the actual word count is within 15% above or below the target. If the count is too low, return a message asking for approximately N more words. If too high, ask to shorten by approximately N words. If within tolerance or after multiple attempts, clear the word count requirement and proceed. The assistant is instructed that if struggling after many attempts, it should clear the word count and explain to the user.
    - Logic location: internal code (word_count_exceeded method) and internal prompt

- [11] Decide whether to rerun agent after actions complete
    - Inputs: Assistant's JSON response with "actions" array containing lookup_gift_card or generate_image actions
    - Outputs: Execution of actions, followed by agent rerun with action results in context
    - Decision logic: If the assistant's response includes an "actions" array, the workflow executes those actions (each decorated with `@llmcallable(rerun_agent=True)`). After actions complete (with 120-second timeout), the agent is rerun with action results appended to its message thread. The agent then generates a final response incorporating the action results. The assistant is instructed: "While you are taking actions, do not write a response. When writing a response, do not take actions."
    - Logic location: internal code (handle_user_input observable) and internal prompt

- [12] Send response to user or request revision
    - Inputs: Final assistant response (after any actions and reruns) and word count validation
    - Outputs: Message sent to Teams conversation, or loop back to assistant for word count adjustment
    - Decision logic: If word count validation returns a message (indicating the response doesn't meet the target), send a warning to the user about rewriting to meet word count requirements, then pass the validation message back to the assistant to generate a revised response. Otherwise, send the final response to the Teams conversation. Empty responses are not sent.
    - Logic location: internal code

- [13] Continue conversation or end workflow
    - Inputs: User's next message in the ongoing conversation
    - Outputs: Continue processing messages through the assistant, or end the conversation
    - Decision logic: After sending a response, the workflow waits for the next message from the user via the ingress queue. If the message is "end" (case-insensitive), send "Conversation ended." and terminate the workflow. Otherwise, process the message as "User input: {message}" and continue the conversation loop. If 15 minutes elapse with no user input, the workflow times out and sends "The workflow has ended after 15 minutes of inactivity."
    - Logic location: internal code

## Data & Formats

### Referenced Documents Inventory and Input Data

- **Product Inventory (giftcards_com_products.json)**
    - Format: JSON dictionary with product names as keys
    - Source: Daily automated scrape of GiftCards.com at 8:00 AM PST
    - Intended Use: Loaded at assistant creation; product names substituted into system prompt; individual products looked up via `lookup_gift_card` action when assistant needs canonical URLs, amounts, and descriptions
    - Contents: Each product entry contains:
        - `name`: Gift card product name (e.g., "Giftcards.com", "Visa® Virtual Account", "Starbucks", "Amazon.com")
        - `amounts`: Array of available denominations (e.g., [50.0, 100.0, 250.0])
        - `description`: Marketing description of the gift card and its features
        - `url`: Canonical GiftCards.com product page URL
        - `out_of_stock`: Boolean indicating inventory availability

- **User Requests (Teams Messages)**
    - Format: Plain text natural language messages
    - Source: Microsoft Teams conversations with users (marketing team members)
    - Intended Use: Parsed by the assistant to understand desired marketing content, target channel, occasion, word count requirements, and any specific constraints or preferences

### Example Output Artifacts

- **Marketing Copy (Primary Output)**
    - Type: Text content for various marketing channels
    - Format: Markdown-formatted text (for structure and links) or plain text
    - Recipients: Marketing team members via Microsoft Teams conversation
    - Contents: Varies by channel type:
        - **Performance Ads**: Ultra-concise copy with one clear benefit, occasion relevance, and short CTA
        - **Blog Posts**: 1500+ word articles with focused title, intro, scannable subheads, numbered/bulleted benefits, diverse recipient scenarios, product links, CTAs
        - **Email**: Compact email content with benefit-led subject line, skimmable body, and one CTA
        - **Social Taglines**: 5+ one-liner options suitable for social media graphics, each tied to occasion and benefit
        - **Internal Selection/Ranking**: Product recommendations ranked by occasion fit and persona coverage with rationale

- **Generated Images**
    - Type: AI-generated visual content
    - Format: PNG images (1024x1024 pixels)
    - Recipients: Displayed inline in Teams conversation via HTML img tags
    - Contents: Custom images generated based on marketing prompts, uploaded to Google Cloud Storage with public URLs

- **Status Messages**
    - Type: Progress updates and notifications
    - Format: Plain text or Markdown with emphasis (e.g., "_Looking up more details..._")
    - Recipients: User in Teams conversation
    - Contents:
        - "_Looking up more details about {card_name}..._" when performing gift card lookups
        - "_Generating an image..._" or "_Generating {N} images..._" when creating visuals
        - "Rewriting response to meet {word_count} (± 15%) word count requirement..." when adjusting for word count
        - "The image has been generated and sent to the user. Do not respond with anything else." (returned to assistant after image generation)

- **Observable Outputs (Supervisor Console)**
    - Type: Business-friendly context logged to The Supervisor observability platform
    - Format: Text saved via `save_to_console(type='observable_output', content=...)`
    - Recipients: Stakeholders viewing The Supervisor dashboard
    - Contents: Concatenated view of all messages sent to the user during the observable execution, including action results and final responses

## Integration Summary

**Integrations:**

- **Microsoft Teams** (Prebuilt `qurrent.Teams`): Provides two-way communication with marketing team users. Receives inbound TeamsMessage events that trigger workflow instances. Sends outbound messages containing marketing copy, status updates, and generated images to specific conversations. Maintains conversation state via link/unlink methods tied to workflow instance IDs.

- **OpenAI** (Custom via `openai.OpenAI` client): Generates custom marketing images using the GPT-image-1 model. Receives text prompts and parameters (size, count) and returns base64-encoded PNG images. Used when the assistant determines visual content would enhance the marketing deliverable.

- **Google Cloud Storage** (Custom via `utils/storage.py`): Stores generated images in a GCS bucket (default: `blackhawk_{environment}`) and provides public URLs for embedding in Teams messages. Creates bucket and folder structure as needed. Supports public ACLs or falls back to 24-hour signed URLs if bucket-level access controls restrict public sharing.

- **GiftCards.com Website** (Custom scraper via `utils/scraper.py`): One-way integration that scrapes product catalog data daily. Fetches HTML from the brands page, extracts product information from JSON-LD structured data and GraphQL API, and saves to `giftcards_com_products.json`. Not interactive—operates on a scheduled basis independent of user requests.

- **Google Cloud Secret Manager** (Custom via `load_secrets.py`): One-way integration for loading configuration secrets at startup. Fetches `customer_keys`, `llm_keys`, and `additional_keys` secrets from GCP Secret Manager and populates `config.yaml` and environment variables. Used during container initialization, not during workflow execution.

## Directory Structure

```
blackhawk-pilot/
├── agents/
│   ├── config/
│   │   └── assistant.yaml
│   └── assistant.py
├── data/
│   └── giftcards_com_products.json
├── utils/
│   ├── scraper.py
│   └── storage.py
├── blackhawk.py
├── load_secrets.py
├── requirements.txt
├── pyproject.toml
├── Dockerfile
├── docker-compose.yaml
├── startup.sh
└── README.md
```

## Agents

**Note:** Document Console Agents first (what business stakeholders see), then Technical Agents (implementation details).

### Console Agents

#### `assistant`
**Type:** Console Agent (method with `@console_agent` decorator)  
**Purpose:** Represents the main GiftCardGuru marketing co-pilot interface that handles all user interactions  
**Docstring:** "Main assistant agent responsible for handling user input"

**Observable Tasks:**

**`handle_user_input(input_message: str, conversation_id: str)`**
- `@observable` decorator
- Docstring: "Handling a request from the user"
- Purpose: Orchestrates the complete user request cycle—from receiving input through generating responses, executing actions, validating word counts, and sending final output
- Technical Agent Calls: 
    - Calls `self.assistant_agent()` to invoke the Assistant technical agent for generating marketing copy and determining actions
    - Calls `self.assistant_agent.get_rerun_responses(timeout=120)` to execute any actions (gift card lookups, image generation) and collect updated responses after agent rerun
- Integration Calls:
    - Calls `self.teams.send_message(conversation_id, message)` to send responses, status updates, and word count warnings to the Teams conversation
- Deterministic Logic:
    - Appends user message to assistant's message thread
    - Calls `self._stringify(response)` to format dictionary responses into readable text
    - Calls `self.word_count_exceeded(message_to_send, required_word_count)` to validate word count against user-specified target (±15% tolerance)
    - Loops back to assistant if word count validation fails, passing correction message
    - Concatenates all messages for observable output
- Observability Output: `save_to_console(type='observable_output', content=observable_output)` containing all user-facing messages generated during this request
- Returns: `None` if response is complete and sent; returns word count correction message if validation fails (triggering rerun via main loop)

### Technical Agents

#### `Assistant`
**Type:** Technical Agent (extends `Agent` class)  
**Pattern:** Orchestrator with Task characteristics—maintains conversation context across turns, uses structured JSON responses with optional actions array, completes marketing content generation tasks with high accuracy  
**Purpose:** Generates persuasive, compliant marketing copy for GiftCards.com across multiple channels while adhering to strict brand guidelines. Acts as a creative writer that can autonomously look up product details and generate images when needed.  
**LLM:** gemini/gemini-2.5-flash (primary), gpt-5 (fallback), standard mode, temp=0, timeout=120s

**Prompt Strategy:**
- Extensive system prompt (204 lines) defining role as "creative-but-precise marketing writer for GiftCards.com"
- Brand identity rules: exact casing "GiftCards.com", warm/savvy/practical tone, conversational crisp language, no emojis/hashtags/exclamation stacks
- Compliance guardrails: no superlatives, only verified claims, age-appropriate framing, inclusive language
- Occasion-first persuasion: lead with the moment, tie benefits to timing and logistics
- Channel-specific guidance: ultra-concise ads, structured scannable blogs, compact emails, standalone social taglines
- Product selection principles: prioritize multi-brand cards for versatility, match only when logic is strong
- Linking mandate: MUST look up products before inserting links, use Markdown syntax only, never bare URLs
- Context: Accumulates conversation history; product inventory names substituted into prompt; available actions documented
- JSON Response: `{"response": "<string>", "word_count": "" or "<user-specified word count>", "actions": [{"name": "<action_name>", "args": {...}}]}`
- Execution best practices: plan-then-write internally, complete tasks end-to-end in one pass, make reasonable assumptions when details missing, self-review against internal rubric before finalizing

**Instance Attributes:**
- `teams: Teams` - Microsoft Teams integration instance for sending messages
- `conversation_id: str` - Unique identifier for the current Teams conversation
- `openai: OpenAI` - OpenAI client for image generation
- `product_inventory: Dict[str, Dict]` - Dictionary mapping product names to product details (amounts, description, URL, stock status) loaded from giftcards_com_products.json

**Create Parameters:**
- `yaml_config_path: str` - Path to "./agents/config/assistant.yaml" containing LLM config and system prompt
- `workflow_instance_id: UUID` - Unique identifier for the parent GiftCardGuru workflow instance
- `teams: Teams` - Teams integration instance (passed from workflow)
- `conversation_id: str` - Teams conversation ID (passed from workflow)
- `product_inventory_file: str` - Filename for product data JSON (typically "giftcards_com_products.json")

**Instantiation Pattern:** Attributes declared in class; set in `create` classmethod which loads product inventory from file and substitutes product names into message thread prompt variables.

#### Direct Actions

(None. The Assistant agent has no direct action methods—all actions are LLM-invoked via `@llmcallable` decorator.)

#### LLM Callables

**`lookup_gift_card(card_name: str) -> Union[str, Dict]`**
- `@llmcallable(rerun_agent=True)` - Results appended to thread; agent rerun after execution
- Docstring Args: `card_name (str): The name of the gift card to lookup.`
- Docstring Description: "Returns the specific gift card amount options, descriptions, and purchase link for a particular gift card product."
- Purpose: Retrieves canonical product information from the pre-loaded product inventory to ensure accurate URLs and details in marketing copy
- Integration usage:
    - Calls `self.teams.send_message(self.conversation_id, f"_Looking up more details about {card_name}..._")` to notify user of the lookup action
- Returns: Dictionary containing `name`, `amounts`, `description`, `url`, and `out_of_stock` fields if product found; otherwise returns string `f"Product {card_name} not found"`
- Manual Message Thread: Return value automatically appended by `@llmcallable` framework; no manual append
- Error Handling: No explicit try/except; returns "not found" message if product key doesn't exist in inventory dictionary

**`generate_image(prompt: str, num_images: int = 1) -> str`**
- `@llmcallable(rerun_agent=True)` - Results appended to thread; agent rerun after execution
- Docstring Args: `prompt (str): A prompt for the image generation.` and `num_images (int): The number of images to generate.`
- Docstring Description: "Generates an image based on the prompt."
- Purpose: Creates custom AI-generated images for marketing content when visual assets would enhance the deliverable
- Integration usage:
    - Calls `self.teams.send_message(self.conversation_id, f"_Generating {num_images} images..._")` or `"_Generating an image..._"` to notify user
    - Calls `self.openai.images.generate(model="gpt-image-1", prompt=prompt, n=num_images, size="1024x1024")` to generate images
    - Calls `self.teams.send_message(self.conversation_id, f"<img src='{public_url}' style='max-width: 100%; height: auto;'><br><br>")` to display generated image inline in Teams
- Util usage:
    - Uses `upload_bytes_to_gcs(object_path=f"images/{uuid.uuid4()}.png", data=image_bytes, content_type="image/png")` to upload image and obtain public URL
- Returns: String message: "The image has been generated and sent to the user. Do not respond with anything else."
- Manual Message Thread: Return value automatically appended by `@llmcallable` framework
- Error Handling: No explicit try/except block; errors would propagate to caller

## YAML Configuration
*Credentials used -- provide keys, not values*

**Secrets loaded from GCP Secret Manager:**
- customer_keys
- llm_keys
- additional_keys

**Expected keys in config.yaml (assembled by load_secrets.py):**

LLM_KEYS:
- ANTHROPIC_API_KEY
- OPENAI_API_KEY

MICROSOFT_TEAMS:
- MICROSOFT_TEAMS_WEBHOOK_URL (webhook endpoint URL for Teams integration)

INGRESS:
- Configuration for Qurrent ingress system (receives TeamsMessage events)

GOOGLE_CLOUD_PROJECT:
- Project ID for GCP services (Secret Manager, Cloud Storage)

ENVIRONMENT:
- Deployment environment (e.g., "development", "production") affecting GCS bucket naming

GCS_BUCKET_NAME (optional):
- Override for default GCS bucket name (defaults to `blackhawk_{environment}`)

## Utils

**`utils.scraper.scrape_giftcards_com(file_name: str = "giftcards_com_products.json") -> None`**
- Purpose: Scrapes GiftCards.com brand catalog to extract current product inventory including names, amounts, descriptions, URLs, and stock status
- Implementation: Creates HTTP session with realistic browser headers; fetches HTML from brands page; parses JSON-LD structured data and embedded JavaScript product objects; makes GraphQL queries to paginate through all products (40 per page); extracts gift card amounts from variant data; normalizes descriptions from HTML; saves products as JSON dictionary with product names as keys
- Dependencies: `requests==*`, `beautifulsoup4==*`, `brotli==*`, `zstandard==*` (for HTTP compression), standard library `json`, `re`, `pathlib`

**`utils.scraper.build_headers() -> dict`**
- Purpose: Constructs realistic browser headers for web scraping to avoid bot detection
- Implementation: Returns dictionary mimicking Chrome 139 on macOS with appropriate accept, encoding, language, referer, sec-fetch, and user-agent headers
- Dependencies: Standard library only

**`utils.scraper.create_session() -> requests.Session`**
- Purpose: Creates configured HTTP session with browser-like headers
- Implementation: Instantiates `requests.Session` and applies headers from `build_headers()`
- Dependencies: `requests==*`

**`utils.scraper.fetch_html(url: str, query: dict, session: requests.Session | None = None) -> str`**
- Purpose: Fetches HTML content from a URL with query parameters
- Implementation: Performs GET request with 30-second timeout; handles gzip/deflate/br/zstd compression automatically; raises exception on HTTP errors
- Dependencies: `requests==*`

**`utils.scraper.parse_products_from_html(html_path: Path) -> list[dict]`**
- Purpose: Extracts product data from saved HTML file using JSON-LD structured data
- Implementation: Parses HTML with BeautifulSoup; finds JSON-LD script tags with type "application/ld+json"; extracts CollectionPage mainEntity arrays; parses Product entities with names, offers (amounts), URLs; checks for out-of-stock status by traversing DOM hierarchy
- Dependencies: `beautifulsoup4==*`, standard library `json`, `pathlib`

**`utils.scraper.extract_plp_items(html_text: str) -> list[dict]`**
- Purpose: Extracts product listing page (PLP) items from embedded JavaScript objects in HTML
- Implementation: Uses regex to find `"products": {...}` patterns; extracts balanced JSON objects using custom bracket-matching algorithm; parses JSON and collects items arrays
- Dependencies: Standard library `re`, `json`

**`utils.scraper.graphql_fetch_plp_page(session: requests.Session, page_index: int, page_size: int = 40, category_key: str = "brands") -> dict`**
- Purpose: Fetches one page of product data from GiftCards.com GraphQL API
- Implementation: Posts GraphQL query with pagination variables to commerce endpoint; includes store ID, operation type, and caller ID headers; validates JSON response; returns parsed data
- Dependencies: `requests==*`

**`utils.scraper.fetch_all_plp_items(session: requests.Session, html_text: str) -> list[dict]`**
- Purpose: Iterates through all product listing pages via GraphQL to collect complete inventory
- Implementation: Extracts total page count from initial HTML; loops through pages 1 to N making GraphQL requests; aggregates all product items; handles errors gracefully and continues pagination
- Dependencies: Calls `graphql_fetch_plp_page` and `plp_total_pages_from_html`

**`utils.scraper.normalize_plp_items_to_products(plp_items: list[dict]) -> list[dict]`**
- Purpose: Converts raw PLP item dictionaries into standardized product format
- Implementation: Maps url_key to full product URL; extracts description from short_description HTML; calls `extract_giftcard_amounts` to parse variant amounts; calls `check_inventory_availability` to determine stock status
- Dependencies: Calls `extract_giftcard_amounts`, `check_inventory_availability`, `normalize_text_html_to_plain`

**`utils.scraper.save_products_to_json(products: list[dict], file_name: str) -> None`**
- Purpose: Saves product list as JSON dictionary to data directory
- Implementation: Converts product list to dictionary with product names as keys; writes to `data/{file_name}` with pretty-printing (indent=2) and UTF-8 encoding
- Dependencies: Standard library `json`, `pathlib`

**`utils.storage.get_or_create_bucket(bucket_name: Optional[str] = None) -> storage.Bucket`**
- Purpose: Returns existing GCS bucket or creates it if missing
- Implementation: Looks up bucket by name (defaults to `blackhawk_{environment}`); creates bucket if not found
- Dependencies: `google-cloud-storage==*`

**`utils.storage.upload_bytes_to_gcs(object_path: str, data: bytes, *, content_type: str = "application/octet-stream", bucket_name: Optional[str] = None, make_public: bool = True) -> str`**
- Purpose: Uploads binary data to Google Cloud Storage and returns a public URL
- Implementation: Ensures bucket exists; creates folder prefix placeholder if path contains slashes; uploads data to blob; attempts to make public and return public URL; falls back to 24-hour signed URL if public ACLs fail
- Dependencies: `google-cloud-storage==*`, standard library `datetime`, `os`

**`blackhawk.GiftCardGuru._stringify(response: Union[dict, str]) -> str`**
- Purpose: Formats assistant responses (dict or string) into readable text for Teams
- Implementation: If response is a dictionary, formats each key-value pair as "**key:**\n{value}" separated by blank lines; otherwise returns string representation
- Dependencies: Standard library only

**`blackhawk.GiftCardGuru.word_count_exceeded(text: str, word_count: str) -> Optional[str]`**
- Purpose: Validates whether text meets target word count within 15% tolerance
- Implementation: Splits text by whitespace to count words; compares actual count to target with ±15% bounds; returns feedback message if out of range (e.g., "Lengthen by N words" or "Shorten by N words"); returns None if within tolerance
- Dependencies: Standard library only

## Dependencies

- `qurrent==*` (implied from imports) - Qurrent OS framework providing Workflow, Agent, Teams integration, event system, decorators (@console_agent, @observable, @llmcallable), and configuration management
- `loguru==*` - Logging framework used throughout for structured logging
- `uvloop==*` - High-performance event loop for asyncio, used to run main() entry point
- `openai==*` - OpenAI client library for GPT-image-1 image generation API
- `google-cloud-storage==*` - Google Cloud Storage client for uploading and managing image files
- `google-cloud-secret-manager==*` (implied from imports) - GCP Secret Manager client for loading configuration secrets at startup
- `pyyaml==*` (implied from imports) - YAML parsing for configuration files and secret processing
- `requests==*` - HTTP client library for web scraping GiftCards.com
- `beautifulsoup4==*` - HTML parsing library for extracting structured data and product information from web pages
- `lxml_html_clean==*` - HTML sanitization and cleaning (likely used by BeautifulSoup)
- `brotli==*` - Brotli compression support for HTTP requests
- `zstandard==*` - Zstandard compression support for HTTP requests
- `fuzzywuzzy==*` - Fuzzy string matching (present in requirements.txt but not visibly used in analyzed code)
- `sendgrid==*` - SendGrid email API client (present in requirements.txt but not visibly used in analyzed code)
- `replicate==*` - Replicate AI model hosting API client (present in requirements.txt but not visibly used in analyzed code)
- `pandas==*` - Data analysis library (present in requirements.txt but not visibly used in analyzed code)
- `openpyxl==*` - Excel file handling (present in requirements.txt but not visibly used in analyzed code)

## Integrations

### Prebuilt: `qurrent.Teams`
- Required Config Section: `MICROSOFT_TEAMS`
- Required Keys:
    - `MICROSOFT_TEAMS_WEBHOOK_URL: str` - Webhook endpoint URL for receiving Teams messages and events

**Methods Used:**

**`await Teams.start(qconfig: QurrentConfig, webhook_endpoint: str) -> Teams`**
- Initializes and starts the Microsoft Teams integration
- Returns configured Teams instance for sending/receiving messages

**`await teams.link(workflow_instance_id: UUID, conversation_id: str)`**
- Links a workflow instance to a specific Teams conversation
- Enables routing of messages between the conversation and workflow

**`await teams.unlink(conversation_id: str)`**
- Unlinks workflow from conversation after workflow completion

**`await teams.send_message(conversation_id: str, message: str)`**
- Sends a message to the specified Teams conversation
- Supports plain text and HTML/Markdown formatting (e.g., for embedded images)

### Custom: `openai.OpenAI`
**Location:** External package `openai`, instantiated in `agents/assistant.py`  
**Type:** One-way (assistant makes requests; no inbound events)

**Config Section:** Environment (expects `OPENAI_API_KEY` from llm_keys secret)

**Methods:**

**`openai.images.generate(model: str, prompt: str, n: int, size: str)`**
- Performs: Generates AI images based on text prompt using OpenAI's image generation model
- Parameters:
    - `model`: "gpt-image-1"
    - `prompt`: Text description of desired image
    - `n`: Number of images to generate (1 or more)
    - `size`: Image dimensions ("1024x1024")
- Returns: Object with `data` array containing image results; each result has `b64_json` field with base64-encoded PNG

### Custom: `google.cloud.storage.Client`
**Location:** `utils/storage.py`  
**Type:** One-way (assistant uploads files; no inbound events)

**Config Section:** Environment (expects `GOOGLE_APPLICATION_CREDENTIALS` or ADC for authentication; `GOOGLE_CLOUD_PROJECT` for project ID; optional `GCS_BUCKET_NAME`)

**Methods:**

**`storage.Client()`**
- Initializes GCS client using Application Default Credentials

**`client.lookup_bucket(bucket_name: str) -> Optional[storage.Bucket]`**
- Checks if a GCS bucket exists
- Returns `Bucket` object if found, `None` otherwise

**`client.create_bucket(bucket_name: str) -> storage.Bucket`**
- Creates a new GCS bucket with the specified name

**`bucket.blob(object_path: str) -> storage.Blob`**
- Returns a Blob object representing an object in the bucket

**`blob.upload_from_string(data: bytes, content_type: str)`**
- Uploads binary data to GCS with specified content type

**`blob.make_public()`**
- Sets object ACL to public-read (may fail if uniform bucket-level access is enabled)

**`blob.generate_signed_url(expiration: timedelta) -> str`**
- Generates a time-limited signed URL for accessing the object

**`blob.public_url: str`**
- Property returning the public URL for the object (requires public ACL)

### Custom: GiftCards.com Web Scraper
**Location:** `utils/scraper.py`  
**Type:** One-way scheduled scraping (no API; extracts from public website)

**Config Section:** None (operates independently with hardcoded URL)

**Behavior:**
- Scheduled to run daily at 8:00 AM PST via `schedule_daily_scrape()` background task
- Fetches HTML from `https://www.giftcards.com/us/en/catalog/brands`
- Extracts initial product data from JSON-LD structured data and embedded JavaScript
- Makes paginated GraphQL queries to `https://www.giftcards.com/commerce/graphql` to fetch complete product catalog (40 products per page)
- Parses product names, available amounts, descriptions, canonical URLs, and inventory status
- Saves results to `data/giftcards_com_products.json` as JSON dictionary with product names as keys
- Runs in infinite loop with error handling; sleeps 60 seconds on error before retrying
- No events triggered; operates purely as a data refresh mechanism

### Custom: Google Cloud Secret Manager
**Location:** `load_secrets.py`  
**Type:** One-way startup configuration (no runtime interaction)

**Config Section:** Environment (expects `GOOGLE_CLOUD_PROJECT` and `GOOGLE_APPLICATION_CREDENTIALS` or ADC)

**Behavior:**
- Executed at container startup (not during workflow execution)
- Fetches three secrets from GCP Secret Manager: `customer_keys`, `llm_keys`, and `additional_keys`
- Parses each secret as YAML content
- Exports key-value pairs as environment variables
- Appends all secret contents to `config.yaml` file
- Terminates with error if any secret fetch fails
- No events or runtime methods; purely initialization logic
