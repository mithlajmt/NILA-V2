============================================================
🤖 ROBOT RESPONSE (Streaming):
============================================================
2026-01-10 00:18:55,860 - src.services.llm.openrouter_provider - INFO - 🧠 Streaming OpenRouter response...
2026-01-10 00:18:57,203 - httpx - INFO - HTTP Request: POST https://openrouter.ai/api/v1/chat/completions "HTTP/1.1 200 OK"
അയ്യോ, ഇത് ആരാ സന്ധ്യക്ക്? സുഖമാണോ?2026-01-10 00:18:57,860 - src.services.feedback.feedback_service - INFO - 💡 Stopped thinking feedback
2026-01-10 00:18:58,732 - src.services.llm.openrouter_provider - INFO - ✅ Stream complete

============================================================
⏳ Waiting for speech to finish...

📊 LATENCY BREAKDOWN (Time since start)
============================================================
🔷 turn_start                | +0.000s | Total: 0.000s | Start of conversation turn
🔈 tts_generation_start      | +0.000s | Total: 0.000s | Generating: Hey welcome, I'm Nil...
🔈 tts_audio_ready           | +1.727s | Total: 1.727s | 
🔈 tts_request_queued        | +0.000s | Total: 1.727s | 
🔈 tts_playback_start        | +0.000s | Total: 1.727s | Playing: Hey welcom...
🎤 stt_listening_start       | +0.501s | Total: 2.228s | 
🔷 vad_speech_start          | +2.660s | Total: 4.889s | Energy: 12390
🔷 vad_speech_start          | +0.961s | Total: 5.850s | Energy: 14097
🔷 vad_speech_start          | +0.705s | Total: 6.555s | Energy: 14391
🔷 vad_speech_end            | +1.218s | Total: 7.774s | Duration: 0.7s
🎤 stt_audio_captured        | +0.001s | Total: 7.775s | Bytes: 100800
🎤 stt_final_transcript      | +0.454s | Total: 8.229s | Text: ഹലോ
🧠 llm_request_start         | +0.001s | Total: 8.229s | 
🧠 llm_first_token           | +1.361s | Total: 9.591s | 
🔈 tts_generation_start      | +0.639s | Total: 10.230s | Generating: അയ്യോ, ഇത് ആരാ സന്ധ്...
🔈 tts_audio_ready           | +0.864s | Total: 11.093s | 
🔈 tts_request_queued        | +0.000s | Total: 11.093s | 
🔈 tts_playback_start        | +0.000s | Total: 11.094s | Playing: അയ്യോ, ഇത്...
🔈 tts_generation_start      | +0.009s | Total: 11.102s | Generating:  സുഖമാണോ?...
🔈 tts_audio_ready           | +0.647s | Total: 11.749s | 
🔈 tts_request_queued        | +0.000s | Total: 11.749s | 
🔈 tts_playback_start        | +0.909s | Total: 12.658s | Playing:  സുഖമാണോ?...
============================================================

📈 KEY METRICS:
  • STT Processing           : 0.454s
  • LLM Time-to-First-Token  : 1.361s
  • TTS Generation           : -0.000s
  • Total Voice-to-Voice     : 4.884s
------------------------------------------------------------

============================================================
🎯 ROBOT LISTENING MODE - AI ACTIVE 🧠
============================================================
💬 Messages received: 1
✅ Successful: 1 | ❌ Failed: 0
🧠 AI Responses: 1 | ❌ AI Failures: 0
⏱️  Uptime: 13s
------------------------------------------------------------
2026-01-10 00:19:01,442 - src.services.speech.speech_recognizer - WARNING - ⚠️ Streaming not available, falling back to batch mode
2026-01-10 00:19:01,443 - src.services.speech.speech_recognizer - INFO - 🎯 Ready to listen...
2026-01-10 00:19:01,443 - src.services.speech.audio_capture - INFO - 🎯 Starting async audio stream (Low Latency Mode)...
🎯 Listening... (Silence cutoff: 0.5s)
Adjusting to noise... Done. (Noise: 7948 → Threshold: 10433)

🗣️ Speech! (Energy: 10553)
✅ Capture complete (1.2s speech)
2026-01-10 00:19:05,822 - src.services.speech.providers.google_stt_provider - INFO - ✅ Transcribed: 'എന്താ പരുപാടി'
✅ Transcribed successfully

🎤 RECEIVED MESSAGE:
  📝 Text: 'എന്താ പരുപാടി'
  ⏱️  Time: 00:19:05
  📏 Length: 13 characters
  🔤 Words: 2 words
  🔢 Message #: 2
------------------------------------------------------------

🧠 Thinking...2026-01-10 00:19:05,823 - src.services.feedback.feedback_service - INFO - 🤔 Started thinking feedback

============================================================
🤖 ROBOT RESPONSE (Streaming):
============================================================
2026-01-10 00:19:05,823 - src.services.llm.openrouter_provider - INFO - 🧠 Streaming OpenRouter response...
2026-01-10 00:19:07,495 - httpx - INFO - HTTP Request: POST https://openrouter.ai/api/v1/chat/completions "HTTP/1.1 200 OK"
അതൊന്നും ചോദിക്കല്ലേ. ഇവിടെ വെറുതെ ഇരിക്കുകയാ.2026-01-10 00:19:07,823 - src.services.feedback.feedback_service - INFO - 💡 Stopped thinking feedback
2026-01-10 00:19:08,531 - src.services.llm.openrouter_provider - INFO - ✅ Stream complete

============================================================
⏳ Waiting for speech to finish...

📊 LATENCY BREAKDOWN (Time since start)
============================================================
🔷 turn_start                | +0.000s | Total: 0.000s | Start of conversation turn
🔈 tts_generation_start      | +0.000s | Total: 0.000s | Generating: Hey welcome, I'm Nil...
🔈 tts_audio_ready           | +1.727s | Total: 1.727s | 
🔈 tts_request_queued        | +0.000s | Total: 1.727s | 
🔈 tts_playback_start        | +0.000s | Total: 1.727s | Playing: Hey welcom...
🎤 stt_listening_start       | +0.501s | Total: 2.228s | 
🔷 vad_speech_start          | +2.660s | Total: 4.889s | Energy: 12390
🔷 vad_speech_start          | +0.961s | Total: 5.850s | Energy: 14097
🔷 vad_speech_start          | +0.705s | Total: 6.555s | Energy: 14391
🔷 vad_speech_end            | +1.218s | Total: 7.774s | Duration: 0.7s
🎤 stt_audio_captured        | +0.001s | Total: 7.775s | Bytes: 100800
🎤 stt_final_transcript      | +0.454s | Total: 8.229s | Text: ഹലോ
🧠 llm_request_start         | +0.001s | Total: 8.229s | 
🧠 llm_first_token           | +1.361s | Total: 9.591s | 
🔈 tts_generation_start      | +0.639s | Total: 10.230s | Generating: അയ്യോ, ഇത് ആരാ സന്ധ്...
🔈 tts_audio_ready           | +0.864s | Total: 11.093s | 
🔈 tts_request_queued        | +0.000s | Total: 11.093s | 
🔈 tts_playback_start        | +0.000s | Total: 11.094s | Playing: അയ്യോ, ഇത്...
🔈 tts_generation_start      | +0.009s | Total: 11.102s | Generating:  സുഖമാണോ?...
🔈 tts_audio_ready           | +0.647s | Total: 11.749s | 
🔈 tts_request_queued        | +0.000s | Total: 11.749s | 
🔈 tts_playback_start        | +0.909s | Total: 12.658s | Playing:  സുഖമാണോ?...
🎤 stt_listening_start       | +1.154s | Total: 13.812s | 
🔷 vad_speech_start          | +2.118s | Total: 15.931s | Energy: 10553
🔷 vad_speech_end            | +1.663s | Total: 17.594s | Duration: 1.2s
🎤 stt_audio_captured        | +0.001s | Total: 17.595s | Bytes: 63360
🎤 stt_final_transcript      | +0.597s | Total: 18.192s | Text: എന്താ പരുപാടി
🧠 llm_request_start         | +0.000s | Total: 18.193s | 
🧠 llm_first_token           | +1.704s | Total: 19.896s | 
🔈 tts_generation_start      | +0.297s | Total: 20.193s | Generating: അതൊന്നും ചോദിക്കല്ലേ...
🔈 tts_audio_ready           | +0.705s | Total: 20.898s | 
🔈 tts_request_queued        | +0.000s | Total: 20.898s | 
🔈 tts_playback_start        | +0.000s | Total: 20.899s | Playing: അതൊന്നും ച...
🔈 tts_generation_start      | +0.003s | Total: 20.901s | Generating:  ഇവിടെ വെറുതെ ഇരിക്ക...
🔈 tts_audio_ready           | +0.828s | Total: 21.729s | 
🔈 tts_request_queued        | +0.000s | Total: 21.729s | 
🔈 tts_playback_start        | +0.333s | Total: 22.063s | Playing:  ഇവിടെ വെറ...
============================================================

📈 KEY METRICS:
  • STT Processing           : 0.597s
  • LLM Time-to-First-Token  : 1.704s
  • TTS Generation           : -0.000s
  • Total Voice-to-Voice     : 4.468s
------------------------------------------------------------

============================================================
🎯 ROBOT LISTENING MODE - AI ACTIVE 🧠
============================================================
💬 Messages received: 2
✅ Successful: 2 | ❌ Failed: 0
🧠 AI Responses: 2 | ❌ AI Failures: 0
⏱️  Uptime: 23s
------------------------------------------------------------
2026-01-10 00:19:11,350 - src.services.speech.speech_recognizer - WARNING - ⚠️ Streaming not available, falling back to batch mode
2026-01-10 00:19:11,350 - src.services.speech.speech_recognizer - INFO - 🎯 Ready to listen...
2026-01-10 00:19:11,351 - src.services.speech.audio_capture - INFO - 🎯 Starting async audio stream (Low Latency Mode)...
🎯 Listening... (Silence cutoff: 0.5s)
Adjusting to noise... Done. (Noise: 8120 → Threshold: 10656)

🗣️ Speech! (Energy: 11157)
✅ Capture complete (2.0s speech)
2026-01-10 00:19:15,390 - src.services.speech.providers.google_stt_provider - INFO - ✅ Transcribed: 'എന്താ വെറുതെയിരിക്കുന്ന വല്ല പണിക്കു പോടാ'
✅ Transcribed successfully

🎤 RECEIVED MESSAGE:
  📝 Text: 'എന്താ വെറുതെയിരിക്കുന്ന വല്ല പണിക്കു പോടാ'
  ⏱️  Time: 00:19:15
  📏 Length: 41 characters
  🔤 Words: 5 words
  🔢 Message #: 3
------------------------------------------------------------

🧠 Thinking...2026-01-10 00:19:15,390 - src.services.feedback.feedback_service - INFO - 🤔 Started thinking feedback

============================================================
🤖 ROBOT RESPONSE (Streaming):
============================================================
2026-01-10 00:19:15,391 - src.services.llm.openrouter_provider - INFO - 🧠 Streaming OpenRouter response...
2026-01-10 00:19:17,358 - httpx - INFO - HTTP Request: POST https://openrouter.ai/api/v1/chat/completions "HTTP/1.1 200 OK"
അത് പിന്നെ എൻ്റെ പണി ഞാൻ ചെയ്യണ്ടേ. ഞാൻ AI അല്ലേ.2026-01-10 00:19:17,891 - src.services.feedback.feedback_service - INFO - 💡 Stopped thinking feedback
2026-01-10 00:19:18,769 - src.services.llm.openrouter_provider - INFO - ✅ Stream complete

============================================================
⏳ Waiting for speech to finish...

📊 LATENCY BREAKDOWN (Time since start)
============================================================
🔷 turn_start                | +0.000s | Total: 0.000s | Start of conversation turn
🔈 tts_generation_start      | +0.000s | Total: 0.000s | Generating: Hey welcome, I'm Nil...
🔈 tts_audio_ready           | +1.727s | Total: 1.727s | 
🔈 tts_request_queued        | +0.000s | Total: 1.727s | 
🔈 tts_playback_start        | +0.000s | Total: 1.727s | Playing: Hey welcom...
🎤 stt_listening_start       | +0.501s | Total: 2.228s | 
🔷 vad_speech_start          | +2.660s | Total: 4.889s | Energy: 12390
🔷 vad_speech_start          | +0.961s | Total: 5.850s | Energy: 14097
🔷 vad_speech_start          | +0.705s | Total: 6.555s | Energy: 14391
🔷 vad_speech_end            | +1.218s | Total: 7.774s | Duration: 0.7s
🎤 stt_audio_captured        | +0.001s | Total: 7.775s | Bytes: 100800
🎤 stt_final_transcript      | +0.454s | Total: 8.229s | Text: ഹലോ
🧠 llm_request_start         | +0.001s | Total: 8.229s | 
🧠 llm_first_token           | +1.361s | Total: 9.591s | 
🔈 tts_generation_start      | +0.639s | Total: 10.230s | Generating: അയ്യോ, ഇത് ആരാ സന്ധ്...
🔈 tts_audio_ready           | +0.864s | Total: 11.093s | 
🔈 tts_request_queued        | +0.000s | Total: 11.093s | 
🔈 tts_playback_start        | +0.000s | Total: 11.094s | Playing: അയ്യോ, ഇത്...
🔈 tts_generation_start      | +0.009s | Total: 11.102s | Generating:  സുഖമാണോ?...
🔈 tts_audio_ready           | +0.647s | Total: 11.749s | 
🔈 tts_request_queued        | +0.000s | Total: 11.749s | 
🔈 tts_playback_start        | +0.909s | Total: 12.658s | Playing:  സുഖമാണോ?...
🎤 stt_listening_start       | +1.154s | Total: 13.812s | 
🔷 vad_speech_start          | +2.118s | Total: 15.931s | Energy: 10553
🔷 vad_speech_end            | +1.663s | Total: 17.594s | Duration: 1.2s
🎤 stt_audio_captured        | +0.001s | Total: 17.595s | Bytes: 63360
🎤 stt_final_transcript      | +0.597s | Total: 18.192s | Text: എന്താ പരുപാടി
🧠 llm_request_start         | +0.000s | Total: 18.193s | 
🧠 llm_first_token           | +1.704s | Total: 19.896s | 
🔈 tts_generation_start      | +0.297s | Total: 20.193s | Generating: അതൊന്നും ചോദിക്കല്ലേ...
🔈 tts_audio_ready           | +0.705s | Total: 20.898s | 
🔈 tts_request_queued        | +0.000s | Total: 20.898s | 
🔈 tts_playback_start        | +0.000s | Total: 20.899s | Playing: അതൊന്നും ച...
🔈 tts_generation_start      | +0.003s | Total: 20.901s | Generating:  ഇവിടെ വെറുതെ ഇരിക്ക...
🔈 tts_audio_ready           | +0.828s | Total: 21.729s | 
🔈 tts_request_queued        | +0.000s | Total: 21.729s | 
🔈 tts_playback_start        | +0.333s | Total: 22.063s | Playing:  ഇവിടെ വെറ...
🎤 stt_listening_start       | +1.657s | Total: 23.720s | 
🔷 vad_speech_start          | +0.748s | Total: 24.468s | Energy: 11157
🔷 vad_speech_end            | +2.460s | Total: 26.928s | Duration: 2.0s
🎤 stt_audio_captured        | +0.001s | Total: 26.928s | Bytes: 89280
🎤 stt_final_transcript      | +0.831s | Total: 27.760s | Text: എന്താ വെറുതെയിരിക്കുന്ന വല്ല പണിക്കു പോടാ
🧠 llm_request_start         | +0.001s | Total: 27.760s | 
🧠 llm_first_token           | +1.972s | Total: 29.732s | 
🔈 tts_generation_start      | +0.529s | Total: 30.261s | Generating: അത് പിന്നെ എൻ്റെ പണി...
🔈 tts_audio_ready           | +0.876s | Total: 31.137s | 
🔈 tts_request_queued        | +0.000s | Total: 31.137s | 
🔈 tts_playback_start        | +0.000s | Total: 31.138s | Playing: അത് പിന്നെ...
🔈 tts_generation_start      | +0.002s | Total: 31.140s | Generating:  ഞാൻ AI അല്ലേ....
🔈 tts_audio_ready           | +0.761s | Total: 31.901s | 
🔈 tts_request_queued        | +0.000s | Total: 31.901s | 
🔈 tts_playback_start        | +1.054s | Total: 32.955s | Playing:  ഞാൻ AI അല...
============================================================

📈 KEY METRICS:
  • STT Processing           : 0.831s
  • LLM Time-to-First-Token  : 1.972s
  • TTS Generation           : -0.000s
  • Total Voice-to-Voice     : 6.026s
------------------------------------------------------------

============================================================
🎯 ROBOT LISTENING MODE - AI ACTIVE 🧠
============================================================
💬 Messages received: 3
✅ Successful: 3 | ❌ Failed: 0
🧠 AI Responses: 3 | ❌ AI Failures: 0
⏱️  Uptime: 34s
------------------------------------------------------------
2026-01-10 00:19:22,140 - src.services.speech.speech_recognizer - WARNING - ⚠️ Streaming not available, falling back to batch mode
2026-01-10 00:19:22,141 - src.services.speech.speech_recognizer - INFO - 🎯 Ready to listen...
2026-01-10 00:19:22,141 - src.services.speech.audio_capture - INFO - 🎯 Starting async audio stream (Low Latency Mode)...
🎯 Listening... (Silence cutoff: 0.5s)
Adjusting to noise... Done. (Noise: 7875 → Threshold: 10338)

🗣️ Speech! (Energy: 10660)
✅ Capture complete (2.5s speech)
2026-01-10 00:19:27,395 - src.services.speech.providers.google_stt_provider - INFO - ✅ Transcribed: 'നീ ഒരു മണ്ടനാണ് കഴുതയെ'
✅ Transcribed successfully

🎤 RECEIVED MESSAGE:
  📝 Text: 'നീ ഒരു മണ്ടനാണ് കഴുതയെ'
  ⏱️  Time: 00:19:27
  📏 Length: 22 characters
  🔤 Words: 4 words
  🔢 Message #: 4
------------------------------------------------------------

🧠 Thinking...2026-01-10 00:19:27,395 - src.services.feedback.feedback_service - INFO - 🤔 Started thinking feedback

============================================================
🤖 ROBOT RESPONSE (Streaming):
============================================================
2026-01-10 00:19:27,396 - src.services.llm.openrouter_provider - INFO - 🧠 Streaming OpenRouter response...
2026-01-10 00:19:28,607 - httpx - INFO - HTTP Request: POST https://openrouter.ai/api/v1/chat/completions "HTTP/1.1 200 OK"
അയ്യോ ഞാൻ ഒന്നും ചെയ്തില്ലല്ലോ. വെറുതെ ചീത്ത പറയുന്നോ2026-01-10 00:19:28,895 - src.services.feedback.feedback_service - INFO - 💡 Stopped thinking feedback
!2026-01-10 00:19:30,466 - src.services.llm.openrouter_provider - INFO - ✅ Stream complete

============================================================
⏳ Waiting for speech to finish...

📊 LATENCY BREAKDOWN (Time since start)
============================================================
🔷 turn_start                | +0.000s | Total: 0.000s | Start of conversation turn
🔈 tts_generation_start      | +0.000s | Total: 0.000s | Generating: Hey welcome, I'm Nil...
🔈 tts_audio_ready           | +1.727s | Total: 1.727s | 
🔈 tts_request_queued        | +0.000s | Total: 1.727s | 
🔈 tts_playback_start        | +0.000s | Total: 1.727s | Playing: Hey welcom...
🎤 stt_listening_start       | +0.501s | Total: 2.228s | 
🔷 vad_speech_start          | +2.660s | Total: 4.889s | Energy: 12390
🔷 vad_speech_start          | +0.961s | Total: 5.850s | Energy: 14097
🔷 vad_speech_start          | +0.705s | Total: 6.555s | Energy: 14391
🔷 vad_speech_end            | +1.218s | Total: 7.774s | Duration: 0.7s
🎤 stt_audio_captured        | +0.001s | Total: 7.775s | Bytes: 100800
🎤 stt_final_transcript      | +0.454s | Total: 8.229s | Text: ഹലോ
🧠 llm_request_start         | +0.001s | Total: 8.229s | 
🧠 llm_first_token           | +1.361s | Total: 9.591s | 
🔈 tts_generation_start      | +0.639s | Total: 10.230s | Generating: അയ്യോ, ഇത് ആരാ സന്ധ്...
🔈 tts_audio_ready           | +0.864s | Total: 11.093s | 
🔈 tts_request_queued        | +0.000s | Total: 11.093s | 
🔈 tts_playback_start        | +0.000s | Total: 11.094s | Playing: അയ്യോ, ഇത്...
🔈 tts_generation_start      | +0.009s | Total: 11.102s | Generating:  സുഖമാണോ?...
🔈 tts_audio_ready           | +0.647s | Total: 11.749s | 
🔈 tts_request_queued        | +0.000s | Total: 11.749s | 
🔈 tts_playback_start        | +0.909s | Total: 12.658s | Playing:  സുഖമാണോ?...
🎤 stt_listening_start       | +1.154s | Total: 13.812s | 
🔷 vad_speech_start          | +2.118s | Total: 15.931s | Energy: 10553
🔷 vad_speech_end            | +1.663s | Total: 17.594s | Duration: 1.2s
🎤 stt_audio_captured        | +0.001s | Total: 17.595s | Bytes: 63360
🎤 stt_final_transcript      | +0.597s | Total: 18.192s | Text: എന്താ പരുപാടി
🧠 llm_request_start         | +0.000s | Total: 18.193s | 
🧠 llm_first_token           | +1.704s | Total: 19.896s | 
🔈 tts_generation_start      | +0.297s | Total: 20.193s | Generating: അതൊന്നും ചോദിക്കല്ലേ...
🔈 tts_audio_ready           | +0.705s | Total: 20.898s | 
🔈 tts_request_queued        | +0.000s | Total: 20.898s | 
🔈 tts_playback_start        | +0.000s | Total: 20.899s | Playing: അതൊന്നും ച...
🔈 tts_generation_start      | +0.003s | Total: 20.901s | Generating:  ഇവിടെ വെറുതെ ഇരിക്ക...
🔈 tts_audio_ready           | +0.828s | Total: 21.729s | 
🔈 tts_request_queued        | +0.000s | Total: 21.729s | 
🔈 tts_playback_start        | +0.333s | Total: 22.063s | Playing:  ഇവിടെ വെറ...
🎤 stt_listening_start       | +1.657s | Total: 23.720s | 
🔷 vad_speech_start          | +0.748s | Total: 24.468s | Energy: 11157
🔷 vad_speech_end            | +2.460s | Total: 26.928s | Duration: 2.0s
🎤 stt_audio_captured        | +0.001s | Total: 26.928s | Bytes: 89280
🎤 stt_final_transcript      | +0.831s | Total: 27.760s | Text: എന്താ വെറുതെയിരിക്കുന്ന വല്ല പണിക്കു പോടാ
🧠 llm_request_start         | +0.001s | Total: 27.760s | 
🧠 llm_first_token           | +1.972s | Total: 29.732s | 
🔈 tts_generation_start      | +0.529s | Total: 30.261s | Generating: അത് പിന്നെ എൻ്റെ പണി...
🔈 tts_audio_ready           | +0.876s | Total: 31.137s | 
🔈 tts_request_queued        | +0.000s | Total: 31.137s | 
🔈 tts_playback_start        | +0.000s | Total: 31.138s | Playing: അത് പിന്നെ...
🔈 tts_generation_start      | +0.002s | Total: 31.140s | Generating:  ഞാൻ AI അല്ലേ....
🔈 tts_audio_ready           | +0.761s | Total: 31.901s | 
🔈 tts_request_queued        | +0.000s | Total: 31.901s | 
🔈 tts_playback_start        | +1.054s | Total: 32.955s | Playing:  ഞാൻ AI അല...
🎤 stt_listening_start       | +1.556s | Total: 34.511s | 
🔷 vad_speech_start          | +1.240s | Total: 35.751s | Energy: 10660
🔷 vad_speech_end            | +3.074s | Total: 38.825s | Duration: 2.5s
🎤 stt_audio_captured        | +0.001s | Total: 38.826s | Bytes: 108480
🎤 stt_final_transcript      | +0.938s | Total: 39.764s | Text: നീ ഒരു മണ്ടനാണ് കഴുതയെ
🧠 llm_request_start         | +0.001s | Total: 39.766s | 
🧠 llm_first_token           | +1.253s | Total: 41.019s | 
🔈 tts_generation_start      | +0.246s | Total: 41.266s | Generating: അയ്യോ ഞാൻ ഒന്നും ചെയ...
🔈 tts_audio_ready           | +0.827s | Total: 42.093s | 
🔈 tts_request_queued        | +0.000s | Total: 42.093s | 
🔈 tts_playback_start        | +0.000s | Total: 42.093s | Playing: അയ്യോ ഞാൻ ...
🔈 tts_generation_start      | +0.002s | Total: 42.095s | Generating:  വെറുതെ ചീത്ത പറയുന്...
🔈 tts_audio_ready           | +0.740s | Total: 42.835s | 
🔈 tts_request_queued        | +0.000s | Total: 42.835s | 
🔈 tts_playback_start        | +0.977s | Total: 43.812s | Playing:  വെറുതെ ചീ...
============================================================

📈 KEY METRICS:
  • STT Processing           : 0.938s
  • LLM Time-to-First-Token  : 1.253s
  • TTS Generation           : -0.000s
  • Total Voice-to-Voice     : 4.985s
------------------------------------------------------------

============================================================
🎯 ROBOT LISTENING MODE - AI ACTIVE 🧠
============================================================
💬 Messages received: 4
✅ Successful: 4 | ❌ Failed: 0
🧠 AI Responses: 4 | ❌ AI Failures: 0
⏱️  Uptime: 45s
------------------------------------------------------------
2026-01-10 00:19:32,948 - src.services.speech.speech_recognizer - WARNING - ⚠️ Streaming not available, falling back to batch mode
2026-01-10 00:19:32,948 - src.services.speech.speech_recognizer - INFO - 🎯 Ready to listen...
2026-01-10 00:19:32,948 - src.services.speech.audio_capture - INFO - 🎯 Starting async audio stream (Low Latency Mode)...
🎯 Listening... (Silence cutoff: 0.5s)
Adjusting to noise... Done. (Noise: 8871 → Threshold: 11632)

🗣️ Speech! (Energy: 11985)
✅ Capture complete (2.8s speech)
2026-01-10 00:19:38,607 - src.services.speech.providers.google_stt_provider - INFO - ✅ Transcribed: 'ഞാൻ ചീത്ത പറയുന്നത് ഞാനാണ് മുതലാളിയാണ് പന്നി'
✅ Transcribed successfully

🎤 RECEIVED MESSAGE:
  📝 Text: 'ഞാൻ ചീത്ത പറയുന്നത് ഞാനാണ് മുതലാളിയാണ് പന്നി'
  ⏱️  Time: 00:19:38
  📏 Length: 44 characters
  🔤 Words: 6 words
  🔢 Message #: 5
------------------------------------------------------------

🧠 Thinking...2026-01-10 00:19:38,608 - src.services.feedback.feedback_service - INFO - 🤔 Started thinking feedback

============================================================
🤖 ROBOT RESPONSE (Streaming):
============================================================
2026-01-10 00:19:38,609 - src.services.llm.openrouter_provider - INFO - 🧠 Streaming OpenRouter response...
2026-01-10 00:19:40,519 - httpx - INFO - HTTP Request: POST https://openrouter.ai/api/v1/chat/completions "HTTP/1.1 200 OK"
നിങ്ങൾ മുതലാളി ആയിക്കോട്ടെ, പക്ഷേ എന്നെ അനാവശ്യമായി ചീത്ത പറയേണ്ട കേട്ടോ.2026-01-10 00:19:41,109 - src.services.feedback.feedback_service - INFO - 💡 Stopped thinking feedback
2026-01-10 00:19:42,493 - src.services.llm.openrouter_provider - INFO - ✅ Stream complete

============================================================
⏳ Waiting for speech to finish...

📊 LATENCY BREAKDOWN (Time since start)
============================================================
🔷 turn_start                | +0.000s | Total: 0.000s | Start of conversation turn
🔈 tts_generation_start      | +0.000s | Total: 0.000s | Generating: Hey welcome, I'm Nil...
🔈 tts_audio_ready           | +1.727s | Total: 1.727s | 
🔈 tts_request_queued        | +0.000s | Total: 1.727s | 
🔈 tts_playback_start        | +0.000s | Total: 1.727s | Playing: Hey welcom...
🎤 stt_listening_start       | +0.501s | Total: 2.228s | 
🔷 vad_speech_start          | +2.660s | Total: 4.889s | Energy: 12390
🔷 vad_speech_start          | +0.961s | Total: 5.850s | Energy: 14097
🔷 vad_speech_start          | +0.705s | Total: 6.555s | Energy: 14391
🔷 vad_speech_end            | +1.218s | Total: 7.774s | Duration: 0.7s
🎤 stt_audio_captured        | +0.001s | Total: 7.775s | Bytes: 100800
🎤 stt_final_transcript      | +0.454s | Total: 8.229s | Text: ഹലോ
🧠 llm_request_start         | +0.001s | Total: 8.229s | 
🧠 llm_first_token           | +1.361s | Total: 9.591s | 
🔈 tts_generation_start      | +0.639s | Total: 10.230s | Generating: അയ്യോ, ഇത് ആരാ സന്ധ്...
🔈 tts_audio_ready           | +0.864s | Total: 11.093s | 
🔈 tts_request_queued        | +0.000s | Total: 11.093s | 
🔈 tts_playback_start        | +0.000s | Total: 11.094s | Playing: അയ്യോ, ഇത്...
🔈 tts_generation_start      | +0.009s | Total: 11.102s | Generating:  സുഖമാണോ?...
🔈 tts_audio_ready           | +0.647s | Total: 11.749s | 
🔈 tts_request_queued        | +0.000s | Total: 11.749s | 
🔈 tts_playback_start        | +0.909s | Total: 12.658s | Playing:  സുഖമാണോ?...
🎤 stt_listening_start       | +1.154s | Total: 13.812s | 
🔷 vad_speech_start          | +2.118s | Total: 15.931s | Energy: 10553
🔷 vad_speech_end            | +1.663s | Total: 17.594s | Duration: 1.2s
🎤 stt_audio_captured        | +0.001s | Total: 17.595s | Bytes: 63360
🎤 stt_final_transcript      | +0.597s | Total: 18.192s | Text: എന്താ പരുപാടി
🧠 llm_request_start         | +0.000s | Total: 18.193s | 
🧠 llm_first_token           | +1.704s | Total: 19.896s | 
🔈 tts_generation_start      | +0.297s | Total: 20.193s | Generating: അതൊന്നും ചോദിക്കല്ലേ...
🔈 tts_audio_ready           | +0.705s | Total: 20.898s | 
🔈 tts_request_queued        | +0.000s | Total: 20.898s | 
🔈 tts_playback_start        | +0.000s | Total: 20.899s | Playing: അതൊന്നും ച...
🔈 tts_generation_start      | +0.003s | Total: 20.901s | Generating:  ഇവിടെ വെറുതെ ഇരിക്ക...
🔈 tts_audio_ready           | +0.828s | Total: 21.729s | 
🔈 tts_request_queued        | +0.000s | Total: 21.729s | 
🔈 tts_playback_start        | +0.333s | Total: 22.063s | Playing:  ഇവിടെ വെറ...
🎤 stt_listening_start       | +1.657s | Total: 23.720s | 
🔷 vad_speech_start          | +0.748s | Total: 24.468s | Energy: 11157
🔷 vad_speech_end            | +2.460s | Total: 26.928s | Duration: 2.0s
🎤 stt_audio_captured        | +0.001s | Total: 26.928s | Bytes: 89280
🎤 stt_final_transcript      | +0.831s | Total: 27.760s | Text: എന്താ വെറുതെയിരിക്കുന്ന വല്ല പണിക്കു പോടാ
🧠 llm_request_start         | +0.001s | Total: 27.760s | 
🧠 llm_first_token           | +1.972s | Total: 29.732s | 
🔈 tts_generation_start      | +0.529s | Total: 30.261s | Generating: അത് പിന്നെ എൻ്റെ പണി...
🔈 tts_audio_ready           | +0.876s | Total: 31.137s | 
🔈 tts_request_queued        | +0.000s | Total: 31.137s | 
🔈 tts_playback_start        | +0.000s | Total: 31.138s | Playing: അത് പിന്നെ...
🔈 tts_generation_start      | +0.002s | Total: 31.140s | Generating:  ഞാൻ AI അല്ലേ....
🔈 tts_audio_ready           | +0.761s | Total: 31.901s | 
🔈 tts_request_queued        | +0.000s | Total: 31.901s | 
🔈 tts_playback_start        | +1.054s | Total: 32.955s | Playing:  ഞാൻ AI അല...
🎤 stt_listening_start       | +1.556s | Total: 34.511s | 
🔷 vad_speech_start          | +1.240s | Total: 35.751s | Energy: 10660
🔷 vad_speech_end            | +3.074s | Total: 38.825s | Duration: 2.5s
🎤 stt_audio_captured        | +0.001s | Total: 38.826s | Bytes: 108480
🎤 stt_final_transcript      | +0.938s | Total: 39.764s | Text: നീ ഒരു മണ്ടനാണ് കഴുതയെ
🧠 llm_request_start         | +0.001s | Total: 39.766s | 
🧠 llm_first_token           | +1.253s | Total: 41.019s | 
🔈 tts_generation_start      | +0.246s | Total: 41.266s | Generating: അയ്യോ ഞാൻ ഒന്നും ചെയ...
🔈 tts_audio_ready           | +0.827s | Total: 42.093s | 
🔈 tts_request_queued        | +0.000s | Total: 42.093s | 
🔈 tts_playback_start        | +0.000s | Total: 42.093s | Playing: അയ്യോ ഞാൻ ...
🔈 tts_generation_start      | +0.002s | Total: 42.095s | Generating:  വെറുതെ ചീത്ത പറയുന്...
🔈 tts_audio_ready           | +0.740s | Total: 42.835s | 
🔈 tts_request_queued        | +0.000s | Total: 42.835s | 
🔈 tts_playback_start        | +0.977s | Total: 43.812s | Playing:  വെറുതെ ചീ...
🎤 stt_listening_start       | +1.506s | Total: 45.318s | 
🔷 vad_speech_start          | +1.289s | Total: 46.607s | Energy: 11985
🔷 vad_speech_end            | +3.309s | Total: 49.915s | Duration: 2.8s
🎤 stt_audio_captured        | +0.002s | Total: 49.917s | Bytes: 116160
🎤 stt_final_transcript      | +1.060s | Total: 50.977s | Text: ഞാൻ ചീത്ത പറയുന്നത് ഞാനാണ് മുതലാളിയാണ് പന്നി
🧠 llm_request_start         | +0.001s | Total: 50.978s | 
🧠 llm_first_token           | +1.912s | Total: 52.890s | 
🔈 tts_generation_start      | +0.588s | Total: 53.479s | Generating: നിങ്ങൾ മുതലാളി ആയിക്...
🔈 tts_audio_ready           | +1.382s | Total: 54.861s | 
🔈 tts_request_queued        | +0.000s | Total: 54.861s | 
🔈 tts_playback_start        | +0.000s | Total: 54.862s | Playing: നിങ്ങൾ മുത...
============================================================

📈 KEY METRICS:
  • STT Processing           : 1.060s
  • LLM Time-to-First-Token  : 1.912s
  • TTS Generation           : -0.000s
  • Total Voice-to-Voice     : 4.944s
------------------------------------------------------------

============================================================
🎯 ROBOT LISTENING MODE - AI ACTIVE 🧠
============================================================
💬 Messages received: 5
✅ Successful: 5 | ❌ Failed: 0
🧠 AI Responses: 5 | ❌ AI Failures: 0
⏱️  Uptime: 58s
------------------------------------------------------------
2026-01-10 00:19:46,355 - src.services.speech.speech_recognizer - WARNING - ⚠️ Streaming not available, falling back to batch mode
2026-01-10 00:19:46,355 - src.services.speech.speech_recognizer - INFO - 🎯 Ready to listen...
2026-01-10 00:19:46,355 - src.services.speech.audio_capture - INFO - 🎯 Starting async audio stream (Low Latency Mode)...
🎯 Listening... (Silence cutoff: 0.5s)
Adjusting to noise... Done. (Noise: 10063 → Threshold: 13183)
^C2026-01-10 00:19:53,559 - src.core.robot_controller - INFO - ⏸️ Shutdown signal received...
2026-01-10 00:19:53,559 - src.core.robot_controller - INFO - 🛑 Robot stopping...
⏱️ Timeout
2026-01-10 00:20:16,398 - src.services.speech.audio_capture - INFO - 🎯 Listening via PipeWire...
🎯 Listening... (Speak naturally)
Adjusting to background noise... Done. (Noise: 2227 -> Threshold: 2972)
^C2026-01-10 00:20:24,017 - src.core.robot_controller - INFO - ⏸️ Shutdown signal received...
2026-01-10 00:20:24,017 - src.core.robot_controller - INFO - 🛑 Robot stopping...
⚠️ No speech detected. Try again!

============================================================
📊 SESSION STATISTICS
============================================================
💬 Total messages: 5
✅ Successful transcriptions: 5
❌ Failed transcriptions: 1
🧠 AI Responses: 5
❌ AI Failures: 0
📊 Total tokens used: 0
💰 Estimated cost: $0.0000
⏱️  Session duration: 96s (1.6 minutes)
📈 Average time per message: 19.3s
🎯 Success rate: 83.3%
============================================================

2026-01-10 00:20:24,320 - src.core.robot_controller - INFO - ✅ Step 3 complete!
2026-01-10 00:20:24,320 - src.services.tts.tts_service - INFO - 🛑 TTS Worker cancelled
2026-01-10 00:20:24,321 - src.core.robot_controller - INFO - 🧹 Cleaning up robot resources...
2026-01-10 00:20:24,321 - PiperTTSProvider - INFO - 🧽 Cleaning up Piper TTS provider...
2026-01-10 00:20:24,321 - src.services.speech.speech_recognizer - INFO - 🧽 Cleaning up speech recognizer...
2026-01-10 00:20:24,321 - src.services.llm.openrouter_provider - INFO - 🧹 Cleaning up OpenRouter provider...
2026-01-10 00:20:24,346 - src.core.robot_controller - INFO - ✅ Cleanup complete
(venv) learnlogicai@raspberrypi:~/Desktop/robotlatest/NILA-V2 $ 