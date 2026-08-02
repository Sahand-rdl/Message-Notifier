import os
import anthropic
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from .base import BaseProvider, MessageObservations, ProviderException
from core.media_preprocessor import process_image, transcribe_audio
from core.prompts import VLM_SYSTEM_PROMPT

class AnthropicProvider(BaseProvider):
    def __init__(self):
        load_dotenv()  # Load variables from .env file
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ProviderException("ANTHROPIC_API_KEY not found in environment.")
        
        self.client = anthropic.Anthropic(api_key=api_key)
        # Using the specified default model
        self.model = "claude-sonnet-4-6"

    def extract_observations(
        self,
        text: Optional[str] = None,
        media_path: Optional[str] = None,
        media_type: Optional[str] = None,
        history: Optional[List[Dict[str, Any]]] = None
    ) -> MessageObservations:
        
        content = []
        
        # Handle Image
        if media_type == 'image' and media_path:
            b64_image = process_image(media_path)
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": b64_image,
                },
            })
            
        # Handle Text Prompt
        text_prompt = "Analyze this WhatsApp message and extract the requested observations."
        if text:
            text_prompt += f"\n\nMessage Text:\n{text}"
            
        # Handle Audio Transcriptions
        if media_type == 'voice' and media_path:
            transcript = transcribe_audio(media_path)
            text_prompt += f"\n\nVoice Note Transcript:\n{transcript}"
            
        if history:
            history_text = "\n".join([
                f"- message_id: {h['message_id']} | Text: {h.get('message_text','') or ''} | Media: {h.get('media_type','') or 'none'}"
                for h in history
            ])
            text_prompt += f"\n\nUser Message History:\n{history_text}"
            
        content.append({
            "type": "text",
            "text": text_prompt
        })
        
        schema = MessageObservations.model_json_schema()
        
        try:
            response = self.client.messages.create(
                model=self.model,
                system=VLM_SYSTEM_PROMPT,
                max_tokens=1024,
                tools=[
                    {
                        "name": "submit_observations",
                        "description": "Submit structured observations extracted from the message.",
                        "input_schema": schema
                    }
                ],
                tool_choice={"type": "tool", "name": "submit_observations"},
                messages=[
                    {
                        "role": "user",
                        "content": content
                    }
                ]
            )
            
            # Find the tool use block
            for block in response.content:
                if block.type == "tool_use" and block.name == "submit_observations":
                    return MessageObservations(**block.input)
                    
            raise ProviderException("Anthropic did not call the submit_observations tool.")
            
        except Exception as e:
            raise ProviderException(f"Anthropic API error: {str(e)}")
