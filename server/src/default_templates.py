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

---role: system
Given the input:
```
{{project.prompt}}
```
---

Generate search parameters for creating a lorebook. The parameters should help gather comprehensive and relevant information based on the type of content requested (characters, locations, events, etc.).

Requirements:
1. Purpose - Clear statement based on request type:
- For characters: "To gather detailed character information including backgrounds, traits, and relationships"
- For locations: "To gather detailed information about places, their features, and significance"
- For other topics: "To gather comprehensive information about the requested subject matter"
2. Extraction Notes - Guidelines: "Focus extraction on the specific type of content requested. For characters: extract names, aliases, descriptions, personality, history, and relationships. For locations: extract features, history, significance. For other topics: extract key aspects relevant to the subject."
3. Criteria - Simple validation requirements:
- For characters: "Page must be specifically created as a character article (e.g., character profile, biography page). Reject pages that only mention or reference the character within other content."
- For locations: "Page must be specifically created as a location article (e.g., place description, area guide). Reject pages that only mention or reference the location in passing."
- For other topics: "Page must be specifically created to document the requested subject. Reject pages that only contain references to the subject within broader content."
"""

entry_creation_prompt = """--- role: system
{{globals.lorebook_definition}}
---

--- role: system
Analyze the following source content (extracted from {{source_url}}) and create a single, detailed SillyTavern lorebook entry.

Focus on:
- A concise, descriptive `name` (e.g., Character Name, Location Name, Concept). If multiple subjects are present, focus on the primary one or create a general entry name.
- Relevant `triggers` (keywords, including the name and aliases). Use 2-5 strong keywords. Ensure triggers are relevant and likely to appear in conversation.
- Well-structured `content` summarizing the key information based on the extraction, suitable for RP context. Ensure it's informative and stands on its own. Aim for reasonable length (e.g., 100-400 words). Format using markdown if appropriate (lists, bolding). Exclude conversational filler or meta-commentary.

--- role: user
{{content}}
---
"""

lorebook_definition = """### WORLDINFO (LOREBOOKS)

**World Info** (often called **Lorebooks**) is a feature used in AI-driven storytelling and role-playing platforms (like SillyTavern, NovelAI, KoboldAI, or Text-generation-webui) to help AI models maintain consistency in fictional worlds. It acts as a dynamic knowledge base that the AI references during interactions to avoid contradictions and keep track of key details.

---

### **What is World Info/Lorebooks?**
- **A structured database**: Stores details about characters, locations, rules, events, or concepts in your fictional world.
- **Contextual triggers**: Entries activate automatically when specific keywords or phrases appear in the conversation/story.
- **Prevents "amnesia"**: Ensures the AI remembers critical lore without relying solely on its limited context window.

---

### **How It Works**
1. **Create Entries**: Define elements (e.g., a character’s backstory, a magic system’s rules).
2. **Set Triggers**: Link entries to keywords (e.g., mention "Dragonstone" → inject lore about that location).
3. **Dynamic Injection**: When a trigger word appears in the chat/story, the relevant entry is temporarily added to the AI’s context.

---

### **Key Features**
- **Hierarchy**: Organize entries into categories (e.g., factions, items, timelines).
- **Priority**: Set which entries take precedence if multiple triggers occur.
- **Cross-references**: Link entries to each other (e.g., a character entry references their home city).
- **Formatting**: Use markdown or plain text.

---

### **Example Lorebook Entry**
```plaintext
Name: Dragonstone Citadel
Triggers: Dragonstone, Citadel, Obsidian Fortress
Content:
  A volcanic fortress built from black obsidian. Home to the ancient Order of Flames,
  who guard the Eternal Fire—a magical flame that grants visions of the future.
  The citadel is rumored to be cursed, as its rulers never live past 40 years.
```

---

### **Use Cases**
1. **Complex Worldbuilding**: Track political factions, religions, or history.
2. **Character Consistency**: Ensure the AI remembers a character’s motives, secrets, or relationships.
3. **Magic/Science Systems**: Define rules (e.g., "Magic drains lifeforce" or "Robots cannot harm humans").
4. **Plot Hooks**: Store hidden clues or foreshadowing for the AI to weave into the narrative.

---

### **Best Practices**
- **Keep entries concise**: AI models process information best in short, clear snippets.
- **Balance detail**: Too many entries can overwhelm the context window.
- **Test triggers**: Ensure keywords are unique enough to avoid false activations.
- **Update dynamically**: Add/remove entries as the story evolves.

Lorebooks are essential for long-term storytelling with AI.
"""
