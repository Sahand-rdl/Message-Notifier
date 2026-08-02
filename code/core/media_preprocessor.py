import io
import base64
from PIL import Image
import whisper

# Global cache for whisper model to avoid reloading on every message
_WHISPER_MODEL = None

def transcribe_audio(file_path: str) -> str:
    """
    Loads Whisper (base model) and transcribes the audio file.
    """
    global _WHISPER_MODEL
    if _WHISPER_MODEL is None:
        _WHISPER_MODEL = whisper.load_model("base")
    
    result = _WHISPER_MODEL.transcribe(file_path)
    return result["text"].strip()

def process_image(file_path: str) -> str:
    """
    Downscales image if longest edge > 896 using Resampling.LANCZOS.
    Returns base64 encoded string of the JPEG.
    """
    with Image.open(file_path) as img:
        # Convert to RGB if necessary (e.g., if it's RGBA/PNG)
        if img.mode != "RGB":
            img = img.convert("RGB")
            
        max_size = 896
        width, height = img.size
        
        if width > max_size or height > max_size:
            if width > height:
                new_width = max_size
                new_height = int(max_size * (height / width))
            else:
                new_height = max_size
                new_width = int(max_size * (width / height))
            
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")
