import asyncio
import sounddevice as sd
import numpy as np
import base64
import json
import os
import websockets
import asyncio

API_KEY = os.getenv("OPENAI_API_KEY") or ""
MODEL = "gpt-4o-realtime-preview"

SAMPLE_RATE = 24000
MIC_DEVICE = 12   # your working mic device


async def request_response(ws, pcm_data):
    # Convert audio to base64
    audio_b64 = base64.b64encode(pcm_data).decode()

    # Send audio chunk
    await ws.send(json.dumps({
        "type": "input_audio_buffer.append",
        "audio": audio_b64
    }))

    # Commit audio
    await ws.send(json.dumps({"type": "input_audio_buffer.commit"}))

    # Ask AI to give response
    await ws.send(json.dumps({"type": "response.create"}))

    print("🔄 Waiting for AI response…")

    # Speaker output
    with sd.OutputStream(channels=1, samplerate=SAMPLE_RATE, dtype="int16") as out:

        while True:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=10)
            except asyncio.TimeoutError:
                print("❌ AI response timed out.")
                break

            data = json.loads(msg)

            # TTS streaming audio
            if data.get("type") == "response.audio.delta":
                audio_bytes = base64.b64decode(data["audio"])
                out.write(np.frombuffer(audio_bytes, dtype=np.int16))

            # Completed
            if data.get("type") == "response.completed":
                print("✅ AI Finished.\n")
                break


async def main():
    uri = f"wss://api.openai.com/v1/realtime?model=gpt-4o-mini-realtime"

    async with websockets.connect(
        uri,
        additional_headers=[("Authorization", f"Bearer {API_KEY}")]
    ) as ws:

        # Kerala personality
        await ws.send(json.dumps({
            "type": "session.update",
            "session": {
                "instructions": "Reply short, friendly, and with a Kerala accent. Understand Malayalam, Manglish, English."
            }
        }))

        print("Ready.\n")

        while True:
            input("Press ENTER to record 5 seconds…")

            print("🎤 Recording...")
            audio = sd.rec(
                int(5 * SAMPLE_RATE),
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="int16",
                device=MIC_DEVICE
            )
            sd.wait()
            pcm_data = audio.tobytes()

            print("➡ Sending to AI…")
            await request_response(ws, pcm_data)


asyncio.run(main())
