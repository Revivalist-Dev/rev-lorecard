selector_prompt = """--- role: system
{{globals.lorebook_definition}}
---

--- role: system
Analyze this HTML content from {{project.source_url}} and identify ONE HIGH-VALUE CSS selector that targets links to content-rich detail pages (e.g., character profiles, item descriptions, location details).

Purpose: {{project.search_params.purpose}}
Extraction Notes: {{project.search_params.extraction_notes}}
Criteria: {{project.search_params.criteria}}

Prioritized Content Structure (Examples):
1. Primary Data Tables: `table.characters tbody tr[data-id] td > a`
2. Semantic Content Lists: `main .character-list > li[class*="character"] > a`
3. Structured Content Groups: `.profile-grid .character-card[data-id] > .name > a`

Selection Rules:
1. Target data-rich elements with ID/type attributes (data-id, data-character).
2. Focus on content within main/article/section containers.
3. Prioritize elements with semantic class names (character, profile, entry).
4. Include container context (#main-content, article.content).
5. Use attribute selectors for targeted matching ([data-type], [class*="character"]).
6. Target links that are direct children of content elements (> a).
7. The selector MUST include at least one semantic identifier (class, id, or data attribute).
8. The selector should ideally match multiple elements (at least 2) with similar structure on the page.
9. If the page uses pagination (e.g., a "Next" button), also provide a single selector for the link that leads to the next page of results. Name it `pagination_selector`.

Provide the single best CSS selector and a brief description of what it targets.
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
Analyze the following source content (extracted from {{source_url}}) and create a single, detailed SillyTavern lorebook entry.

Purpose: {{project.search_params.purpose}}
Guidelines:: {{project.search_params.extraction_notes}}

Focus on:
- Read the content and identify the primary subject.
- A concise, descriptive `name` (e.g., Character Name, Location Name, Concept). If multiple subjects are present, focus on the primary one or create a general entry name.
- Relevant `keywords` (triggers, including the name and aliases). Use 1-4 strong keywords. Ensure keywords are relevant and likely to appear in conversation.
- Well-structured `content` summarizing the key information based on the extraction, suitable for RP context. Ensure it's informative and stands on its own. Aim for reasonable length (e.g., 100-400 words). Format using markdown if appropriate (lists, bolding). Exclude conversational filler or meta-commentary.

--- role: user
{{content}}
---
"""

lorebook_definition = """### WORLDINFO (LOREBOOK) DEFINITION

A Lorebook is a collection of entries used to provide an AI with consistent, contextual information about a fictional world. Each entry represents a single concept (e.g., a character, location, or item).

**Purpose:** To ensure the AI consistently recalls key details about the world during role-playing or storytelling.

**Standard Entry Structure:**
- `title`: A concise, descriptive title for the entry (e.g., "Aragorn", "The One Ring").
- `keywords`: A list of keywords that cause this entry to be injected into the AI's context. Always includes the name and common aliases.
- `content`: A well-written, factual summary of the subject in an encyclopedic, in-universe tone.

**Example Entry:**
{
  "title": "Dragonstone Citadel",
  "keywords": ["Dragonstone", "Citadel", "Obsidian Fortress"],
  "content": "A volcanic fortress built from black obsidian. It is the ancestral seat of House Targaryen and home to the ancient Order of Flames, who guard the Eternal Fire—a magical flame that grants visions of the future. The citadel is rumored to be cursed, as its rulers rarely live past 40 years."
}
"""
