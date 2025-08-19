import markdown
import bleach

def markdown_to_html(markdown_text: str) -> str:
    """Convert markdown to safe HTML with custom styling"""
    # Convert markdown to HTML
    html = markdown.markdown(
        markdown_text,
        extensions=['tables', 'fenced_code', 'nl2br']
    )
    
    # Configure allowed HTML tags and attributes
    allowed_tags = [
        'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li',
        'strong', 'em', 'code', 'pre', 'blockquote', 'table', 'thead',
        'tbody', 'tr', 'th', 'td', 'br'
    ]
    
    allowed_attributes = {
        '*': ['class', 'style']
    }
    
    # Sanitize HTML
    clean_html = bleach.clean(
        html,
        tags=allowed_tags,
        attributes=allowed_attributes
    )
    
    return clean_html
