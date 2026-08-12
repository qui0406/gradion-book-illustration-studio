import os
import json
import logging
import tempfile
from typing import Optional, Tuple, Any, List
from google import genai
from pydantic import BaseModel

from app.models.project import Character, Chapter 

class CharacterPrompt(BaseModel):
    name: str
    prompt: str
logger = logging.getLogger(__name__)

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data"))
IMAGES_DIR = os.path.join(DATA_DIR, "images")
os.makedirs(IMAGES_DIR, exist_ok=True)

PRESET_ART_STYLES = [
    "Watercolor Illustration",
    "Anime / Manga Style",
    "Fairy Tale Storybook",
    "Classic Oil Painting",
    "Digital Fantasy Art",
    "Cyberpunk / Sci-Fi Concept Art"
]


# === ĐỊNH NGHĨA CLASS GEMINI SERVICE ===
class GeminiService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        self.client = genai.Client(api_key=self.api_key)
        self.text_model = "gemini-3.5-flash"
        self.image_model = "gemini-2.5-flash-image"
    
    # === STEP 1: EXTRACT ART STYLE ===
    def extract_art_style(
        self, 
        book_text: str, 
        custom_style: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> Tuple[str, str, str]:
        """
        Step 1: Determine Art Style and create Gemini Session Ref.
        Returns: (style_name, style_source, interaction_id)
        """
        # Sending the book must succeed — everything downstream depends on this
        # interaction_id. Let this raise; caller sets step_state=FAILED so the
        # user can retry, instead of silently continuing without real context.
        book_interaction = self._create_book_interaction(book_text)

        if custom_style and custom_style.strip():
            style = custom_style.strip()
            style_interaction = self.client.interactions.create(
                model=self.text_model,
                input=f'The art style will be: "{style}". Keep that in mind.',
                previous_interaction_id=book_interaction.id,
            )
            return style, "user_provided", style_interaction.id

        style_interaction = self.client.interactions.create(
            model=self.text_model,
            input="Define an art style that fits this story. Return ONLY the style name, nothing else.",
            previous_interaction_id=book_interaction.id,
        )
        style = style_interaction.output_text.strip().strip('"\'.,!? \n')
        if not style:
            raise ValueError("Gemini returned an empty style")
        if len(style) > 50:
            style = self._extract_style_from_response(style)
        return style, "ai_generated", style_interaction.id
    
    # === HELPER: CREATE BOOK INTERACTION ===
    def _create_book_interaction(self, book_text: str) -> Any:
        """Upload book to File API và tạo interaction đầu tiên."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.txt', delete=False, encoding='utf-8'
        ) as f:
            f.write(book_text)
            temp_path = f.name
        
        try:
            book_file = self.client.files.upload(file=temp_path)
            
            book_interaction = self.client.interactions.create(
                model=self.text_model,
                input=[
                    {"type": "text", "text": "Here's a book to illustrate. Don't say anything for now, instructions will follow."},
                    {"type": "document", "uri": book_file.uri},
                ],
            )
            return book_interaction
        finally:
            try:
                os.unlink(temp_path)
            except:
                pass
    
    # === HELPER: EXTRACT STYLE FROM RESPONSE ===
    def _extract_style_from_response(self, response: str) -> str:
        """Trích xuất style từ response dài."""
        lines = response.split('\n')
        first_line = lines[0].strip()
        
        if ':' in first_line:
            return first_line.split(':', 1)[1].strip()
        
        words = first_line.split()
        if len(words) > 5:
            return ' '.join(words[:5])
        
        return first_line

    # === STEP 2: EXTRACT CHARACTERS ===
    def extract_characters(
        self,
        session_ref: str,
        style: str,
        max_characters: int = 2
    ) -> List[Character]:
        """
        Step 2: Extract main adult characters (max 2).
        Uses structured output with Pydantic.
        """
        prompt = """
        Extract the main adult characters from this book.
        
        Requirements:
        - Return EXACTLY 2 characters maximum
        - Only include ADULT characters (age 18+)
        - For each character provide:
          - name: Character's full name
          - prompt: Detailed description for AI image generation (at least 50 words)
            Include: physical appearance, clothing, personality, and the artistic style
        
        Return as JSON array with fields: name, prompt
        """
        
        response = self.client.interactions.create(
            model=self.text_model,
            input=prompt,
            previous_interaction_id=session_ref,
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": {"type": "array", "items": CharacterPrompt.model_json_schema()},
            },
        )
        
        # Parse response
        try:
            data = json.loads(response.output_text)
        except json.JSONDecodeError:
            import re
            match = re.search(r'\[.*\]', response.output_text, re.DOTALL)
            if match:
                data = json.loads(match.group())
            else:
                raise ValueError("Failed to parse Gemini response")
        
        # Convert to Character objects
        characters = []
        for idx, item in enumerate(data[:max_characters]):
            image_prompt = f"{item.get('prompt', '')} Style: {style}"
            
            char = Character(
                id=f"char_{idx + 1}",
                name=item.get("name", "Unknown"),
                description=item.get("prompt", ""),
                image_prompt=image_prompt
            )
            characters.append(char)
        
        return characters
