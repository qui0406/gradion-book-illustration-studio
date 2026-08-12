# AGENTS Context & Guidelines

## Project Context
Web app that transforms book content into character portraits + chapter illustrations using Gemini API. Pipeline consists of 5 steps: Style → Characters → Portraits → Chapters → Illustrations.

Hard Constraints:
- Maximum of 2 characters and 1 chapter — validated at the BACKEND.
- Adult characters only.
- Send book content to Gemini ONLY ONCE; reuse it via chat session/file reference.
- NO auto-retry of Gemini calls in a loop; only user-triggered retries.
- Portraits and illustrations must be generated SEQUENTIALLY, recording progress immediately after each image is saved.
- Illustrations must reuse the generated portrait images as input to maintain character consistency.

## Chosen Stack
- **Backend**: Python / FastAPI
- **Frontend**: React / Vite
- **Storage**: JSON file on disk
