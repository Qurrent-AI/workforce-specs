# Workforce Specification: GiftCardGuru

**Contributors:** alex, Alex Reents, augustfr, Alex McConville

## Overview

GiftCardGuru is a marketing co-pilot system for Blackhawk Network (GiftCards.com) that assists marketing professionals in creating persuasive, compliant, and conversion-oriented marketing copy for gift card products across multiple channels. The system helps marketing teams craft occasion-specific campaigns for ads, blogs, emails, social media, and internal product selection, while maintaining strict brand voice guidelines and compliance guardrails.

**Problem & Stakeholders:** Marketing teams at Blackhawk Network need to produce high-quality, brand-compliant marketing copy for hundreds of gift card products across different occasions (Back to School, Father's Day, holidays, etc.) and channels (performance ads, blog posts, emails, social media). The workforce serves marketing professionals who need to generate persuasive copy quickly while adhering to strict brand guidelines, avoiding superlatives, maintaining compliance with advertising standards, and ensuring accurate product information.

**Happy Path:** A marketing professional initiates a conversation via Microsoft Teams requesting specific marketing copy (e.g., "Write a 1500-word blog post about gift cards for Back to School"). The assistant analyzes the request, looks up relevant gift card products from the GiftCards.com inventory, and generates compliant marketing copy following brand voice and tone guidelines. If the user requests product links or details, the assistant retrieves canonical URLs and product information. For image generation requests, the assistant creates custom images and delivers them inline. The assistant automatically validates word count requirements and iteratively refines content until it meets specifications. The conversation continues until the user types "end" or the workflow times out after 15 minutes of inactivity.

**Value Proposition:** The workforce dramatically accelerates marketing content creation while ensuring consistent brand voice, compliance with advertising regulations, and accurate product information. It eliminates the need for marketers to manually look up product URLs, ensures copy meets exact word count requirements (±15% tolerance), and provides immediate access to a comprehensive gift card inventory. The system's deep knowledge of GiftCards.com brand guidelines (warm-but-precise tone, no superlatives, occasion-first persuasion) ensures all output is immediately usable without extensive review cycles.

## Custom Instructions
*FDE-provided instructions for how this particular workforce specification should be configured*
<!--
[Provide custom instructions here around how to understand and document this particular workforce]
-->

## Decision Audit

Documents the possible paths of workflow execution through the lens of decisions the workforce makes.

### Content Creation & Product Selection Decisions

- [1] **Determine Content Type and Requirements**
    - Inputs: User's natural language request describing desired marketing content (channel, occasion, length, specific requirements)
    - Outputs: Structured understanding of what content to create (blog post, ad copy, email, social taglines, product ranking); word count target if specified
    - Decision logic: The `Assistant` agent parses the user request to identify: (1) the marketing channel (performance ads, blog, email, social media, or internal selection/ranking), (2) the occasion or theme (Back to School, Father's Day, etc.), (3) any word count requirements, (4) specific constraints mentioned (e.g., "no emojis," "avoid shopping local"), and (5) required product inclusions. The agent's system prompt contains detailed channel-specific guidance that shapes how it interprets requests.
    - Logic location: internal prompt (`Assistant`)

- [2] **Decide Whether to Look Up Product Information**
    - Inputs: Parsed content requirements; assessment of whether specific product details or URLs are needed
    - Outputs: Decision to invoke product lookup actions or proceed directly to content generation
    - Decision logic: The agent determines whether the content requires specific product links or detailed product information. Product lookups are required when: (1) the user requests specific gift card brands to be included, (2) the content type requires product links (blog posts always link products, ads may link them), or (3) the agent needs to verify product availability and amounts. The system prompt explicitly mandates looking up products before linking to obtain canonical URLs.
    - Logic location: internal prompt (`Assistant`)

- [3] **Select Appropriate Gift Cards for Occasion**
    - Inputs: Content occasion/theme, available product inventory (400+ gift card products), target personas (parents, students, gamers, etc.)
    - Outputs: Curated list of 3-8 gift card products that fit the occasion
    - Decision logic: The agent applies product selection principles from its system prompt: (1) prioritize multi-brand cards (One4all, Cheers To You, Home Sweet Home) for versatility, (2) include distinct single-brand options covering different personas (gaming, outdoor, home improvement, coffee, beauty, movies, dining), (3) match products only when the occasion logic is strong, (4) ensure variety and breadth of appeal. For example, Back to School might include Amazon, Target, Apple, and Visa Virtual Account; Father's Day might include Home Depot, Bass Pro Shops, Starbucks, and DoorDash.
    - Logic location: internal prompt (`Assistant`)

- [4] **Retrieve Product Details and URLs**
    - Inputs: Selected gift card product names
    - Outputs: LLM-invoked `lookup_gift_card` action for each product; returned data includes product amounts (e.g., $25, $50, $100), description, canonical purchase URL
    - Decision logic: When the agent determines a product needs to be linked or referenced with specific details, it invokes the `lookup_gift_card` action. The action searches the product inventory dictionary (loaded from `giftcards_com_products.json`) for an exact name match and returns the product object or a "not found" message. The agent is instructed to never guess or invent URLs.
    - Logic location: internal prompt (`Assistant`); internal code (action implementation)

- [5] **Determine Image Generation Requirement**
    - Inputs: User request content; analysis of whether visual assets are needed
    - Outputs: Decision to generate images or proceed with text-only content
    - Decision logic: The agent invokes image generation when: (1) the user explicitly requests images (e.g., "create an image of...," "generate a graphic"), (2) the content type benefits from visual assets (social media posts may trigger this), or (3) the agent determines an image would enhance the deliverable. The system prompt does not contain specific guidance on when to generate images, leaving this as an LLM judgment call based on user intent.
    - Logic location: internal prompt (`Assistant`)

- [6] **Generate Marketing Images**
    - Inputs: Image generation prompt derived from user request and content context; number of images requested (default 1)
    - Outputs: LLM-invoked `generate_image` action; generated image uploaded to Google Cloud Storage; public URL returned; image rendered inline in Teams
    - Decision logic: When image generation is triggered, the agent constructs a detailed prompt for the image generation model based on the marketing content requirements. The agent sends a status message ("Generating an image..." or "Generating N images...") to indicate progress. After generation, the image is automatically uploaded to cloud storage and displayed inline in the Teams conversation using HTML image tags.
    - Logic location: internal prompt (`Assistant`); internal code (action implementation and cloud upload)

### Content Quality & Compliance Decisions

- [7] **Apply Brand Voice and Tone Guidelines**
    - Inputs: Draft content generated by the agent
    - Outputs: Content that adheres to GiftCards.com brand personality and voice
    - Decision logic: The agent applies comprehensive brand guidelines embedded in its system prompt: (1) brand name must always be "GiftCards.com" (camel case with dot com), (2) tone is warm, savvy, practical, lightly playful—"fun aunt energy" without being snarky or cutesy, (3) conversational and crisp with strong verbs and short sentences, (4) default to second person ("you") or neutral voice, (5) no emojis, no hashtags, no exclamation stacks. These rules are enforced during content generation through the LLM's training on the system prompt.
    - Logic location: internal prompt (`Assistant`)

- [8] **Enforce Compliance and Risk Guardrails**
    - Inputs: Generated marketing content; compliance rules
    - Outputs: Content free of prohibited claims and language
    - Decision logic: The agent enforces strict compliance rules: (1) no superlatives (e.g., "best," "perfect," "#1"), (2) avoid unverifiable claims, (3) only state features explicitly provided in the brief, (4) age-appropriate framing (don't glamorize alcohol, never imply suitability for minors), (5) inclusive and respectful without stereotypes. The agent performs internal self-review against these criteria before finalizing content. If the agent detects compliance issues, it revises the content automatically.
    - Logic location: internal prompt (`Assistant`)

- [9] **Structure Content by Channel**
    - Inputs: Content type (performance ads, blog, email, social); channel-specific guidelines
    - Outputs: Content formatted and structured appropriately for the target channel
    - Decision logic: The agent applies different structural rules based on channel: **Performance Ads** - ultra-concise, one clear benefit, persona coverage via variants, one short CTA; **Blog Posts** - focused title, tight intro, scannable subheads, numbered/bulleted benefits, ~5 occasion-specific reasons, early and end CTAs; **Email** - compact, direct, skimmable, one idea per line, one CTA, no emojis; **Social Taglines** - at least 5 one-liners that stand alone, light brand-fit puns allowed, tied to occasion, no hashtags/emojis; **Internal Selection/Ranking** - rank by occasion fit and variety, lead with multi-brand options, cover distinct personas.
    - Logic location: internal prompt (`Assistant`)

- [10] **Validate Word Count Requirements**
    - Inputs: Generated content text; user-specified target word count
    - Outputs: Validation result (pass/fail); feedback message if adjustment needed
    - Decision logic: When a user specifies a word count (e.g., "write a 1500-word blog post"), the agent returns the target in the `word_count` JSON field. The workflow then counts actual words in the response and checks if it falls within ±15% tolerance (defined by `WORD_COUNT_TOLERANCE = 0.15`). If the word count is too low, the workflow returns a message like "Your response has 1200 words but needs 1500. Lengthen your response by approximately 300 more words." If too high, similar feedback is provided to shorten. This triggers the agent to regenerate content with the adjusted requirement.
    - Logic location: internal code (workflow validates word count); internal prompt (`Assistant` regenerates with feedback)

- [11] **Decide Whether to Continue Refining Content**
    - Inputs: Word count validation feedback; iteration count
    - Outputs: Either regenerated content or final content with explanation
    - Decision logic: When word count validation fails, the workflow sends the feedback message back to the agent as a user message and re-invokes the agent to regenerate content. This loop continues until the word count requirement is met or the agent determines it cannot meet the requirement. If struggling after multiple attempts, the agent sets `word_count` to an empty string and explains to the user why the requirement cannot be met. The system prompt instructs the agent to persist but acknowledge limitations.
    - Logic location: internal code (loop control); internal prompt (`Assistant` decides when to stop trying)

### Conversation Management Decisions

- [12] **Determine If Conversation Should Continue or End**
    - Inputs: User message content
    - Outputs: Either continue conversation or end workflow
    - Decision logic: The workflow checks if the user message is exactly "end" (case-insensitive). If so, it sends "Conversation ended." and completes the workflow. Otherwise, it continues processing the message. This is a simple deterministic check in the main conversation loop.
    - Logic location: internal code

- [13] **Decide Whether to Send Progress/Status Messages**
    - Inputs: Action being performed (product lookup, image generation)
    - Outputs: Informational messages sent to Teams (e.g., "_Looking up more details about Starbucks..._", "_Generating an image..._")
    - Decision logic: When the agent invokes actions that may take time, it sends immediate status messages to provide feedback to the user. Product lookups trigger messages like "_Looking up more details about [card_name]..._". Image generation triggers "_Generating an image..._" or "_Generating N images..._" based on the number requested. These messages use italics (markdown `_text_`) to distinguish them as system status rather than final content.
    - Logic location: internal code (within action implementations)

### System Operation Decisions

- [14] **Schedule Daily Product Inventory Updates**
    - Inputs: Current time in PST; target time of 8:00 AM PST
    - Outputs: Scheduled execution of web scraping to refresh product inventory
    - Decision logic: A background task runs continuously calculating the time until the next 8:00 AM PST. When that time arrives, it triggers the `scrape_giftcards_com` utility to fetch the latest product catalog from GiftCards.com. If the current time is already past 8:00 AM today, it schedules for 8:00 AM tomorrow. After each successful scrape, it recalculates and waits for the next 8:00 AM PST. If an error occurs, it waits 60 seconds and tries again.
    - Logic location: internal code (scheduler loop in `schedule_daily_scrape`)

- [15] **Handle Workflow Timeout**
    - Inputs: Workflow running time; timeout threshold of 15 minutes
    - Outputs: Timeout message sent to user; workflow closed with "completed" status
    - Decision logic: The main event handler wraps workflow execution in a 15-minute timeout (defined by `TIMEOUT_MINUTES = 15`). If the workflow doesn't receive user input or complete within 15 minutes, an `asyncio.TimeoutError` is raised. The error handler sends the message "The workflow has ended after 15 minutes of inactivity." to the Teams conversation and closes the workflow gracefully.
    - Logic location: internal code (timeout wrapper in `handle_event`)

- [16] **Handle Unexpected Workflow Errors**
    - Inputs: Exception raised during workflow execution
    - Outputs: User-friendly error message sent to Teams; error logged to console; workflow closed with "failed" status
    - Decision logic: If any exception occurs during workflow execution (other than timeout), the error handler catches it, logs the full traceback, and sends a generic message to the user: "The workflow failed unexpectedly. The Qurrent team has been notified. In the meantime, please try again." This prevents exposing technical details to end users while preserving debugging information in logs.
    - Logic location: internal code (exception handler in `handle_event`)

## Agent Design

### Console Agents

#### `assistant`
**Type:** Console Agent (method with `@console_agent` decorator)
**Purpose:** Main orchestration point for handling all user interactions with the GiftCardGuru marketing co-pilot
**Docstring:** "Main assistant agent responsible for handling user input"

**Observable Tasks:**

**`handle_user_input(input_message: str, conversation_id: str)`**
- `@observable` decorator
- Docstring: "Handling a request from the user"
- Purpose: Orchestrates the complete request-response cycle for marketing content generation, including LLM invocation, action handling, word count validation, and message delivery
- Technical Agent Calls: 
  - Appends user message to `assistant_agent.message_thread`
  - Invokes `assistant_agent()` for LLM turn to generate marketing content
  - Calls `assistant_agent.get_rerun_responses(timeout=120)` to retrieve results from any LLM-invoked actions (product lookups, image generation)
- Integration Calls: 
  - Calls `teams.send_message(conversation_id, message)` to deliver generated content, status updates, and warnings to the user
- Deterministic Logic:
  - Uses `_stringify()` helper to convert dict responses to formatted markdown strings (joins dict entries with `**key:**\nvalue` pattern)
  - Invokes `word_count_exceeded()` to validate content length against user requirements
  - If word count validation fails, sends warning message "_Rewriting response to meet [N] (± 15%) word count requirement..._" and returns validation feedback to trigger agent regeneration
  - Accumulates all responses (initial + rerun results) into `observable_output` for console logging
- Observability Output: `save_to_console(type='observable_output', content=observable_output)` captures complete interaction trace including all generated content and status messages
- Returns: `None` if content is acceptable and sent; validation feedback string if word count needs adjustment (triggers agent re-invocation in main loop)

### Technical Agents

#### `Assistant`
**Type:** Technical Agent (extends `Agent` class)
**Pattern:** Orchestrator with Agentic Search capabilities
**Purpose:** LLM-powered marketing copywriter that generates compliant, persuasive copy for GiftCards.com across multiple channels while autonomously looking up product information and generating images as needed
**LLM:** gemini/gemini-2.5-flash (primary), gpt-5 (fallback), standard mode, temp=0, timeout=120 seconds

**Prompt Strategy:**
- Comprehensive system prompt defining role as "creative-but-precise marketing writer for GiftCards.com"
- Detailed brand identity rules (exact naming: "GiftCards.com", warm/savvy/practical personality, conversational tone)
- Strict compliance guardrails (no superlatives, no unverifiable claims, age-appropriate content, inclusive language)
- Occasion-first persuasion framework (lead with the moment, tie benefits to timing/flexibility/choice)
- Channel-specific guidance for ads, blogs, emails, social media, and internal selection with distinct structural requirements
- Product selection principles emphasizing multi-brand versatility and persona coverage
- Linking mandate: MUST look up products before linking to obtain canonical URLs
- Output format rules requiring JSON with `{"response": "<string>", "word_count": "<target or empty>", "actions": [...]}`
- Paraphrase mandate: never duplicate supplied product descriptions verbatim
- Internal self-review checklist against quality and compliance criteria
- Context: accumulates across conversation (does not reset message thread between turns)
- JSON Response Structure: `{"response": "<marketing copy as single string>", "word_count": "" or "<user-specified target>", "actions": [{"name": "lookup_gift_card" or "generate_image", "args": {...}}]}`

**Instance Attributes:**
- `teams: Teams` - Integration for sending messages to Microsoft Teams conversations
- `conversation_id: str` - ID of the Teams conversation for delivering status messages and images
- `openai: OpenAI` - Client for generating images via OpenAI image generation API
- `product_inventory: Dict[str, Dict]` - Dictionary mapping gift card names to product data (amounts, description, URL, stock status); loaded from JSON file at initialization

**Create Parameters:**
- `yaml_config_path: str` - Path to `./agents/config/assistant.yaml` containing LLM configuration
- `workflow_instance_id: UUID` - Unique identifier for the workflow instance
- `teams: Teams` - Teams integration instance
- `conversation_id: str` - Teams conversation ID for messaging
- `product_inventory_file: str` - Filename for product inventory JSON (typically `"giftcards_com_products.json"`)

#### LLM Callables

**`lookup_gift_card(card_name: str) -> Union[str, Dict]`**
- `@llmcallable(rerun_agent=True, append_result=True)` - result automatically appended to message thread for LLM context
- Docstring Args: `card_name (str): The name of the gift card to lookup.`
- Purpose: Retrieves specific gift card amount options, descriptions, and canonical purchase URLs from the product inventory; enables agent to provide accurate product information and links in marketing copy
- Integration usage:
  - Calls `teams.send_message(conversation_id, f"_Looking up more details about {card_name}..._")` to provide user feedback
- Returns: If product found, returns dict with keys `{"name", "amounts": [50.0, 100.0, ...], "description": "...", "url": "https://...", "out_of_stock": bool}`; if not found, returns string `"Product {card_name} not found"`
- Error Handling: No explicit try/except; relies on dictionary `.get()` with default value

**`generate_image(prompt: str, num_images: int = 1) -> str`**
- `@llmcallable(rerun_agent=True, append_result=True)` - result automatically appended to message thread
- Docstring Args: `prompt (str): A prompt for the image generation.`, `num_images (int): The number of images to generate.`
- Purpose: Generates custom marketing images based on text prompts; uploads images to Google Cloud Storage; displays images inline in Teams conversation
- Integration usage:
  - Calls `teams.send_message()` to send progress message ("_Generating an image..._" or "_Generating {num_images} images..._")
  - Calls `openai.images.generate(model="gpt-image-1", prompt=prompt, n=num_images, size="1024x1024")` to generate images
  - Calls `upload_bytes_to_gcs(object_path=f"images/{uuid}.png", data=image_bytes, content_type="image/png")` to upload and get public URL
  - Calls `teams.send_message(conversation_id, f"<img src='{public_url}' style='max-width: 100%; height: auto;'><br><br>")` to display image inline
- Returns: String message `"The image has been generated and sent to the user. Do not respond wth anything else."` instructing the agent not to add additional commentary
- Manual Message Thread: N/A (append_result=True)
- Error Handling: No explicit try/except; exceptions would propagate to workflow error handler

## Happy Path Call Stack

**Note:** Clearly indicate which agents are Technical Agents (TA) vs Console Agents (CA) in the call stack.

```text
→ START EVENT: events.TeamsMessage with {"conversation_id": "abc123", "message": "Write a 1500 word blog post about gift cards for Back to School"}
  ├─ handle_event() creates GiftCardGuru workflow instance
  │  ├─ GiftCardGuru.create()
  │  │  └─ Assistant.create() [TA instantiation]
  │  │     ├─ Loads product inventory from data/giftcards_com_products.json
  │  │     └─ Substitutes {product_inventory} variable in system prompt with product names
  │  └─ teams.link(workflow_instance_id, conversation_id) → establishes two-way link
  │
  ├─ blackhawk_workflow.run(event) wrapped in 15-minute timeout
  │  └─ Main conversation loop (while True)
  │     ├─ user_message = "User input: Write a 1500 word blog post about gift cards for Back to School"
  │     │
  │     ├─ @console_agent: blackhawk_workflow.assistant(user_message, conversation_id) [CA]
  │     │  └─ @observable: blackhawk_workflow.handle_user_input(user_message, conversation_id) [CA observable]
  │     │     ├─ assistant_agent.message_thread.append(Message(role="user", content=user_message))
  │     │     │
  │     │     ├─ assistant_agent() [TA LLM turn - Assistant orchestrator agent]
  │     │     │  │  (Agent analyzes request, determines it's a blog post requiring product links)
  │     │     │  └─ Returns: {"response": "", "word_count": "1500", "actions": [
  │     │     │       {"name": "lookup_gift_card", "args": {"card_name": "Amazon"}},
  │     │     │       {"name": "lookup_gift_card", "args": {"card_name": "Target"}},
  │     │     │       {"name": "lookup_gift_card", "args": {"card_name": "Apple"}},
  │     │     │       {"name": "lookup_gift_card", "args": {"card_name": "Visa® Virtual Account"}}
  │     │     │     ]}
  │     │     │
  │     │     ├─ assistant_agent.get_rerun_responses(timeout=120) [TA action execution + rerun]
  │     │     │  ├─ @llmcallable: assistant_agent.lookup_gift_card("Amazon") [TA action]
  │     │     │  │  ├─ teams.send_message(conversation_id, "_Looking up more details about Amazon..._")
  │     │     │  │  └─ Returns: {"name": "Amazon", "amounts": [25.0, 50.0, 100.0], "description": "...", "url": "https://...", "out_of_stock": false}
  │     │     │  │
  │     │     │  ├─ @llmcallable: assistant_agent.lookup_gift_card("Target") [TA action]
  │     │     │  │  └─ (similar execution pattern)
  │     │     │  │
  │     │     │  ├─ @llmcallable: assistant_agent.lookup_gift_card("Apple") [TA action]
  │     │     │  │  └─ (similar execution pattern)
  │     │     │  │
  │     │     │  ├─ @llmcallable: assistant_agent.lookup_gift_card("Visa® Virtual Account") [TA action]
  │     │     │  │  └─ (similar execution pattern)
  │     │     │  │
  │     │     │  └─ assistant_agent() [TA LLM rerun after all lookups]
  │     │     │     │  (Agent now has all product data in context, generates full blog post)
  │     │     │     └─ Returns: {"response": "<1500-word blog post with product links>", "word_count": "1500", "actions": []}
  │     │     │
  │     │     ├─ _stringify(response["response"]) → message_to_send = "<formatted blog post>"
  │     │     │
  │     │     ├─ word_count_exceeded(message_to_send, "1500") → validates word count
  │     │     │  └─ Returns: None (word count is within ±15% tolerance)
  │     │     │
  │     │     ├─ teams.send_message(conversation_id, message_to_send) → delivers blog post
  │     │     │
  │     │     └─ save_to_console(type="observable_output", content=observable_output)
  │     │
  │     ├─ Loop continues: user_message = None
  │     └─ ingress.get_workflow_event(workflow_instance_id) → waits for next Teams message
  │
→ INGRESS EVENT: TeamsMessage {"conversation_id": "abc123", "message": "Generate an image of a student with a backpack"}
  │  ├─ next_event received in conversation loop
  │  │  └─ user_message = "User input: Generate an image of a student with a backpack"
  │  │
  │  ├─ @console_agent: blackhawk_workflow.assistant(user_message, conversation_id) [CA]
  │  │  └─ @observable: blackhawk_workflow.handle_user_input(user_message, conversation_id) [CA observable]
  │  │     ├─ assistant_agent.message_thread.append(Message(role="user", content=user_message))
  │  │     │
  │  │     ├─ assistant_agent() [TA LLM turn - Assistant]
  │  │     │  └─ Returns: {"response": "", "word_count": "", "actions": [
  │  │     │       {"name": "generate_image", "args": {"prompt": "A cheerful student wearing a colorful backpack...", "num_images": 1}}
  │  │     │     ]}
  │  │     │
  │  │     ├─ assistant_agent.get_rerun_responses(timeout=120) [TA action execution + rerun]
  │  │     │  ├─ @llmcallable: assistant_agent.generate_image(prompt="...", num_images=1) [TA action]
  │  │     │  │  ├─ teams.send_message(conversation_id, "_Generating an image..._")
  │  │     │  │  ├─ openai.images.generate(model="gpt-image-1", prompt="...", n=1, size="1024x1024") → image data
  │  │     │  │  ├─ upload_bytes_to_gcs(object_path="images/12345.png", data=image_bytes, content_type="image/png") → public URL
  │  │     │  │  ├─ teams.send_message(conversation_id, "<img src='...' style='max-width: 100%; height: auto;'><br><br>")
  │  │     │  │  └─ Returns: "The image has been generated and sent to the user. Do not respond wth anything else."
  │  │     │  │
  │  │     │  └─ assistant_agent() [TA LLM rerun]
  │  │     │     └─ Returns: {"response": "<brief confirmation>", "word_count": "", "actions": []}
  │  │     │
  │  │     ├─ teams.send_message(conversation_id, message_to_send) → delivers confirmation
  │  │     └─ save_to_console(type="observable_output", content=observable_output)
  │  │
  │  └─ Loop continues waiting for next message
  │
→ INGRESS EVENT: TeamsMessage {"conversation_id": "abc123", "message": "end"}
  │  ├─ next_event received in conversation loop
  │  ├─ user_message = "end"
  │  ├─ Condition check: message.lower() == "end" → True
  │  ├─ teams.send_message(conversation_id, "Conversation ended.")
  │  └─ return (exits run method)
  │
→ WORKFLOW COMPLETE: User sent "end" message or 15-minute timeout reached
  ├─ blackhawk_workflow.close(status="completed")
  └─ teams.unlink(conversation_id)

→ BACKGROUND PROCESS (runs continuously, independent of conversation flow):
  └─ schedule_daily_scrape() [spawned task]
     ├─ Calculates time until next 8:00 AM PST
     ├─ asyncio.sleep(seconds_until_target)
     ├─ scrape_giftcards_com(PRODUCT_INVENTORY_FILE) [utility function]
     │  ├─ create_session() → requests session with browser headers
     │  ├─ fetch_html("https://www.giftcards.com/us/en/catalog/brands", query) → initial HTML
     │  ├─ fetch_all_plp_items(session, html_text) → GraphQL paginated fetch
     │  │  ├─ plp_total_pages_from_html(html_text) → extract total pages
     │  │  └─ For each page: graphql_fetch_plp_page(session, page_index) → collect all product items
     │  ├─ normalize_plp_items_to_products(all_plp_items) → convert to product dict format
     │  └─ save_products_to_json(products, file_name) → write to data/giftcards_com_products.json
     └─ Loop repeats for next day
```

## Data & Formats

### Referenced Documents Inventory and Input Data

- **Product Inventory JSON** (`giftcards_com_products.json`)
    - Format: JSON dictionary with gift card names as keys
    - Source: Daily automated scrape of GiftCards.com website (https://www.giftcards.com/us/en/catalog/brands) via GraphQL API
    - Intended Use: Loaded at Assistant agent creation; provides canonical product data for lookup actions
    - Structure: Each product entry contains `{"name": str, "amounts": [float, ...], "description": str, "url": str, "out_of_stock": bool}`
    - Size: 400+ gift card products
    - Update Schedule: Refreshed daily at 8:00 AM PST via background scraper

- **User Requests** (Microsoft Teams messages)
    - Format: Plain text natural language messages
    - Source: Marketing professionals via Microsoft Teams chat
    - Intended Use: Parsed by Assistant agent to determine content requirements, channel, occasion, word count, and constraints
    - Common Patterns: 
        - "Write a [word count] word blog post about [occasion]"
        - "Create ad copy for [product] targeting [persona]"
        - "Generate [number] social taglines for [occasion]"
        - "Rank these products for [occasion]: [product list]"
        - "Generate an image of [description]"

### Example Output Artifacts

- **Blog Posts**
    - Type: Marketing content
    - Format: Markdown-formatted text with headings, lists, and hyperlinks
    - Recipients: Marketing team members (delivered via Teams)
    - Contents: 
        - Focused title referencing occasion
        - Tight introductory paragraph establishing relevance
        - Scannable subheadings organizing benefits
        - 5+ numbered or bulleted occasion-specific reasons to buy gift cards
        - Multiple product recommendations with Markdown links to canonical URLs
        - Persona-specific scenarios (parents, students, teachers, etc.)
        - Call-to-action prompts (e.g., "Shop GiftCards.com")
        - Typical length: 1000-2000 words based on user specification

- **Performance Ad Copy**
    - Type: Marketing content
    - Format: Plain text or simple Markdown
    - Recipients: Marketing team members (delivered via Teams)
    - Contents:
        - Ultra-concise messaging (typically 25-75 words)
        - One clear benefit tied to occasion
        - Multiple variants covering different personas
        - Single short call-to-action
        - Optional product links

- **Email Marketing Copy**
    - Type: Marketing content
    - Format: Plain text or simple Markdown with subject line
    - Recipients: Marketing team members (delivered via Teams)
    - Contents:
        - Benefit-led subject line (no superlatives or clickbait)
        - Compact, skimmable body with one idea per line
        - Single call-to-action
        - Optional product links
        - No emojis or first-person language

- **Social Media Taglines**
    - Type: Marketing content
    - Format: Plain text list
    - Recipients: Marketing team members (delivered via Teams)
    - Contents:
        - Minimum 5 one-liner taglines
        - Each line stands alone (suitable for graphics)
        - Light, brand-fit puns included in some variants
        - Tied to specific occasion and benefit
        - No hashtags or emojis

- **Product Rankings/Recommendations**
    - Type: Internal selection guidance
    - Format: Structured text with rationale
    - Recipients: Marketing team members (delivered via Teams)
    - Contents:
        - Ranked list of gift card products
        - Rationale for each selection (occasion fit, persona appeal, variety)
        - Multi-brand cards prioritized for flexibility
        - Single-brand cards covering distinct use cases
        - Explicit note if no products fit the occasion well

- **Generated Images**
    - Type: Visual marketing asset
    - Format: PNG images (1024x1024 pixels)
    - Recipients: Marketing team members (displayed inline in Teams)
    - Delivery: Uploaded to Google Cloud Storage bucket; rendered inline via HTML `<img>` tags
    - Contents: Custom images generated based on text prompts, typically featuring lifestyle scenarios, products, or occasion-specific themes
    - Storage Location: GCS bucket `blackhawk_{environment}` under `images/` prefix with UUID filenames
    - Access: Public URLs (24-hour signed URLs if public access restricted)

## Integrations

### Prebuilt: `qurrent.Teams`
- Required Config Section: `MICROSOFT_TEAMS_WEBHOOK_URL`
- Required Keys:
    - `MICROSOFT_TEAMS_WEBHOOK_URL: str` - Webhook endpoint for Microsoft Teams integration

**Methods Used:**

**`link(workflow_instance_id: UUID, conversation_id: str) -> None`**
- Performs: Establishes two-way link between workflow instance and Teams conversation, enabling message routing
- Behavior: Allows workflow to receive ingress events from the specific conversation; ensures messages are routed correctly

**`unlink(conversation_id: str) -> None`**
- Performs: Removes link between workflow instance and Teams conversation when workflow completes
- Behavior: Cleanup operation ensuring conversation is no longer routed to completed workflow instance

**`send_message(conversation_id: str, message: str) -> None`**
- Performs: Sends text or HTML message to specified Teams conversation
- Behavior: Delivers generated marketing content, status updates, warnings, error messages, and inline images to the user
- Sample Usage:
    - Content delivery: `teams.send_message(conversation_id, "<1500-word blog post>")`
    - Status updates: `teams.send_message(conversation_id, "_Looking up more details about Amazon..._")`
    - Warnings: `teams.send_message(conversation_id, "Rewriting response to meet 1500 (± 15%) word count requirement...")`
    - Images: `teams.send_message(conversation_id, "<img src='https://...' style='max-width: 100%; height: auto;'><br><br>")`

### Prebuilt: `qurrent.Ingress`
- Required Config Section: `INGRESS`
- Required Keys: (Configuration details managed by Qurrent framework)

**Methods Used:**

**`get_start_event(use_snapshots: bool = False) -> Tuple[events.TeamsMessage, Any]`**
- Performs: Retrieves initial TeamsMessage event that triggers new workflow instance creation
- Behavior: Blocks until a new conversation starts in Teams; returns event containing `conversation_id` and initial `message`
- Returns: Tuple of (event, metadata)

**`get_workflow_event(workflow_instance_id: UUID) -> events.TeamsMessage`**
- Performs: Retrieves next TeamsMessage event for a specific workflow instance during conversation
- Behavior: Blocks until user sends next message in linked Teams conversation; enables conversational loop
- Returns: Event containing `conversation_id` and `message`

### External: OpenAI Image Generation API
**Integration Type:** External API (via `openai` Python client)
**Purpose:** Generate custom marketing images based on text prompts

**Configuration:**
- Requires: `OPENAI_API_KEY` environment variable (loaded via secret management)
- Client instantiation: `OpenAI()` (uses environment variable automatically)

**Method:**

**`openai.images.generate(model: str, prompt: str, n: int, size: str) -> ImagesResponse`**
- Performs: Generates AI images based on text prompt
- Parameters:
    - `model`: "gpt-image-1" (OpenAI's image generation model)
    - `prompt`: Detailed text description of desired image
    - `n`: Number of images to generate (typically 1, can be multiple)
    - `size`: Image dimensions ("1024x1024")
- Returns: Response object with `data` array containing `b64_json` (base64-encoded PNG data)
- Usage Pattern: Called within `generate_image` LLM callable; base64 data decoded and uploaded to GCS

### External: Google Cloud Storage
**Integration Type:** External API (via `google-cloud-storage` Python client)
**Purpose:** Store and serve generated images with public URLs

**Configuration:**
- Environment Variables:
    - `GOOGLE_CLOUD_PROJECT`: GCP project ID (e.g., "blackhawk-dev-08272025")
    - `GCS_BUCKET_NAME` (optional): Custom bucket name; defaults to `blackhawk_{environment}`
    - `ENVIRONMENT` (optional): Environment name (development/production); defaults to "development"
- Authentication: Uses Application Default Credentials (ADC) or service account key file

**Methods:**

**`storage.Client() -> storage.Client`**
- Performs: Creates authenticated GCS client
- Behavior: Uses environment credentials; no explicit parameters needed

**`client.lookup_bucket(bucket_name: str) -> Optional[storage.Bucket]`**
- Performs: Checks if bucket exists
- Returns: Bucket object if exists, None otherwise

**`client.create_bucket(bucket_name: str) -> storage.Bucket`**
- Performs: Creates new GCS bucket if it doesn't exist
- Behavior: One-time operation during first image upload

**`bucket.blob(object_path: str) -> storage.Blob`**
- Performs: Creates blob reference for object path
- Returns: Blob object for upload/download operations

**`blob.upload_from_string(data: bytes, content_type: str) -> None`**
- Performs: Uploads bytes data to GCS
- Parameters: Binary data and MIME type (e.g., "image/png")

**`blob.make_public() -> None`**
- Performs: Sets blob to publicly readable
- Behavior: Attempts to set public ACL; falls back to signed URL if restricted

**`blob.public_url -> str`**
- Returns: Public HTTPS URL for blob

**`blob.generate_signed_url(expiration: timedelta) -> str`**
- Performs: Generates time-limited signed URL (fallback when public ACLs disabled)
- Parameters: Expiration time (24 hours)
- Returns: Signed URL valid for specified duration

## Utils

### Web Scraping (`utils/scraper.py`)

**Purpose:** Automatically fetch and parse the complete GiftCards.com product catalog to maintain up-to-date inventory for the Assistant agent.

**`scrape_giftcards_com(file_name: str = "giftcards_com_products.json") -> None`**
- Purpose: Main orchestration function that scrapes GiftCards.com and saves product inventory to JSON
- Implementation: 
    1. Creates HTTP session with browser-like headers to avoid bot detection
    2. Fetches initial HTML page from https://www.giftcards.com/us/en/catalog/brands
    3. Calls `fetch_all_plp_items()` to retrieve all products via GraphQL pagination
    4. Normalizes product data with `normalize_plp_items_to_products()`
    5. Saves to `data/{file_name}` with `save_products_to_json()`
- Dependencies: `requests`, `beautifulsoup4`, `lxml_html_clean`
- Error Handling: Logs errors and continues; called daily by scheduler

**`fetch_all_plp_items(session: requests.Session, html_text: str) -> list[dict]`**
- Purpose: Fetch all product listings from GiftCards.com GraphQL API across multiple pages
- Implementation:
    1. Extracts total page count from initial HTML using `plp_total_pages_from_html()`
    2. Iterates through pages 1 to N
    3. For each page, calls `graphql_fetch_plp_page()` to retrieve product data
    4. Aggregates all product items from paginated responses
- Returns: List of raw product dictionaries from GraphQL

**`graphql_fetch_plp_page(session: requests.Session, page_index: int, page_size: int = 40, category_key: str = "brands") -> dict`**
- Purpose: Execute GraphQL query to fetch one page of product listings
- Implementation:
    - POST to https://www.giftcards.com/commerce/graphql
    - Uses realistic headers including store ID, operation type, caller ID, and anti-bot headers
    - Query fetches: product names, URLs, amounts, descriptions, images, inventory status, categories
    - Handles configurable products with variants and giftcard amount options
- Returns: GraphQL response JSON with nested product data structure

**`normalize_plp_items_to_products(plp_items: list[dict]) -> list[dict]`**
- Purpose: Transform raw GraphQL product data into simplified, consistent format
- Implementation:
    - Extracts product URL from `url_key` field
    - Parses HTML descriptions to plain text with `normalize_text_html_to_plain()`
    - Extracts gift card amounts from variants using `extract_giftcard_amounts()`
    - Checks inventory availability with `check_inventory_availability()`
- Returns: List of dicts with keys `{name, amounts, description, url, out_of_stock}`

**`extract_giftcard_amounts(item: dict) -> list[float]`**
- Purpose: Extract all available dollar amounts for a gift card from product variants
- Implementation: Navigates nested structure `variants[].product.giftcard_amounts[].value`; converts to floats and sorts
- Returns: Sorted list of unique amounts (e.g., `[25.0, 50.0, 100.0, 250.0]`)

**`check_inventory_availability(item: dict) -> bool`**
- Purpose: Determine if any product variant has inventory in stock
- Implementation: Checks if any variant has `product.has_inventory == True`
- Returns: True if available, False if out of stock

**`save_products_to_json(products: list[dict], file_name: str) -> None`**
- Purpose: Save product list to JSON file in data directory as dictionary keyed by product name
- Implementation:
    - Converts list to dict with product names as keys
    - Creates `data/` directory if needed
    - Writes formatted JSON with 2-space indentation and Unicode support
- Output Format: `{"Product Name": {"name": "...", "amounts": [...], ...}, ...}`

**`create_session() -> requests.Session`**
- Purpose: Create HTTP session with browser-like headers to avoid bot detection
- Implementation: Sets realistic Chrome browser headers including User-Agent, Accept encodings, Sec-Fetch headers, and Referer
- Returns: Configured requests.Session instance

**`build_graphql_headers() -> dict`**
- Purpose: Build headers specifically for GraphQL API requests
- Implementation: Includes store identifier ("gift_cards_us_en"), operation type, caller ID, and anti-bot client ID
- Returns: Header dictionary for POST requests to GraphQL endpoint

### Cloud Storage (`utils/storage.py`)

**Purpose:** Upload generated images to Google Cloud Storage and retrieve public URLs for embedding in Teams messages.

**`upload_bytes_to_gcs(object_path: str, data: bytes, *, content_type: str = "application/octet-stream", bucket_name: Optional[str] = None, make_public: bool = True) -> str`**
- Purpose: Upload binary data to GCS and return accessible URL
- Implementation:
    1. Gets or creates bucket using `get_or_create_bucket()`
    2. Ensures parent "folder" exists with `_ensure_prefix_exists()`
    3. Uploads data with `blob.upload_from_string()`
    4. Attempts to make public with `blob.make_public()`
    5. Returns `blob.public_url` if successful
    6. Falls back to 24-hour signed URL if public ACLs disabled
- Dependencies: `google-cloud-storage`
- Returns: HTTPS URL (public or signed) for accessing uploaded file

**`get_or_create_bucket(bucket_name: Optional[str] = None) -> storage.Bucket`**
- Purpose: Retrieve existing GCS bucket or create it if needed
- Implementation:
    1. Resolves bucket name from parameter or default (`blackhawk_{environment}`)
    2. Checks existence with `client.lookup_bucket()`
    3. Creates bucket if not found with `client.create_bucket()`
- Returns: GCS Bucket object ready for upload operations

**`_ensure_prefix_exists(bucket: storage.Bucket, prefix: str) -> None`**
- Purpose: Create "folder" placeholder in GCS (GCS is flat but uses prefix convention)
- Implementation: Creates zero-length object with trailing slash (e.g., `images/`) with content type "application/x-directory"
- Side Effects: Makes prefix visible in GCS console and tools

**`_get_environment() -> str`**
- Purpose: Determine current environment (development/production)
- Implementation: Reads `ENVIRONMENT` env var, defaults to "development", converts to lowercase
- Returns: Environment name string

**`_get_default_bucket_name() -> str`**
- Purpose: Construct default bucket name based on environment
- Implementation: Returns `GCS_BUCKET_NAME` env var if set, otherwise `blackhawk_{environment}`
- Returns: Bucket name string (e.g., "blackhawk_development")

## Directory Structure

```text
blackhawk-pilot/
    agents/
        assistant.py            # Assistant technical agent (marketing copywriter)
        config/
            assistant.yaml      # LLM configuration and system prompt
    utils/
        scraper.py             # Web scraping utilities for product catalog
        storage.py             # Google Cloud Storage upload utilities
    data/
        giftcards_com_products.json  # Product inventory (400+ gift cards)
    blackhawk.py               # Main workflow (GiftCardGuru class)
    requirements.txt           # Python dependencies
    pyproject.toml            # Project metadata
    load_secrets.py           # Secret management from GCP Secret Manager
    docker-compose.yaml       # Docker configuration
    Dockerfile                # Container build configuration
    README.md                 # Project documentation
```
