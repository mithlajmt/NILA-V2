import os
import logging
import torch
from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import FileResponse
from pydantic import BaseModel
from parler_tts import ParlerTTSForConditionalGeneration
from transformers import AutoTokenizer
import soundfile as sf
import uuid

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI4Bharat TTS Server")

# Global Variables for Model
model = None
tokenizer = None
device = "cuda" if torch.cuda.is_available() else "cpu"

# Configuration
MODEL_NAME = "ai4bharat/indic-parler-tts"

class TTSRequest(BaseModel):
    text: str
    description: str = "A male speaker delivering a slightly expressive and animated speech with a moderate speed and pitch."
    language: str = "en" # Not strictly used by Parler-TTS as it's multilingual, but good for context

@app.on_event("startup")
async def load_model():
    global model, tokenizer
    logger.info(f"🚀 Loading model {MODEL_NAME} on {device}...")
    try:
        model = ParlerTTSForConditionalGeneration.from_pretrained(MODEL_NAME).to(device)
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        logger.info("✅ Model loaded successfully!")
    except Exception as e:
        logger.error(f"❌ Failed to load model: {e}")
        raise RuntimeError("Model loading failed")

@app.get("/health")
async def health_check():
    return {"status": "ok", "device": device, "model": MODEL_NAME}

@app.post("/v1/audio/speech")
async def generate_speech(request: TTSRequest):
    global model, tokenizer
    
    if not model:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        logger.info(f"🗣️ Generating speech for: {request.text[:50]}...")
        
        # Tokenize description and prompt
        input_ids = tokenizer(request.description, return_tensors="pt").input_ids.to(device)
        prompt_input_ids = tokenizer(request.text, return_tensors="pt").input_ids.to(device)
        
        # Generate audio
        generation = model.generate(input_ids=input_ids, prompt_input_ids=prompt_input_ids)
        audio_arr = generation.cpu().numpy().squeeze()
        
        # Save to temporary file
        filename = f"output_{uuid.uuid4()}.wav"
        sf.write(filename, audio_arr, model.config.sampling_rate)
        
        logger.info(f"✅ Audio generated: {filename}")
        
        # Return file
        return FileResponse(filename, media_type="audio/wav", filename=filename)
        
    except Exception as e:
        logger.error(f"❌ Generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
