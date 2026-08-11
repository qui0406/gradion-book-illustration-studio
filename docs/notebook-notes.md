# Notes from Google's Book Illustration notebook
(Run on: 2026-08-11)

## 1. Models used
- Text model: gemini-2.5-flash
- Image model: nano-banana

## 2. Context-chaining mechanism
Interactions API — The notebook utilizes the updated client.interactions pipeline. The book text file is uploaded once via the File API. Subsequent instructions reuse the conversation context state (book_interaction) by appending requests across different code cells without re-sending the whole file data.

    book = client.files.upload(file="book.txt")
    
    book_interaction = client.interactions.create(
        model=GEMINI_MODEL_ID,
        input=[
            {"type": "text", "text": "Here's a book, to illustrate using Nano Banana. Don't say anything for now, instructions will follow."},
            {"type": "document", "uri": book.uri},
        ],
    )

## 3. Structured output — Characters
    from pydantic import BaseModel

    class CharacterPrompt(BaseModel):
        name: str
        prompt: str

    class CharacterPromptsList(BaseModel):
        characters: list[CharacterPrompt]

## 4. Structured output — Chapters
    from pydantic import BaseModel

    class ChapterIllustrationPrompt(BaseModel):
        chapter_number: int
        title: str
        prompt: str

    class BookIllustrationsList(BaseModel):
        chapters: list[ChapterIllustrationPrompt]


## 5. Portrait generation input
    response = client.models.generate_images(
        model='nano-banana',
        prompt=character.prompt,
        config=dict(numberOfImages=1, aspectRatio="1:1")
    )


## 6. Illustration generation input
No. The pipeline never reuses the generated portrait files or images as physical pixel inputs (neither via base64 arrays nor file storage URI pointers).How it works: Character consistency is maintained purely using textual prompt alignment. The descriptive textual elements generated in Step 3 are concatenated directly into the structural chapter context prompts in Step 4. The image model generates consistent character designs based on these deep text references.

## 7. Corresponding REST endpoints
- generateContent: POST https://googleapis.com{model}:generateContent
- File upload: POST https://googleapis.com (triggered by client.files.upload)
- Chat/conversation continuation: POST https://googleapis.com