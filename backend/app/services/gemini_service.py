import os
import json
import logging
import tempfile
import base64
from datetime import datetime, timezone
from typing import Optional, Tuple, Any, List
from google import genai
from pydantic import BaseModel

from app.models.project import Character, Chapter 

class CharacterPrompt(BaseModel):
    name: str
    prompt: str

class ChapterPrompt(BaseModel):
    name: str           # Chapter title
    prompt: str         # Illustration prompt (at least 50 words)
    characters: List[str]  # Characters appearing in this chapter

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

    def generate_portraits(self, project_id: str, characters: List[Character],
                           style: str, session_ref: str) -> List[dict]:
        """
        Step 3: Generate character portraits sequentially.
        """
        system_instructions = """
            There must be no text on the image, it should not look like a cover page.
            It should be a full illustration with no borders, titles, nor description.
            Stay family-friendly with uplifting colors.
            Each produced should be a simple image, no panels.
        """
        
        portraits = []
        
        # === Tạo image context ===
        logger.info(f"Starting portrait generation for {len(characters)} characters")
        image_context = self.client.interactions.create(
            model=self.image_model,
            input=f"""
                You are going to generate portrait images to illustrate this book.
                The style we want you to follow is: {style}
                Also follow those rules: {system_instructions}
            """,
            previous_interaction_id=session_ref,
        )
        last_interaction_id = image_context.id
        
        # === Loop từng character ===
        for idx, character in enumerate(characters):
            logger.info(f"Generating portrait {idx+1}/{len(characters)}: {character.name}")
            
            # Gọi Gemini Imagen
            portrait_interaction = self.client.interactions.create(
                model=self.image_model,
                input=f"Create a portrait illustration for {character.name} following this description: {character.image_prompt}",
                previous_interaction_id=last_interaction_id,
            )
            
            # === Extract image từ response ===
            generated_image = None
            for step in reversed(portrait_interaction.steps):
                if step.type == "model_output" and step.content:
                    for content in reversed(step.content):
                        if content.type == "image":
                            generated_image = content
                            break
                    if generated_image:
                        break
            
            if generated_image:
                image_path = self._save_image(
                    project_id=project_id,
                    step="portraits",
                    entity_id=character.id,
                    image_data=generated_image.data
                )
                
                portraits.append({
                    "character_id": character.id,
                    "character_name": character.name,
                    "image_path": image_path,
                    "generated_at": datetime.now(timezone.utc).isoformat()
                })
                logger.info(f"✅ Portrait saved: {image_path}")
            else:
                logger.error(f"No image generated for {character.name}")
                raise RuntimeError(f"Gemini Imagen failed to generate a portrait image for character: {character.name}")
            
            last_interaction_id = portrait_interaction.id
        
        logger.info(f"Portrait generation completed: {len(portraits)}/{len(characters)} portraits generated")
        return portraits
    
    # === STEP 4: EXTRACT CHAPTERS ===
    def extract_chapters(
        self,
        session_ref: str,
        characters: List[Character],
        style: str,
        max_chapters: int = 1
    ) -> List[Chapter]:
        """
        Step 4: Extract the most visually interesting chapter (max 1).
        Uses the existing Gemini session (session_ref) — no re-upload of book.
        """
        character_names = ", ".join([c.name for c in characters])

        prompt = f"""
        Extract the most visually interesting chapter from this book.

        Requirements:
        - Return EXACTLY 1 chapter maximum
        - The chapter should feature these characters: {character_names}
        - For each chapter provide:
          - name: Chapter title
          - prompt: Detailed description for AI image generation (at least 50 words)
            Include: setting, actions, mood, lighting, and the artistic style
          - characters: List of character names appearing in this chapter

        Return as JSON array with fields: name, prompt, characters
        """

        response = self.client.interactions.create(
            model=self.text_model,
            input=prompt,
            previous_interaction_id=session_ref,
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": {"type": "array", "items": ChapterPrompt.model_json_schema()},
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
                raise ValueError("Failed to parse Gemini chapter extraction response")

        # Normalize to list of dicts
        if isinstance(data, dict):
            data = [data]
        if not isinstance(data, list):
            raise ValueError(f"Unexpected response shape: {type(data)}")

        # Server-side enforcement: max 1 chapter
        if len(data) > max_chapters:
            data = data[:max_chapters]
            logger.warning(f"Gemini returned {len(data)} chapters, truncated to {max_chapters}")

        chapters = []
        for idx, item in enumerate(data):
            chapter = Chapter(
                id=f"ch_{idx + 1}",
                title=item.get("name", f"Chapter {idx + 1}"),
                summary=item.get("prompt", ""),
                illustration_prompt=f"{item.get('prompt', '')} Style: {style}",
                characters=item.get("characters", [])
            )
            chapters.append(chapter)

        logger.info(f"Extracted {len(chapters)} chapter(s) via Gemini")
        return chapters

    # === STEP 5: GENERATE ILLUSTRATIONS ===
    def generate_illustrations(
        self,
        project_id: str,
        chapters: List[Chapter],
        portraits: List[dict],
        style: str,
        session_ref: str
    ) -> List[dict]:
        """
        Step 5: Generate a full scene illustration for each chapter.
        Uses existing Gemini session (session_ref) — no re-upload of book.
        Characters are referenced by name from portraits for prompt consistency.
        """
        system_instructions = """
            There must be no text on the image, it should not look like a cover page.
            It should be a full illustration with no borders, titles, nor description.
            Stay family-friendly with uplifting colors.
            Each produced should be a simple image, no panels.
        """
        illustrations = []

        for chapter in chapters:
            logger.info(f"Generating illustration for chapter: {chapter.title}")

            # Prepare input items for Gemini
            input_items = []

            # 1. Upload and attach portrait images
            for p in portraits:
                rel_path = p["image_path"].replace("/api/images/", "", 1)
                local_path = os.path.join(IMAGES_DIR, rel_path)
                try:
                    p_file = self.client.files.upload(file=local_path)
                    input_items.append({"type": "text", "text": f"Character reference for {p['character_name']}:"})
                    input_items.append({"type": "image", "uri": p_file.uri})
                except Exception as e:
                    logger.warning(f"Could not upload portrait for {p.get('character_name')}: {e}")

            # 2. Build character reference list from portraits for the text prompt
            char_refs = "\n".join(
                f"- {p['character_name']}" for p in portraits
            ) if portraits else "characters as described in the story"

            prompt = f"""
                Create a full scene illustration for this chapter.
                Chapter: {chapter.title}
                Scene description: {chapter.illustration_prompt}
                Characters in this scene:
                {char_refs}
                Style: {style}
                Rules: {system_instructions}
            """
            input_items.append({"type": "text", "text": prompt.strip()})

            illustration_interaction = self.client.interactions.create(
                model=self.image_model,
                input=input_items,
                previous_interaction_id=session_ref,
            )

            # Extract image from Gemini interaction steps
            generated_image = None
            for step_item in reversed(illustration_interaction.steps):
                if step_item.type == "model_output" and step_item.content:
                    for content_item in reversed(step_item.content):
                        if content_item.type == "image":
                            generated_image = content_item
                            break
                    if generated_image:
                        break

            if not generated_image:
                raise RuntimeError(
                    f"Gemini Imagen returned no image for chapter: {chapter.title}"
                )

            image_path = self._save_image(
                project_id=project_id,
                step="illustrations",
                entity_id=chapter.id,
                image_data=generated_image.data
            )

            illustrations.append({
                "chapter_id": chapter.id,
                "chapter_title": chapter.title,
                "image_path": image_path,
                "generated_at": datetime.now(timezone.utc).isoformat()
            })
            logger.info(f"Illustration saved: {image_path}")

        logger.info(f"Illustration generation completed: {len(illustrations)}/{len(chapters)}")
        return illustrations

    def _save_image(self, project_id: str, step: str, entity_id: str, image_data: str) -> str:
        # Decode base64 image
        if isinstance(image_data, str):
            image_bytes = base64.b64decode(image_data)
        else:
            image_bytes = image_data
        
        # === VALIDATE IMAGE BYTES ===
        if not image_bytes or len(image_bytes) < 100:
            raise ValueError(f"Generated image is too small or empty ({len(image_bytes) if image_bytes else 0} bytes)")
        
        is_png = image_bytes.startswith(b"\x89PNG\r\n\x1a\n")
        is_jpeg = image_bytes.startswith(b"\xff\xd8\xff")
        if not (is_png or is_jpeg):
            raise ValueError("Corrupt or invalid image format. Image must be a valid PNG or JPEG file.")
            
        extension = "png" if is_png else "jpg"
        filename = f"{entity_id}.{extension}"
        
        # Create directory
        step_path = os.path.join(IMAGES_DIR, project_id, step)
        os.makedirs(step_path, exist_ok=True)
        
        # Save file
        file_path = os.path.join(step_path, filename)
        with open(file_path, "wb") as f:
            f.write(image_bytes)
        
        # Return URL path (for frontend to display)
        return f"/api/images/{project_id}/{step}/{filename}"
