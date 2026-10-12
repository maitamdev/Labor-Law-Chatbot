"""
Toast notification component generator for Streamlit / Web UI.
"""
def create_toast_payload(message: str, toast_type: str = "info", duration_ms: int = 3000) -> dict:
    """Create a structured toast message payload."""
    valid_types = {"info", "success", "warning", "error"}
    t_type = toast_type if toast_type in valid_types else "info"
    return {
        "message": message,
        "type": t_type,
        "duration": duration_ms,
    }

def render_toast_html(payload: dict) -> str:
    """Render toast markup for injection."""
    return f'''<div class="toast-alert toast-{payload["type"]}" role="alert">
        <span>{payload["message"]}</span>
    </div>'''
