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
        
        ⚠️ KNOWN ISSUE: Không validate image trước khi lưu.
        Nếu image bị corrupt hoặc quá nhỏ, vẫn lưu vào disk.
        Sẽ fix ở phần sau.
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
                # ⚠️ LỖ HỔNG: Không validate image trước khi lưu
                # - Không kiểm tra kích thước
                # - Không kiểm tra image có bị corrupt không
                # - Không kiểm tra định dạng
                # → Có thể lưu ảnh lỗi vào disk!
                
                filename = f"{character.name}.png"
                image_path = self._save_image(
                    project_id=project_id,
                    step="portraits",
                    filename=filename,
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
                logger.error(f"❌ No image generated for {character.name}")
                # ⚠️ LỖ HỔNG: Không raise exception, vẫn tiếp tục với character tiếp theo
                # → User không biết character nào bị lỗi
            
            last_interaction_id = portrait_interaction.id
        
        logger.info(f"Portrait generation completed: {len(portraits)}/{len(characters)} portraits generated")
        return portraits
    
    def _save_image(self, project_id: str, step: str, filename: str, image_data: str) -> str:
        """Save image to disk and return URL path.
        
        ⚠️ KNOWN ISSUE: Không validate image trước khi lưu.
        """
        # Decode base64 image
        if isinstance(image_data, str):
            image_bytes = base64.b64decode(image_data)
        else:
            image_bytes = image_data
        
        # ⚠️ LỖ HỔNG: Không kiểm tra image_bytes có hợp lệ không
        # - Không kiểm tra len(image_bytes) > 0
        # - Không kiểm tra image có đúng định dạng PNG không
        # - Không kiểm tra image có bị corrupt không
        
        # Create directory
        step_path = os.path.join(IMAGES_DIR, project_id, step)
        os.makedirs(step_path, exist_ok=True)
        
        # Save file
        file_path = os.path.join(step_path, filename)
        with open(file_path, "wb") as f:
            f.write(image_bytes)
        
        # Return URL path (for frontend to display)
        return f"/images/{project_id}/{step}/{filename}"
