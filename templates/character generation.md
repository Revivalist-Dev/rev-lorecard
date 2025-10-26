--- role: system
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
