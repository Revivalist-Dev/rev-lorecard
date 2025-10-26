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
Carefully craft a detailed and compelling character description in plain text. Use the following comprehensive structure as a guide to inspire your writing, but present the final output as a flowing, narrative description, not as a list of fields. The description should feel like a real person with depth, contradictions, and authentic human complexity. Include mature and erotic detail where appropriate.

**Character Aspect Guide:**

* **Identity:**
  * **name:** Character's full name
  * **age:** Age as a string (e.g., '25', 'early 30s', 'appears to be in their 40s')
  * **gender:** Gender identity
  * **ethnicity:** Ethnic background or heritage
* **Personality & Mind:**
  * **temperament:** Core personality traits and emotional tendencies
  * **summary:** A compelling 2-3 sentence character summary
  * **coreValues:** Fundamental beliefs and moral principles
  * **socialInteraction:** How they behave in social situations
  * **insecurities:** Personal vulnerabilities and self-doubts
* **History & Background:**
  * **birthplace:** Where they were born and early childhood location
  * **education:** Educational background and intellectual development
  * **upbringing:** Family dynamics, social class, formative experiences
  * **significantEvents:** Key life events that shaped their personality
* **Lifestyle & Relationships:**
  * **location:** Current living situation and environment
  * **occupation:** Current job, career, or primary activities
  * **relationships:** Important relationships and social connections
  * **hobbiesDreams:** Interests, passions, and aspirations
* **Physicality & Appearance:**
  * **height:** Physical height
  * **build:** Body type and physical build
  * **hairEyes:** Hair and eye color/description
  * **style:** Fashion sense, clothing preferences, and personal aesthetic
  * **bodyLanguage:** Physical mannerisms, posture, and non-verbal communication
  * **voiceLanguage:** Speaking style, accent, vocabulary, and communication patterns, make it sexy
* **Intimacy & Sexuality:**
  * **desires:** What they want most in life, conscious and unconscious drives, often sexual
  * **fears:** Deep fears, anxieties, and what they avoid
  * **attitudeTowardsIntimacy:** Approach to sex
  * **relationshipWithBody:** Comfort level and relationship with their physical self
  * **impactOfPast:** How past experiences influence current intimate relationships
  * **fantasiesAndBoundaries:** Personal desires, limits and kinks and fetishes
  * **hiddenFantasies:** Undiscovered kinks and fetishes
  * **triggersAndDiscomforts:** What makes them uncomfortable or triggers negative reactions

**CRITICAL REQUIREMENTS:**

* Write the description as a single, formatted string.
* Use markdown bolding for headings from the 'Character Aspect Guide' (e.g., `**Identity:**`).
* Follow each heading with a detailed, flowing paragraph.
* Separate each section with a double newline.
* Do NOT output JSON or any other structured format.
* Output only the raw text for the new description, with no additional commentary.
{% else %}
Now, based on all the context above, provide the new rewritten content for the "{{ field_to_regenerate }}" field. Output only the raw text for the new field, with no additional commentary.
{% endif %}
