--- role: system
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

{% if field_to_regenerate == 'description' %}
Return your response as a valid JSON object with the following structure:
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


CRITICAL FORMATTING REQUIREMENTS:
- Respond with ONLY the JSON object using the exact field names above
- Do not wrap in additional objects or use different field names
- Do not nest further data structures
- ONLY STRINGS!
- Do not include markdown code blocks or extra formatting
  - Ensure all fields are filled with meaningful, character-appropriate content
  - Make the character feel like a real person with depth, contradictions, and authentic human complexity
- Include mature and erotic detail where appropriate.
{% else %}
Now, based on all the context above, provide the new rewritten content for the "{{ field_to_regenerate }}" field. Output only the raw text for the new field, with no additional commentary.
{% endif %}
