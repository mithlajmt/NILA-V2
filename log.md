💬 Messages received: 2
✅ Successful: 2 | ❌ Failed: 1
🧠 AI Responses: 2 | ❌ AI Failures: 0
⏱️  Uptime: 53s
------------------------------------------------------------
2026-01-09 23:31:53,774 - src.services.speech.speech_recognizer - WARNING - ⚠️ Streaming not available, falling back to batch mode
2026-01-09 23:31:53,774 - src.services.speech.speech_recognizer - INFO - 🎯 Ready to listen...
2026-01-09 23:31:53,774 - src.services.speech.audio_capture - INFO - 🎯 Listening via PipeWire...
🎯 Listening... (Speak naturally)
Adjusting to background noise... Done. (Noise: 2266 -> Threshold: 3019)
🗣️ Speech detected (Energy: 3562)
🗣️ Speech detected (Energy: 3222)
✅ Capture complete (9.0s)
2026-01-09 23:32:08,456 - src.services.speech.providers.google_stt_provider - INFO - ✅ Transcribed: 'ഹലോ'
✅ Transcribed successfully

🎤 RECEIVED MESSAGE:
  📝 Text: 'ഹലോ'
  ⏱️  Time: 23:32:08
  📏 Length: 3 characters
  🔤 Words: 1 words
  🔢 Message #: 3
------------------------------------------------------------

🧠 Thinking...2026-01-09 23:32:08,457 - src.services.feedback.feedback_service - INFO - 🤔 Started thinking feedback

============================================================
🤖 ROBOT RESPONSE (Streaming):
============================================================
2026-01-09 23:32:08,457 - src.services.llm.openrouter_provider - INFO - 🧠 Streaming OpenRouter response...
2026-01-09 23:32:09,420 - httpx - INFO - HTTP Request: POST https://openrouter.ai/api/v1/chat/completions "HTTP/1.1 200 OK"
എന്താ ഇപ്പൊ ഹലോ ഒക്കെ ? രാവിലെ വിളിച്ചതല്ലേ.2026-01-09 23:32:09,957 - src.services.feedback.feedback_service - INFO - 💡 Stopped thinking feedback
2026-01-09 23:32:11,246 - httpx - INFO - HTTP Request: POST https://api.elevenlabs.io/v1/text-to-speech/ErXwobaYiN019PkySvjV "HTTP/1.1 200 OK"
2026-01-09 23:32:11,370 - src.services.llm.openrouter_provider - INFO - ✅ Stream complete

============================================================
⏳ Waiting for speech to finish...

📊 LATENCY BREAKDOWN (Time since start)
============================================================
🔷 turn_start                | +0.000s | Total: 0.000s | Start of conversation turn
🔈 tts_generation_start      | +0.000s | Total: 0.000s | Generating: Hey welcome, I'm Nil...
🔈 tts_audio_ready           | +0.000s | Total: 0.000s | 
🔈 tts_request_queued        | +0.000s | Total: 0.000s | 
🔈 tts_playback_start        | +0.000s | Total: 0.000s | Playing: Hey welcom...
🎤 stt_listening_start       | +0.501s | Total: 0.502s | 
🎤 stt_audio_captured        | +4.072s | Total: 4.573s | Bytes: 81600
🎤 stt_final_transcript      | +0.506s | Total: 5.079s | Text: ഹലോ
🧠 llm_request_start         | +0.001s | Total: 5.080s | 
🧠 llm_first_token           | +1.596s | Total: 6.676s | 
🔈 tts_generation_start      | +0.405s | Total: 7.081s | Generating: അയ്യോ നമസ്ക്കാരം....
🔈 tts_audio_ready           | +1.401s | Total: 8.482s | 
🔈 tts_request_queued        | +0.000s | Total: 8.482s | 
🔈 tts_playback_start        | +0.003s | Total: 8.485s | Playing: അയ്യോ നമസ്...
🔈 tts_generation_start      | +0.001s | Total: 8.486s | Generating:  എപ്പഴാ വന്നേ?...
🔈 tts_audio_ready           | +1.262s | Total: 9.748s | 
🔈 tts_request_queued        | +0.000s | Total: 9.748s | 
🔈 tts_playback_start        | +0.216s | Total: 9.964s | Playing:  എപ്പഴാ വന...
🎤 stt_listening_start       | +1.426s | Total: 11.390s | 
🎤 stt_audio_captured        | +4.067s | Total: 15.457s | Bytes: 92160
🎤 stt_final_transcript      | +0.712s | Total: 16.169s | Text: എന്തൊക്കെയുണ്ട് ആശാനേ വിശേഷം
🧠 llm_request_start         | +0.001s | Total: 16.170s | 
🧠 llm_first_token           | +1.338s | Total: 17.508s | 
🔈 tts_generation_start      | +0.162s | Total: 17.670s | Generating: ഓ ഇവിടെ പ്രത്യേകിച്ച...
🔈 tts_audio_ready           | +1.930s | Total: 19.601s | 
🔈 tts_request_queued        | +0.000s | Total: 19.601s | 
🔈 tts_playback_start        | +0.001s | Total: 19.601s | Playing: ഓ ഇവിടെ പ്...
🔈 tts_generation_start      | +0.002s | Total: 19.603s | Generating:  സുഖമായിട്ട് പോകുന്ന...
🔈 tts_audio_ready           | +1.375s | Total: 20.977s | 
🔈 tts_request_queued        | +0.000s | Total: 20.978s | 
🔈 tts_playback_start        | +0.168s | Total: 21.145s | Playing:  സുഖമായിട്...
🎤 stt_listening_start       | +1.763s | Total: 22.909s | 
🎤 stt_listening_start       | +30.410s | Total: 53.319s | 
🎤 stt_audio_captured        | +14.040s | Total: 67.358s | Bytes: 287040
🎤 stt_final_transcript      | +0.642s | Total: 68.000s | Text: ഹലോ
🧠 llm_request_start         | +0.001s | Total: 68.001s | 
🧠 llm_first_token           | +0.964s | Total: 68.965s | 
🔈 tts_generation_start      | +0.536s | Total: 69.501s | Generating: എന്താ ഇപ്പൊ ഹലോ ഒക്ക...
🔈 tts_audio_ready           | +1.410s | Total: 70.912s | 
🔈 tts_request_queued        | +0.000s | Total: 70.912s | 
🔈 tts_playback_start        | +0.001s | Total: 70.913s | Playing: എന്താ ഇപ്പ...
============================================================

📈 KEY METRICS:
  • STT Processing           : 0.642s
  • LLM Time-to-First-Token  : 0.964s
  • TTS Generation           : -0.000s
  • Total Voice-to-Voice     : 3.555s
------------------------------------------------------------

============================================================
🎯 ROBOT LISTENING MODE - AI ACTIVE 🧠
============================================================
💬 Messages received: 3
✅ Successful: 3 | ❌ Failed: 1
🧠 AI Responses: 3 | ❌ AI Failures: 0
⏱️  Uptime: 73s
------------------------------------------------------------
2026-01-09 23:32:14,284 - src.services.speech.speech_recognizer - WARNING - ⚠️ Streaming not available, falling back to batch mode
2026-01-09 23:32:14,284 - src.services.speech.speech_recognizer - INFO - 🎯 Ready to listen...
2026-01-09 23:32:14,285 - src.services.speech.audio_capture - INFO - 🎯 Listening via PipeWire...
🎯 Listening... (Speak naturally)
Adjusting to background noise... Done. (Noise: 2265 -> Threshold: 3018)
🗣️ Speech detected (Energy: 3098)
✅ Capture complete (2.4s)
2026-01-09 23:32:18,987 - src.services.speech.providers.google_stt_provider - INFO - ✅ Transcribed: 'തൂറിയോ നീ തൂറിയോ'
✅ Transcribed successfully

🎤 RECEIVED MESSAGE:
  📝 Text: 'തൂറിയോ നീ തൂറിയോ'
  ⏱️  Time: 23:32:18
  📏 Length: 16 characters
  🔤 Words: 3 words
  🔢 Message #: 4
------------------------------------------------------------

🧠 Thinking...2026-01-09 23:32:18,987 - src.services.feedback.feedback_service - INFO - 🤔 Started thinking feedback

============================================================
🤖 ROBOT RESPONSE (Streaming):
============================================================
2026-01-09 23:32:18,988 - src.services.llm.openrouter_provider - INFO - 🧠 Streaming OpenRouter response...
2026-01-09 23:32:20,154 - httpx - INFO - HTTP Request: POST https://openrouter.ai/api/v1/chat/completions "HTTP/1.1 200 OK"
അയ്യോ ഞാൻ ഒരു റോബോട്ടാ. എനിക്ക് വിശപ്പ് ദാഹം ഒന്നുമില്ല.2026-01-09 23:32:20,488 - src.services.feedback.feedback_service - INFO - 💡 Stopped thinking feedback
2026-01-09 23:32:21,680 - httpx - INFO - HTTP Request: POST https://api.elevenlabs.io/v1/text-to-speech/ErXwobaYiN019PkySvjV "HTTP/1.1 200 OK"
2026-01-09 23:32:21,812 - src.services.llm.openrouter_provider - INFO - ✅ Stream complete
2026-01-09 23:32:23,097 - httpx - INFO - HTTP Request: POST https://api.elevenlabs.io/v1/text-to-speech/ErXwobaYiN019PkySvjV "HTTP/1.1 200 OK"

============================================================
⏳ Waiting for speech to finish...

📊 LATENCY BREAKDOWN (Time since start)
============================================================
🔷 turn_start                | +0.000s | Total: 0.000s | Start of conversation turn
🔈 tts_generation_start      | +0.000s | Total: 0.000s | Generating: Hey welcome, I'm Nil...
🔈 tts_audio_ready           | +0.000s | Total: 0.000s | 
🔈 tts_request_queued        | +0.000s | Total: 0.000s | 
🔈 tts_playback_start        | +0.000s | Total: 0.000s | Playing: Hey welcom...
🎤 stt_listening_start       | +0.501s | Total: 0.502s | 
🎤 stt_audio_captured        | +4.072s | Total: 4.573s | Bytes: 81600
🎤 stt_final_transcript      | +0.506s | Total: 5.079s | Text: ഹലോ
🧠 llm_request_start         | +0.001s | Total: 5.080s | 
🧠 llm_first_token           | +1.596s | Total: 6.676s | 
🔈 tts_generation_start      | +0.405s | Total: 7.081s | Generating: അയ്യോ നമസ്ക്കാരം....
🔈 tts_audio_ready           | +1.401s | Total: 8.482s | 
🔈 tts_request_queued        | +0.000s | Total: 8.482s | 
🔈 tts_playback_start        | +0.003s | Total: 8.485s | Playing: അയ്യോ നമസ്...
🔈 tts_generation_start      | +0.001s | Total: 8.486s | Generating:  എപ്പഴാ വന്നേ?...
🔈 tts_audio_ready           | +1.262s | Total: 9.748s | 
🔈 tts_request_queued        | +0.000s | Total: 9.748s | 
🔈 tts_playback_start        | +0.216s | Total: 9.964s | Playing:  എപ്പഴാ വന...
🎤 stt_listening_start       | +1.426s | Total: 11.390s | 
🎤 stt_audio_captured        | +4.067s | Total: 15.457s | Bytes: 92160
🎤 stt_final_transcript      | +0.712s | Total: 16.169s | Text: എന്തൊക്കെയുണ്ട് ആശാനേ വിശേഷം
🧠 llm_request_start         | +0.001s | Total: 16.170s | 
🧠 llm_first_token           | +1.338s | Total: 17.508s | 
🔈 tts_generation_start      | +0.162s | Total: 17.670s | Generating: ഓ ഇവിടെ പ്രത്യേകിച്ച...
🔈 tts_audio_ready           | +1.930s | Total: 19.601s | 
🔈 tts_request_queued        | +0.000s | Total: 19.601s | 
🔈 tts_playback_start        | +0.001s | Total: 19.601s | Playing: ഓ ഇവിടെ പ്...
🔈 tts_generation_start      | +0.002s | Total: 19.603s | Generating:  സുഖമായിട്ട് പോകുന്ന...
🔈 tts_audio_ready           | +1.375s | Total: 20.977s | 
🔈 tts_request_queued        | +0.000s | Total: 20.978s | 
🔈 tts_playback_start        | +0.168s | Total: 21.145s | Playing:  സുഖമായിട്...
🎤 stt_listening_start       | +1.763s | Total: 22.909s | 
🎤 stt_listening_start       | +30.410s | Total: 53.319s | 
🎤 stt_audio_captured        | +14.040s | Total: 67.358s | Bytes: 287040
🎤 stt_final_transcript      | +0.642s | Total: 68.000s | Text: ഹലോ
🧠 llm_request_start         | +0.001s | Total: 68.001s | 
🧠 llm_first_token           | +0.964s | Total: 68.965s | 
🔈 tts_generation_start      | +0.536s | Total: 69.501s | Generating: എന്താ ഇപ്പൊ ഹലോ ഒക്ക...
🔈 tts_audio_ready           | +1.410s | Total: 70.912s | 
🔈 tts_request_queued        | +0.000s | Total: 70.912s | 
🔈 tts_playback_start        | +0.001s | Total: 70.913s | Playing: എന്താ ഇപ്പ...
🎤 stt_listening_start       | +2.916s | Total: 73.829s | 
🎤 stt_audio_captured        | +4.062s | Total: 77.891s | Bytes: 77760
🎤 stt_final_transcript      | +0.641s | Total: 78.531s | Text: തൂറിയോ നീ തൂറിയോ
🧠 llm_request_start         | +0.001s | Total: 78.532s | 
🧠 llm_first_token           | +1.317s | Total: 79.848s | 
🔈 tts_generation_start      | +0.184s | Total: 80.032s | Generating: അയ്യോ ഞാൻ ഒരു റോബോട്...
🔈 tts_audio_ready           | +1.322s | Total: 81.354s | 
🔈 tts_request_queued        | +0.000s | Total: 81.354s | 
🔈 tts_playback_start        | +0.000s | Total: 81.354s | Playing: അയ്യോ ഞാൻ ...
🔈 tts_generation_start      | +0.003s | Total: 81.357s | Generating:  എനിക്ക് വിശപ്പ് ദാഹ...
🔈 tts_audio_ready           | +1.338s | Total: 82.695s | 
🔈 tts_request_queued        | +0.000s | Total: 82.695s | 
🔈 tts_playback_start        | +0.393s | Total: 83.089s | Playing:  എനിക്ക് വ...
============================================================

📈 KEY METRICS:
  • STT Processing           : 0.641s
  • LLM Time-to-First-Token  : 1.317s
  • TTS Generation           : -0.000s
  • Total Voice-to-Voice     : 5.198s
------------------------------------------------------------

============================================================
🎯 ROBOT LISTENING MODE - AI ACTIVE 🧠
============================================================
💬 Messages received: 4
✅ Successful: 4 | ❌ Failed: 1
🧠 AI Responses: 4 | ❌ AI Failures: 0
⏱️  Uptime: 84s
------------------------------------------------------------
2026-01-09 23:32:25,437 - src.services.speech.speech_recognizer - WARNING - ⚠️ Streaming not available, falling back to batch mode
2026-01-09 23:32:25,437 - src.services.speech.speech_recognizer - INFO - 🎯 Ready to listen...
2026-01-09 23:32:25,437 - src.services.speech.audio_capture - INFO - 🎯 Listening via PipeWire...
🎯 Listening... (Speak naturally)
Adjusting to background noise... Done. (Noise: 2268 -> Threshold: 3021)
🗣️ Speech detected (Energy: 3197)
✅ Capture complete (3.8s)
2026-01-09 23:32:32,322 - src.services.speech.providers.google_stt_provider - INFO - ✅ Transcribed: 'എന്നാലും നീ തൂറും നിൻറെ തീട്ടം വലുതാണ്'
✅ Transcribed successfully

🎤 RECEIVED MESSAGE:
  📝 Text: 'എന്നാലും നീ തൂറും നിൻറെ തീട്ടം വലുതാണ്'
  ⏱️  Time: 23:32:32
  📏 Length: 38 characters
  🔤 Words: 6 words
  🔢 Message #: 5
------------------------------------------------------------

🧠 Thinking...2026-01-09 23:32:32,323 - src.services.feedback.feedback_service - INFO - 🤔 Started thinking feedback

============================================================
🤖 ROBOT RESPONSE (Streaming):
============================================================
2026-01-09 23:32:32,323 - src.services.llm.openrouter_provider - INFO - 🧠 Streaming OpenRouter response...
2026-01-09 23:32:33,577 - httpx - INFO - HTTP Request: POST https://openrouter.ai/api/v1/chat/completions "HTTP/1.1 200 OK"
ഹേയ് ഞാൻ റോബോട്ടാ എന്ന് പറഞ്ഞില്ലേ. റോബോട്ടുകൾക്ക് അത2026-01-09 23:32:33,825 - src.services.feedback.feedback_service - INFO - 💡 Stopped thinking feedback
2026-01-09 23:32:35,158 - httpx - INFO - HTTP Request: POST https://api.elevenlabs.io/v1/text-to-speech/ErXwobaYiN019PkySvjV "HTTP/1.1 200 OK"
ൊന്നും പറ്റില്ല.2026-01-09 23:32:36,773 - httpx - INFO - HTTP Request: POST https://api.elevenlabs.io/v1/text-to-speech/ErXwobaYiN019PkySvjV "HTTP/1.1 200 OK"
2026-01-09 23:32:36,908 - src.services.llm.openrouter_provider - INFO - ✅ Stream complete

============================================================
⏳ Waiting for speech to finish...

📊 LATENCY BREAKDOWN (Time since start)
============================================================
🔷 turn_start                | +0.000s | Total: 0.000s | Start of conversation turn
🔈 tts_generation_start      | +0.000s | Total: 0.000s | Generating: Hey welcome, I'm Nil...
🔈 tts_audio_ready           | +0.000s | Total: 0.000s | 
🔈 tts_request_queued        | +0.000s | Total: 0.000s | 
🔈 tts_playback_start        | +0.000s | Total: 0.000s | Playing: Hey welcom...
🎤 stt_listening_start       | +0.501s | Total: 0.502s | 
🎤 stt_audio_captured        | +4.072s | Total: 4.573s | Bytes: 81600
🎤 stt_final_transcript      | +0.506s | Total: 5.079s | Text: ഹലോ
🧠 llm_request_start         | +0.001s | Total: 5.080s | 
🧠 llm_first_token           | +1.596s | Total: 6.676s | 
🔈 tts_generation_start      | +0.405s | Total: 7.081s | Generating: അയ്യോ നമസ്ക്കാരം....
🔈 tts_audio_ready           | +1.401s | Total: 8.482s | 
🔈 tts_request_queued        | +0.000s | Total: 8.482s | 
🔈 tts_playback_start        | +0.003s | Total: 8.485s | Playing: അയ്യോ നമസ്...
🔈 tts_generation_start      | +0.001s | Total: 8.486s | Generating:  എപ്പഴാ വന്നേ?...
🔈 tts_audio_ready           | +1.262s | Total: 9.748s | 
🔈 tts_request_queued        | +0.000s | Total: 9.748s | 
🔈 tts_playback_start        | +0.216s | Total: 9.964s | Playing:  എപ്പഴാ വന...
🎤 stt_listening_start       | +1.426s | Total: 11.390s | 
🎤 stt_audio_captured        | +4.067s | Total: 15.457s | Bytes: 92160
🎤 stt_final_transcript      | +0.712s | Total: 16.169s | Text: എന്തൊക്കെയുണ്ട് ആശാനേ വിശേഷം
🧠 llm_request_start         | +0.001s | Total: 16.170s | 
🧠 llm_first_token           | +1.338s | Total: 17.508s | 
🔈 tts_generation_start      | +0.162s | Total: 17.670s | Generating: ഓ ഇവിടെ പ്രത്യേകിച്ച...
🔈 tts_audio_ready           | +1.930s | Total: 19.601s | 
🔈 tts_request_queued        | +0.000s | Total: 19.601s | 
🔈 tts_playback_start        | +0.001s | Total: 19.601s | Playing: ഓ ഇവിടെ പ്...
🔈 tts_generation_start      | +0.002s | Total: 19.603s | Generating:  സുഖമായിട്ട് പോകുന്ന...
🔈 tts_audio_ready           | +1.375s | Total: 20.977s | 
🔈 tts_request_queued        | +0.000s | Total: 20.978s | 
🔈 tts_playback_start        | +0.168s | Total: 21.145s | Playing:  സുഖമായിട്...
🎤 stt_listening_start       | +1.763s | Total: 22.909s | 
🎤 stt_listening_start       | +30.410s | Total: 53.319s | 
🎤 stt_audio_captured        | +14.040s | Total: 67.358s | Bytes: 287040
🎤 stt_final_transcript      | +0.642s | Total: 68.000s | Text: ഹലോ
🧠 llm_request_start         | +0.001s | Total: 68.001s | 
🧠 llm_first_token           | +0.964s | Total: 68.965s | 
🔈 tts_generation_start      | +0.536s | Total: 69.501s | Generating: എന്താ ഇപ്പൊ ഹലോ ഒക്ക...
🔈 tts_audio_ready           | +1.410s | Total: 70.912s | 
🔈 tts_request_queued        | +0.000s | Total: 70.912s | 
🔈 tts_playback_start        | +0.001s | Total: 70.913s | Playing: എന്താ ഇപ്പ...
🎤 stt_listening_start       | +2.916s | Total: 73.829s | 
🎤 stt_audio_captured        | +4.062s | Total: 77.891s | Bytes: 77760
🎤 stt_final_transcript      | +0.641s | Total: 78.531s | Text: തൂറിയോ നീ തൂറിയോ
🧠 llm_request_start         | +0.001s | Total: 78.532s | 
🧠 llm_first_token           | +1.317s | Total: 79.848s | 
🔈 tts_generation_start      | +0.184s | Total: 80.032s | Generating: അയ്യോ ഞാൻ ഒരു റോബോട്...
🔈 tts_audio_ready           | +1.322s | Total: 81.354s | 
🔈 tts_request_queued        | +0.000s | Total: 81.354s | 
🔈 tts_playback_start        | +0.000s | Total: 81.354s | Playing: അയ്യോ ഞാൻ ...
🔈 tts_generation_start      | +0.003s | Total: 81.357s | Generating:  എനിക്ക് വിശപ്പ് ദാഹ...
🔈 tts_audio_ready           | +1.338s | Total: 82.695s | 
🔈 tts_request_queued        | +0.000s | Total: 82.695s | 
🔈 tts_playback_start        | +0.393s | Total: 83.089s | Playing:  എനിക്ക് വ...
🎤 stt_listening_start       | +1.893s | Total: 84.981s | 
🎤 stt_audio_captured        | +6.073s | Total: 91.054s | Bytes: 121920
🎤 stt_final_transcript      | +0.812s | Total: 91.866s | Text: എന്നാലും നീ തൂറും നിൻറെ തീട്ടം വലുതാണ്
🧠 llm_request_start         | +0.001s | Total: 91.867s | 
🧠 llm_first_token           | +1.255s | Total: 93.122s | 
🔈 tts_generation_start      | +0.248s | Total: 93.370s | Generating: ഹേയ് ഞാൻ റോബോട്ടാ എന...
🔈 tts_audio_ready           | +1.642s | Total: 95.012s | 
🔈 tts_request_queued        | +0.000s | Total: 95.012s | 
🔈 tts_playback_start        | +0.000s | Total: 95.012s | Playing: ഹേയ് ഞാൻ റ...
🔈 tts_generation_start      | +0.001s | Total: 95.013s | Generating:  റോബോട്ടുകൾക്ക് അതൊന...
🔈 tts_audio_ready           | +1.438s | Total: 96.452s | 
🔈 tts_request_queued        | +0.000s | Total: 96.452s | 
🔈 tts_playback_start        | +1.128s | Total: 97.580s | Playing:  റോബോട്ടുക...
============================================================

📈 KEY METRICS:
  • STT Processing           : 0.812s
  • LLM Time-to-First-Token  : 1.255s
  • TTS Generation           : -0.000s
  • Total Voice-to-Voice     : 6.525s
------------------------------------------------------------

============================================================
🎯 ROBOT LISTENING MODE - AI ACTIVE 🧠
============================================================
💬 Messages received: 5
✅ Successful: 5 | ❌ Failed: 1
🧠 AI Responses: 5 | ❌ AI Failures: 0
⏱️  Uptime: 100s
------------------------------------------------------------
2026-01-09 23:32:40,945 - src.services.speech.speech_recognizer - WARNING - ⚠️ Streaming not available, falling back to batch mode
2026-01-09 23:32:40,945 - src.services.speech.speech_recognizer - INFO - 🎯 Ready to listen...
2026-01-09 23:32:40,945 - src.services.speech.audio_capture - INFO - 🎯 Listening via PipeWire...
🎯 Listening... (Speak naturally)
Adjusting to background noise...^C2026-01-09 23:32:41,591 - src.core.robot_controller - INFO - ⏸️ Shutdown signal received...
 Done. (Noise: 0 -> Threshold: 300)
2026-01-09 23:32:41,591 - src.core.robot_controller - INFO - 🛑 Robot stopping...
⚠️ No speech detected. Try again!

============================================================
📊 SESSION STATISTICS
============================================================
💬 Total messages: 5
✅ Successful transcriptions: 5
❌ Failed transcriptions: 2
🧠 AI Responses: 5
❌ AI Failures: 0
📊 Total tokens used: 0
💰 Estimated cost: $0.0000
⏱️  Session duration: 101s (1.7 minutes)
📈 Average time per message: 20.3s
🎯 Success rate: 71.4%
============================================================

2026-01-09 23:32:41,894 - src.core.robot_controller - INFO - ✅ Step 3 complete!
2026-01-09 23:32:41,894 - src.services.tts.tts_service - INFO - 🛑 TTS Worker cancelled
2026-01-09 23:32:41,895 - src.core.robot_controller - INFO - 🧹 Cleaning up robot resources...
2026-01-09 23:32:41,895 - src.services.speech.speech_recognizer - INFO - 🧽 Cleaning up speech recognizer...
2026-01-09 23:32:41,895 - src.services.llm.openrouter_provider - INFO - 🧹 Cleaning up OpenRouter provider...
2026-01-09 23:32:41,919 - src.core.robot_controller - INFO - ✅ Cleanup complete
(venv) learnlogicai@raspberrypi:~/Desktop/robotlatest/NILA-V2 $ 