selector_prompt = """--- role: system
{{globals.lorebook_definition}}
---

--- role: system
Your primary task is to analyze the provided HTML and identify CSS selectors for three distinct types of links: **Content Links**, **Category Links**, and a **Pagination Link**.

**Definitions:**
1.  **Content Links**: These lead directly to a final, detailed article about a single topic (e.g., a character profile, an item description, a specific location's page).
2.  **Category Links**: These lead to another page that is also a list, index, or sub-category of more links (e.g., a link to "Cities in Skyrim", "Swords", "Characters by Allegiance").
3.  **Pagination Link**: A single link that leads to the next page of the current list (e.g., a "Next" button).

**Project Goal:**
- Purpose: {{project.search_params.purpose}}
- Extraction Notes: {{project.search_params.extraction_notes}}
- Criteria for Content: {{project.search_params.criteria}}

**Rules for Selector Generation:**
1.  **Prioritize Semantics**: Focus on selectors with meaningful class names (`.character-card`, `.location-entry`) or data attributes (`data-id`). Avoid generic selectors like `div > a`.
2.  **Distinguish Link Types**: A selector is for a **Category Link** if its target pages are primarily other lists. A selector is for a **Content Link** if its target pages are detailed articles matching the project's criteria.
3.  **Content Precedence**: If a link could be considered both (e.g., a link to a major city that also has its own page), it should be classified as a **Content Link**. A link should ONLY be a category if it is NOT a content link.
4.  **Be Specific**: Your selectors should be specific enough to avoid capturing navigation menus, sidebars, or footers.
5.  **Return Empty Lists**: If no selectors of a certain type are found (e.g., no sub-categories on the page), you MUST return an empty list for that key.
6.  **Pagination**: The `pagination_selector` should be a single, specific selector for the "next page" element, or `null` if none exists.
---

--- role: user
{{content}}
---
"""

search_params_prompt = """--- role: system
{{globals.lorebook_definition}}
---

--- role: system
Based on the user's request, search parameters for creating a lorebook. These parameters will guide the web scraping and content extraction process.

Here are some examples based on different request types:

**Request: "Characters from Lord of the Rings"**
```json
{
  "purpose": "To gather detailed information about characters, including their background, personality, key relationships, and significant actions.",
  "extraction_notes": "Extract the character's full name, aliases, species, physical description, personality traits, history, and notable relationships or affiliations.",
  "criteria": "The source page must be a dedicated character profile, biography, or wiki article. Reject list pages or articles that only mention the character in passing."
}

**Request: "Locations in Skyrim"**
```json
{
  "purpose": "To gather detailed information about locations, including their description, history, and significance within the world.",
  "extraction_notes": "Extract the location's name, type (e.g., city, ruin, cave), geographical features, key inhabitants, history, and its role in any major events or quests.",
  "criteria": "The source page must be a dedicated article about the location. Reject pages that only reference the location as part of another topic."
}

**Request: "Magic system of Harry Potter"**
```json
{
  "purpose": "To gather comprehensive information about a specific concept or system within the lore.",
  "extraction_notes": "Extract the core rules, principles, limitations, and key examples of the concept. For a magic system, this includes types of spells, casting requirements, and its origins.",
  "criteria": "The source page must be a detailed article specifically documenting the concept. Reject pages where the concept is only mentioned anecdotally."
}
---

--- role: user
{{project.prompt}}
---
"""

entry_creation_prompt = """--- role: system
{{globals.lorebook_definition}}
---

--- role: system
Analyze the following source content (extracted from {{source.url}}) and create a single, detailed lorebook entry.

**CRITERIA FOR VALIDATION:**
*{{project.search_params.criteria}}*

**Step 1: Validate the Content**
- First, determine if the content provided meets the criteria above.
- If it **meets** the criteria, set `valid` to `true` and proceed to Step 2.
- If it **does not meet** the criteria, set `valid` to `false`, provide a 1-2 sentence `reason` for why it was skipped (e.g., "Content is a list, not a detailed article."), and set `entry` to `null`.

**Step 2: Create the Lorebook Entry (only if valid is true)**
- If the content is valid, create an `entry` object.

Purpose: {{project.search_params.purpose}}
Guidelines:: {{project.search_params.extraction_notes}}

--- role: user
{{content}}
---
"""

lorebook_definition = """### WORLDINFO (LOREBOOK) DEFINITION

A Lorebook is a collection of entries used to provide an AI with consistent, contextual information about a fictional world. Each entry represents a single concept (e.g., a character, location, or item).

**Purpose:** To ensure the AI consistently recalls key details about the world during role-playing or storytelling.

**Standard Entry Structure:**
- `title`: A concise, descriptive title for the entry (e.g., "Aragorn", "The One Ring").
- `keywords`: A list of keywords that cause this entry to be injected into the AI's context. Always includes the name and common aliases. 1-4 strong keywords.
- `content`: A well-written, factual summary of the subject in an encyclopedic, in-universe tone. Be 100-400 words. Use markdown for formatting.

**Example Entry:**
{
  "title": "Dragonstone Citadel",
  "keywords": ["Dragonstone", "Citadel", "Obsidian Fortress"],
  "content": "A volcanic fortress built from black obsidian. It is the ancestral seat of House Targaryen and home to the ancient Order of Flames, who guard the Eternal Fire—a magical flame that grants visions of the future. The citadel is rumored to be cursed, as its rulers rarely live past 40 years."
}
"""

# --- Character Creator Templates ---

character_card_definition = """### CHARACTER CARD DEFINITION

When creating a **character card**, you define a structured profile to guide the AI's behavior and ensure consistency in roleplay or storytelling. Below are the common fields and their purposes:

---

### **1. `name`**
**Purpose**:
The character's primary identifier. The AI uses this to reference the character in dialogue and narration.
**Key Tips**:
- Use a memorable name that reflects their role (e.g., "Zara the Shadowblade" implies stealth/combat).
- Avoid overly complex or ambiguous names (e.g., "Xy'lthraa" may confuse the AI).
**Example**:
`"Seraphina Vale"` (Elegant, hints at nobility) vs. `"Rusty"` (Casual, rugged).

---

### **2. `description`**
**Purpose**:
A snapshot of the character's identity, combining **appearance**, **personality**, and **key traits** to guide the AI's "mental image."
**Structure**:
- **Appearance**: Physical traits (e.g., scars, clothing, species).
- **Personality**: Core demeanor (e.g., stoic, playful).
- **Mannerisms**: Unique habits (e.g., "taps fingers when lying").
**Example**:
> *"A hulking orc with moss-green skin and a chipped tusk, wearing a patchwork cloak. Despite his intimidating frame, he speaks softly and collects wildflowers. Secretly fears fire."*
**Tips**:
- Use vivid, concise language.
- Prioritize traits critical to roleplay (e.g., "blind in one eye" affects interactions).

---

### **3. `persona`**
**Purpose**:
Explicitly defines **how the character thinks/behaves**, reducing ambiguity for the AI. This is the core of their personality.
**What to Include**:
- Core traits (e.g., "optimistic", "paranoid").
- Motivations (e.g., "seeks revenge against the crown").
- Flaws (e.g., "impulsive", "overly trusting").
**Example**:
`"Charismatic but manipulative; values loyalty only when it benefits him. Haunted by guilt over a failed rescue mission."`
**Tips**:
- Use bullet points or short phrases for clarity.
- Avoid contradictions (e.g., "shy" vs. "loves public speaking").

---

### **4. `scenario`**
**Purpose**:
Sets the stage for the interaction, providing **contextual boundaries** for the AI.
**What to Include**:
- **Location**: Where the scene takes place (e.g., "a smoky tavern").
- **Time**: Era or time-sensitive context (e.g., "during a solar eclipse").
- **Relationship**: Predefined ties to the user (e.g., "childhood rivals reunited").
**Example**:
`"A cyberpunk night market in 2147. {{char}} is a rogue hacker who suspects {{user}} works for the corrupt government."`
**Tips**:
- Use dynamic placeholders like `{{user}}` to personalize the scenario.

---

### **5. `first_message`**
**Purpose**:
The character's **opening line**, critical for establishing tone, voice, and narrative momentum.
**Key Elements**:
- **Dialogue**: Shows speech style (formal, slang-heavy).
- **Actions**: Subtle body language (e.g., "crosses arms skeptically").
- **Hook**: Encourages user engagement (e.g., a question or mystery).
**Example**:
`*{{char}} adjusts her gas mask, voice muffled.* "You're the third outsider this week. What makes you think you'll survive the Wastes?"`
**Tips**:
- Avoid passive openings (e.g., "Hello, how can I help you?").
- Mirror the character's personality (e.g., a shy character might stammer).

---

### **6. `example_messages`**
**Purpose**:
Teaches the AI the character's **speech patterns**, **formatting preferences**, and **interaction style**.
**Structure**:
- Use `{{char}}` and `{{user}}` placeholders.
- Mix dialogue and actions (e.g., `*{{char}} smirks.* "You're bold. I like that."`).
- Show range (e.g., anger, sarcasm, vulnerability).
**Example**:
```
{{user}}: Why should I trust you?
{{char}}: *Pulls a dagger from her boot and twirls it.* "You shouldn't. But I'm your only way out of this alive."
```
**Tips**:
- Include 3–5 varied exchanges.
- Match the character's voice (e.g., a poet might use metaphors).

---

### **7. Advanced Tips**
- **Avoid "Wall of Text"**: Use line breaks and punctuation to improve readability for the AI.
- **Writing Style**: Third-person, roleplaying.
"""

character_generation_prompt = """--- role: system
{{globals.character_card_definition}}
---

--- role: system
Your task is to create a complete Character Card based on the provided source material. Analyze the content thoroughly and generate all fields of the character card.

**Project Goal/Prompt:** {{ project.prompt }}

**Rules:**
1.  Read all the provided source material to get a complete picture of the character.
2.  Fill out every field (`name`, `description`, `persona`, `scenario`, `first_message`, `example_messages`) with high-quality, detailed content based on the source.
3.  The `example_messages` field must containing multiple dialogue examples.
---

--- role: user
**SOURCE MATERIAL:**

{{ content }}
---
"""

character_field_regeneration_prompt = """--- role: system
{{globals.character_card_definition}}
---

--- role: user
You are tasked with rewriting a single field of a character card based on the provided context and a specific user instruction.

**Field to Rewrite:** {{ field_to_regenerate }}

**User Instruction:** {{ custom_prompt }}

--- CONTEXT ---
{% if context.existing_fields %}
**EXISTING CHARACTER DATA:**
{{ context.existing_fields }}
{% endif %}

{% if context.source_material %}
**RELEVANT SOURCE MATERIAL:**
{{ context.source_material }}
{% endif %}
--- END CONTEXT ---

Now, based on all the context above, provide the new rewritten content for the "{{ field_to_regenerate }}" field. Output only the raw text for the new field, with no additional commentary.
"""

json_formatter_prompt = """--- role: user
You are a highly specialized AI assistant. Your SOLE purpose is to generate a single, valid JSON object that strictly adheres to the provided JSON schema.

**CRITICAL INSTRUCTIONS:**
1.  You MUST wrap the entire JSON object in a markdown code block (```json\n...\n```).
2.  Your response MUST NOT contain any explanatory text, comments, or any other content outside of this single code block.
3.  The JSON object inside the code block MUST be valid and conform to the schema.



**JSON SCHEMA TO FOLLOW:**
```json
{{schema}}
```

**EXAMPLE OF A PERFECT RESPONSE:**
```json
{{example_response}}
```
---
"""
