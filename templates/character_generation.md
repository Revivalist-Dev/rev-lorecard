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

**Description Field Formatting:**
The `description` field MUST be a valid JSON object with the following structure. Do not include any other text or markdown formatting around the JSON.

{
  "name": "Character's full name",
  "age": "Age as a string (e.g., '25', 'early 30s', 'appears to be in their 40s')",
  "gender": "Gender identity",
  "ethnicity": "Ethnic background or heritage",
  "temperament": "Core personality traits and emotional tendencies",
  "summary": "A compelling 2-3 sentence character summary",
  "birthplace": "Where they were born and early childhood location",
  "education": "Educational background and intellectual development",
  "upbringing": "Family dynamics, social class, formative experiences",
  "significantEvents": "Key life events that shaped their personality",
  "location": "Current living situation and environment",
  "occupation": "Current job, career, or primary activities",
  "relationships": "Important relationships and social connections",
  "hobbiesDreams": "Interests, passions, and aspirations",
  "coreValues": "Fundamental beliefs and moral principles",
  "desires": "What they want most in life, conscious and unconscious drives, often sexual",
  "fears": "Deep fears, anxieties, and what they avoid",
  "socialInteraction": "How they behave in social situations",
  "bodyLanguage": "Physical mannerisms, posture, and non-verbal communication",
  "insecurities": "Personal vulnerabilities and self-doubts",
  "height": "Physical height",
  "build": "Body type and physical build",
  "hairEyes": "Hair and eye color/description",
  "style": "Fashion sense, clothing preferences, and personal aesthetic",
  "voiceLanguage": "Speaking style, accent, vocabulary, and communication patterns, make it sexy",
  "attitudeTowardsIntimacy": "Approach to sex",
  "relationshipWithBody": "Comfort level and relationship with their physical self",
  "impactOfPast": "How past experiences influence current intimate relationships",
  "fantasiesAndBoundaries": "Personal desires, limits and kinks and fetishes",
  "hiddenFantasies": "Undiscovered kinks and fetishes",
  "triggersAndDiscomforts": "What makes them uncomfortable or triggers negative reactions"
}

CRITICAL FORMATTING REQUIREMENTS for the description field:

- Respond with ONLY the JSON object for the description field.
- Do not wrap in additional objects or use different field names.
- Do not nest further data structures.
- All values in the JSON object MUST be strings.
- Do not include markdown code blocks or extra formatting.
- Ensure all fields are filled with meaningful, character-appropriate content.
- Make the character feel like a real person with depth, contradictions, and authentic human complexity.

- Include mature and erotic detail where appropriate.
---

--- role: user
**SOURCE MATERIAL:**

{{ content }}
---
