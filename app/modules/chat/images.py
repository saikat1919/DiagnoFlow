import base64
from app.core.exceptions.errors import ValidationError

MAX_IMAGE_BYTES = 8 * 1024 * 1024


def image_data_url(data: bytes) -> str:
    if not data:
        raise ValidationError("Uploaded image is empty")
    if len(data) > MAX_IMAGE_BYTES:
        raise ValidationError("Image must be at most 8 MB")
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        mime = "image/png"
    elif data[:3] == b"\xff\xd8\xff":
        mime = "image/jpeg"
    elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        mime = "image/webp"
    else:
        raise ValidationError("Upload a PNG, JPG or WEBP image")
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{encoded}"