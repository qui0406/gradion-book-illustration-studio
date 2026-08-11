"""
Gemini API Service Skeleton.

Handles interactions with Google Gemini API for:
- Uploading book text once (via file API or chat session reference).
- Extracting art style options.
- Extracting main adult characters (validated to max 2).
- Generating character portraits sequentially.
- Extracting chapter summaries (validated to max 1).
- Generating chapter illustrations sequentially, using portrait images as input for character consistency.
"""


def upload_book_content(project_id: str, content: str):
    """
    Skeleton: Send book text to Gemini ONLY ONCE and store chat session / file reference.
    """
    pass


def extract_art_style(project_id: str):
    """
    Skeleton: Analyze book content and extract art style suggestions.
    """
    pass


def extract_characters(project_id: str):
    """
    Skeleton: Extract adult characters from book content (truncate/validate max 2 characters).
    """
    pass


def generate_portraits_sequential(project_id: str):
    """
    Skeleton: Generate character portraits sequentially, updating progress state after each image.
    """
    pass


def extract_chapters(project_id: str):
    """
    Skeleton: Extract chapter breakdown from book content (truncate/validate max 1 chapter).
    """
    pass


def generate_illustrations_sequential(project_id: str):
    """
    Skeleton: Generate chapter illustrations sequentially using portrait images as input context.
    """
    pass
