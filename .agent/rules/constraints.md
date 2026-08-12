# Constraints

- Lock by `projectId`: Ensure each project only executes one pipeline task at a time to prevent race conditions.
- Do not trust output counts from Gemini: The backend must validate, truncate, or reject the response if Gemini's output exceeds the allowed limits (max 2 characters, 1 chapter).
- Avoid Over-engineering: Prioritize simple, flat designs, saving data directly as JSON files on disk instead of setting up a complex database.
