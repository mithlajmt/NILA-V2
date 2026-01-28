# 🎤 TTS Voice Options Guide

## 📊 Current gTTS Settings

**Current Configuration:**
- **TLD**: `co.in` (Indian English accent)
- **Slow**: `False` (normal speed)
- **Language**: `en` (English)

**Location**: `src/config/settings.py` lines 48-51

---

## ⚠️ Important Clarification

### ❌ Gemini is NOT a TTS Service!

**Gemini** is an **LLM (Language Model)** - it generates text responses, NOT voices!
- Gemini = AI brain (what Nila says)
- TTS = Voice (how Nila sounds)

You're already using **OpenAI GPT** as your LLM (AI brain), not Gemini.

---

## 🎵 TTS Service Comparison

### 1. **gTTS (Free, Current)**

**What you have now:**
- ✅ **FREE** - No API keys needed
- ✅ **Simple** - Easy to use
- ❌ **Limited** - No real "voices", only accents
- ❌ **One voice per accent** - Can't choose different voices

**Available Options:**
- **Accents** (via TLD):
  - `co.in` - Indian English (current)
  - `com` - American English
  - `co.uk` - British English
  - `com.au` - Australian English
- **Speed**: `slow=True/False`
- **Language**: `en`, `en-in`, `en-us`, `en-uk`, `en-au`

**Limitations:**
- ❌ No voice selection (male/female)
- ❌ No pitch control
- ❌ No speaking rate control
- ❌ Only one voice per accent
- ❌ Robotic sound quality

---

### 2. **Edge TTS (Free, High Quality)**

**Microsoft Edge TTS - Free Neural Voices:**
- ✅ **FREE** - No API keys or quotas needed
- ✅ **High Quality** - Microsoft's neural voices
- ✅ **Malayalam Support** - Native Malayalam voices
- ✅ **Multiple Voices** - Male and female options
- ✅ **Fast** - Low latency for responsive interactions
- ❌ **Unofficial API** - Uses Microsoft Edge's internal API

**Available Voices:**
- **Malayalam (India)**:
  - `ml-IN-SobhanaNeural` - Female (default)
  - `ml-IN-MidhunNeural` - Male
- **English (US)**:
  - `en-US-AriaNeural` - Female (default)
  - `en-US-GuyNeural` - Male

**Configuration:**
```env
TTS_PROVIDER=edge
EDGE_TTS_VOICE_GENDER=female  # or 'male'
```

**Features:**
- ✅ Automatic language detection (Malayalam vs English)
- ✅ Audio caching for performance
- ✅ Natural-sounding voices
- ✅ No cost or API limits

---

### 3. **Google Cloud TTS (Premium)**

**What you can upgrade to:**
- ✅ **Professional voices** - Multiple voices per language
- ✅ **Voice selection** - Male/female, different personalities
- ✅ **Full control** - Pitch, speed, volume
- ✅ **Malayalam support** - Native Malayalam voices
- ✅ **High quality** - Natural-sounding voices
- ❌ **Requires API key** - Needs Google Cloud account
- ❌ **Costs money** - Pay per character (but very cheap)

**Available Voices:**
- **English (India)**:
  - `en-IN-Wavenet-A` - Female
  - `en-IN-Wavenet-B` - Male
  - `en-IN-Wavenet-C` - Female
  - `en-IN-Wavenet-D` - Male (current default)
- **Malayalam (India)**:
  - `ml-IN-Wavenet-A` - Female (current default)
  - `ml-IN-Wavenet-B` - Male
  - `ml-IN-Wavenet-C` - Female
  - `ml-IN-Wavenet-D` - Male

**Controls:**
- Speaking rate: 0.25 to 4.0 (1.0 = normal)
- Pitch: -20.0 to 20.0 (0.0 = normal)
- Volume: -96.0 to 16.0 dB (0.0 = normal)

---

## 🔄 How to Switch TTS Providers

### Option 1: Stay with gTTS (Free, Current)

**Current settings in `.env`:**
```env
TTS_PROVIDER=gtts
GTTS_TLD=co.in        # Indian accent
GTTS_SLOW=False       # Normal speed
GTTS_LANG=en          # English
```

**Change accent:**
```env
# American accent
GTTS_TLD=com
GTTS_LANG=en-us

# British accent
GTTS_TLD=co.uk
GTTS_LANG=en-uk

# Australian accent
GTTS_TLD=com.au
GTTS_LANG=en-au
```

**⚠️ Note**: gTTS doesn't have "different voices" - only different accents. All voices sound the same for each accent.

---

### Option 2: Upgrade to Google Cloud TTS (Premium)

**Requirements:**
1. Google Cloud account
2. Service account JSON file
3. TTS API enabled
4. API key

**Setup:**
```env
# Switch to Google Cloud TTS
TTS_PROVIDER=google_cloud

# Set service account credentials
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Choose voices
TTS_VOICE_ENGLISH=en-IN-Wavenet-A    # Female English
TTS_VOICE_MALAYALAM=ml-IN-Wavenet-A  # Female Malayalam

# Control voice
TTS_SPEAKING_RATE=1.0    # Speed (0.25-4.0)
TTS_PITCH=0.0            # Pitch (-20 to 20)
TTS_VOLUME_GAIN_DB=0.0   # Volume (-96 to 16 dB)
```

**Available English Voices (India):**
- `en-IN-Wavenet-A` - Female voice
- `en-IN-Wavenet-B` - Male voice
- `en-IN-Wavenet-C` - Female voice (alternative)
- `en-IN-Wavenet-D` - Male voice (alternative)

**Available Malayalam Voices:**
- `ml-IN-Wavenet-A` - Female voice
- `ml-IN-Wavenet-B` - Male voice
- `ml-IN-Wavenet-C` - Female voice (alternative)
- `ml-IN-Wavenet-D` - Male voice (alternative)

---

## 🎯 Recommendation

### For Free (gTTS):
- **Current**: Indian accent (`co.in`)
- **Options**: Change TLD for different accents
- **Limitation**: Only one voice per accent, no voice selection

### For Better Quality (Google Cloud TTS):
- **Cost**: ~$4 per 1 million characters (very cheap)
- **Quality**: Professional, natural voices
- **Features**: Multiple voices, pitch/speed control, Malayalam support
- **Setup**: Requires Google Cloud account and API key

---

## ❓ FAQ

**Q: Can I use Gemini voices with gTTS?**  
A: No. Gemini is an LLM (text generator), not a TTS service. It doesn't have voices.

**Q: Can I get different voices with gTTS?**  
A: No. gTTS only offers different accents, not different voices. All voices sound the same for each accent.

**Q: How do I get different voices?**  
A: Upgrade to Google Cloud TTS, which offers multiple voices (male/female) per language.

**Q: Is Google Cloud TTS expensive?**  
A: No, it's very cheap. ~$4 per 1 million characters. For a robot, it's practically free.

**Q: Can I use both gTTS and Google Cloud TTS?**  
A: Yes! You can switch between them in `.env` by changing `TTS_PROVIDER=gtts` or `TTS_PROVIDER=google_cloud`.

---

## 📝 Summary

| Feature | gTTS (Free) | Edge TTS (Free) | Google Cloud TTS (Premium) |
|---------|-------------|-----------------|---------------------------|
| **Cost** | Free | Free | ~$4 per 1M characters |
| **Voices** | 1 per accent | 2 per language | Multiple per language |
| **Voice Selection** | ❌ No | ✅ Yes (male/female) | ✅ Yes (male/female) |
| **Pitch Control** | ❌ No | ❌ No | ✅ Yes |
| **Speed Control** | ❌ Limited | ❌ No | ✅ Yes |
| **Malayalam** | ❌ No | ✅ Yes | ✅ Yes |
| **Quality** | Basic | High (Neural) | Professional |
| **Setup** | Easy | Easy | Requires API key |

---

**Current Setup**: You're using **gTTS** with Indian accent (`co.in`).  
**Recommended**: Switch to **Edge TTS** for free high-quality voices with Malayalam support.  
**Premium Option**: Use **Google Cloud TTS** for full voice control and customization.
