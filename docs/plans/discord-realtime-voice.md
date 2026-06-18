# Discord Realtime Voice Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task after Jonatan explicitly approves implementation. Do not start code changes from this plan without that approval.

**Goal:** Add a second Discord voice mode to `jarvis-discord`: `/voice join` remains the existing turn-based mode, while `/voice realtime` joins the caller's voice channel and starts a low-latency streaming conversation.

**Architecture:** Keep the current turn-based Discord voice pipeline intact. Add a separate realtime session module that bridges Discord PCM frames to OpenAI Realtime and streams returned audio into the existing Discord `VoiceMixer`. Expose only a small, safe tool surface in realtime: reminders, web search summaries, and image generation to the linked text channel; barge-in/interruption is intentionally deferred to a later phase.

**Tech Stack:** Python, discord.py voice, PyNaCl/Opus, asyncio, websockets, OpenAI Realtime API, Hermes gateway, existing Discord `VoiceReceiver` and `VoiceMixer`, pytest.

---

## Current decision

Final command surface:

```text
/voice join       # existing turn-based STT -> Hermes -> TTS mode; unchanged
/voice realtime   # joins user's voice channel and activates realtime streaming
/voice status     # reports normal/realtime/off state
/voice leave      # disconnects and cleans both normal and realtime voice state
```

Explicitly **not** implementing:

```text
/voice join realtime
```

Reason: redundant with `/voice realtime`; fewer command variants means fewer state bugs.

## Scope boundaries

### In scope for the first implementation

- `/voice realtime` command.
- Join the requesting user's current Discord voice channel.
- Start one realtime voice session per guild.
- Link realtime session to the text channel where the command was invoked.
- Stream inbound Discord voice audio to the realtime provider.
- Stream model audio deltas back into Discord voice through the existing mixer.
- Optional text trace in the linked text channel.
- Hard session limits for cost/safety.
- Restricted tools:
  - create reminders,
  - web information lookup/summarization,
  - image generation and delivery to the linked text channel.
- Clean shutdown through `/voice leave` and timeouts.

### Explicitly out of scope for the first implementation

- Barge-in / natural interruption while Jarvis is speaking.
- Full Hermes tool access.
- Terminal/filesystem/system-control tools.
- Multi-guild/multi-channel concurrency beyond one realtime session per guild.
- Complex multiuser diarization.
- Replacing `/voice join` or changing current turn-based behavior.

### Deferred phase

- **Barge-in**: detect user speech while output audio is playing, cancel the current realtime response, clear outbound audio buffers, and continue listening. This remains pending after the first implementation.

## Configuration design

Target profile config:

```text
/home/jony/.hermes/profiles/jarvis-discord/config.yaml
```

Proposed config subtree:

```yaml
discord:
  voice:
    realtime:
      enabled: true
      provider: openai
      model: "gpt-realtime"
      max_session_seconds: 600
      idle_timeout_seconds: 60
      require_authorized_users: true
      text_trace: true
      tools:
        reminders: true
        web_search: true
        image_generation: true
        terminal: false
        files: false
        system_control: false
      barge_in:
        enabled: false
        status: deferred
```

Environment:

```text
OPENAI_API_KEY=<set in jarvis-discord profile>
```

Current environment verification from 2026-06-13:

- `OPENAI_API_KEY`: set in `jarvis-discord` profile.
- `websockets`: installed.
- `numpy`: installed.
- `ffmpeg`: installed.
- `PyNaCl`: installed.
- `discord.py`: installed.
- `webrtcvad`: not installed; only needed if/when implementing barge-in with local VAD.
- `soundfile`: not installed; avoid requiring it in MVP.

## Safety model

Realtime mode is a conversational fast path, not full Jarvis admin mode.

Permitted realtime tools:

1. `create_reminder`
   - Creates a reminder/cron job scoped to the linked Discord origin.
   - Requires parseable time and non-empty reminder text.
   - Returns a short confirmation.

2. `web_search_summary`
   - Performs a short web lookup and returns a concise spoken summary.
   - Must have timeout and length limits.

3. `generate_image_to_discord`
   - Generates an image and sends it to the linked text channel.
   - Spoken output should acknowledge generation and delivery.

Forbidden in realtime MVP:

- shell commands,
- file reads/writes,
- config/profile edits,
- gateway restarts,
- backups/restores,
- credential handling,
- smart-home actions,
- arbitrary Hermes tool dispatch.

If the user asks for an out-of-scope operation, realtime should answer:

```text
Eso requiere modo operativo completo, señor. Pídamelo por texto a Jarvis para ejecutarlo con seguridad.
```

## Runtime state model

Add explicit realtime state independent from the existing turn-based voice mode:

```python
_realtime_voice_sessions: Dict[int, DiscordRealtimeVoiceSession]  # guild_id -> session
_realtime_voice_text_channels: Dict[int, int]                     # guild_id -> channel_id
_realtime_voice_sources: Dict[int, Dict[str, Any]]                # guild_id -> source metadata
```

State transition summary:

```text
off
  ├── /voice join      -> turn_based
  └── /voice realtime  -> realtime

turn_based
  ├── /voice realtime  -> stop/replace turn-based receive loop as needed, start realtime
  └── /voice leave     -> off

realtime
  ├── /voice join      -> stop realtime, start turn-based
  ├── /voice leave     -> off
  └── timeout/error    -> off with notice in linked text channel
```

## Audio architecture

### Current turn-based path

```text
Discord voice packets
  -> VoiceReceiver
  -> completed utterance PCM
  -> WAV conversion
  -> STT
  -> Hermes agent
  -> TTS audio file
  -> Discord VoiceMixer/playback
```

### New realtime path

```text
Discord voice packets
  -> VoiceReceiver frame/chunk callback
  -> DiscordRealtimeVoiceSession
  -> OpenAI Realtime input audio buffer
  -> OpenAI Realtime output audio deltas
  -> StreamingPCMSource queue
  -> VoiceMixer
  -> Discord voice channel
```

Key design rule: keep `VoiceReceiver` and `VoiceMixer` reusable. Do not fork the whole Discord adapter unless absolutely necessary.

## Files to modify/create

### Modify

- `gateway/run.py`
  - Parse and dispatch `/voice realtime`.
  - Add `_handle_voice_realtime_join()`.
  - Update `/voice status` output.
  - Ensure `/voice leave` stops realtime sessions.

- `plugins/platforms/discord/adapter.py`
  - Add adapter methods for realtime session lifecycle.
  - Add optional streaming PCM frame callback from `VoiceReceiver`.
  - Ensure turn-based and realtime receivers do not both process the same audio.
  - Expose helper to install/get a streaming source in the mixer.

- `plugins/platforms/discord/voice_mixer.py`
  - Add or support a streaming queue-based PCM child/source.
  - Preserve existing mixer behavior and tests.

- `hermes_cli/config.py` or relevant config defaults, if Hermes requires explicit default config registration for the new subtree.

- Discord docs/help strings, if slash command choices are enumerated.

### Create

- `plugins/platforms/discord/realtime_voice.py`
  - `DiscordRealtimeVoiceSession`
  - provider-neutral session skeleton with OpenAI implementation initially.

- `plugins/platforms/discord/realtime_tools.py`
  - safe tool bridge for reminders/search/images.
  - no terminal/filesystem/system tools.

- `tests/gateway/test_discord_voice_realtime.py`
  - command parsing,
  - lifecycle,
  - status,
  - leave cleanup,
  - tool allowlist,
  - no regression to `/voice join`.

- Optional later: `tests/gateway/test_discord_realtime_audio.py`
  - lower-level streaming source/mixer tests.

## Implementation tasks

### Task 1: Add realtime command recognition tests

**Objective:** Lock the final command surface before implementation.

**Files:**
- Create: `tests/gateway/test_discord_voice_realtime.py`
- Modify: none initially.

**Tests:**

- `/voice realtime` dispatches to realtime handler.
- `/voice join` still dispatches to existing turn-based handler.
- `/voice join realtime` is not a supported command and should return help/unsupported-mode text.
- `/voice leave` invokes realtime cleanup when a realtime session exists.
- `/voice status` can display `realtime` state.

**Run:**

```bash
python -m pytest tests/gateway/test_discord_voice_realtime.py -q -o 'addopts='
```

Expected before implementation: failing tests for missing realtime behavior.

### Task 2: Add config loader/defaults for realtime voice

**Objective:** Make the feature explicitly configurable and off unless enabled in config.

**Files:**
- Modify: config defaults if needed.
- Test: `tests/gateway/test_discord_voice_realtime.py`

**Acceptance:**

- Default behavior does not break existing Discord voice.
- Realtime can be enabled through `discord.voice.realtime.enabled: true`.
- Missing config falls back safely: disabled or safe defaults depending on existing config style.

### Task 3: Implement `/voice realtime` gateway handler skeleton

**Objective:** Add command handling and state transition without real streaming yet.

**Files:**
- Modify: `gateway/run.py`
- Test: `tests/gateway/test_discord_voice_realtime.py`

**Behavior:**

- Validate Discord server context.
- Find user's current voice channel using existing adapter helper.
- Reject if user is not in a voice channel.
- Reject if realtime disabled.
- Call adapter realtime-start method.
- Persist linked text source/channel.
- Return Spanish/Jarvis-facing confirmation.

### Task 4: Add `DiscordRealtimeVoiceSession` skeleton

**Objective:** Introduce lifecycle abstraction independent from the Discord adapter.

**Files:**
- Create: `plugins/platforms/discord/realtime_voice.py`
- Test: `tests/gateway/test_discord_voice_realtime.py`

**Class API:**

```python
class DiscordRealtimeVoiceSession:
    async def start(self) -> None: ...
    async def stop(self, reason: str = "") -> None: ...
    async def send_audio_frame(self, pcm: bytes, *, user_id: int | None = None) -> None: ...
    async def interrupt(self) -> None: ...  # placeholder for deferred barge-in
    @property
    def active(self) -> bool: ...
```

**Acceptance:**

- Can start/stop with fake provider in tests.
- Stop is idempotent.
- No network required in unit tests.

### Task 5: Add streaming audio source for VoiceMixer

**Objective:** Let realtime output feed Discord incrementally instead of as complete files.

**Files:**
- Modify: `plugins/platforms/discord/voice_mixer.py`
- Test: existing mixer tests plus new streaming tests.

**Design:**

- Queue-based PCM source.
- Discord-native frame geometry: 48 kHz, stereo, signed 16-bit LE, 20 ms frames.
- Silence when queue is briefly empty.
- Bounded queue to prevent unbounded memory growth.
- Clear/drain method for future barge-in.

**Run:**

```bash
python -m pytest tests/gateway/test_discord_voice_mixer.py -q -o 'addopts='
```

### Task 6: Add VoiceReceiver realtime frame callback

**Objective:** Provide small PCM chunks to realtime without breaking completed-utterance STT mode.

**Files:**
- Modify: `plugins/platforms/discord/adapter.py`
- Test: `tests/gateway/test_discord_voice_realtime.py`

**Design:**

- Add optional callback, e.g. `_realtime_pcm_callback`.
- Only one processing path active per guild: turn-based OR realtime.
- Ignore bot SSRC as current receiver already does.
- Respect allowed users.

**Acceptance:**

- `/voice join` still uses completed utterance path.
- `/voice realtime` uses frame/chunk path.
- Authorized-user filtering remains enforced.

### Task 7: Implement OpenAI Realtime provider connection

**Objective:** Connect session skeleton to real OpenAI Realtime over WebSocket.

**Files:**
- Modify: `plugins/platforms/discord/realtime_voice.py`
- Test: unit tests use fake WebSocket; live test manual only.

**Events:**

- open session with configured model,
- send session instructions/persona,
- send input audio chunks,
- receive output audio deltas,
- push decoded PCM to streaming source,
- handle close/error/timeouts.

**Important:** Do not hardcode secrets. Read `OPENAI_API_KEY` through profile-aware config/env helpers.

### Task 8: Implement safe realtime tools bridge

**Objective:** Add limited function/tool support without exposing full Hermes toolset.

**Files:**
- Create: `plugins/platforms/discord/realtime_tools.py`
- Modify: `plugins/platforms/discord/realtime_voice.py`
- Test: `tests/gateway/test_discord_voice_realtime.py`

**Tools:**

- `create_reminder(text, when)`
- `web_search_summary(query)`
- `generate_image_to_discord(prompt)`

**Acceptance:**

- Tool allowlist is explicit.
- Any non-allowlisted tool request is rejected with a safe message.
- Tool outputs are short and voice-friendly.
- Image output goes to linked text channel, not voice.

### Task 9: Integrate `/voice status` and `/voice leave`

**Objective:** Make operational state visible and cleanup reliable.

**Files:**
- Modify: `gateway/run.py`
- Modify: `plugins/platforms/discord/adapter.py`
- Test: `tests/gateway/test_discord_voice_realtime.py`

**Acceptance:**

`/voice status` shows:

```text
Voice mode: realtime
Voice channel: <name/id>
Linked text channel: <id>
Realtime provider: openai
Tools: reminders, web_search, image_generation
Barge-in: pending/deferred
```

`/voice leave`:

- stops realtime session,
- drains output queue,
- stops voice receiver,
- disconnects from channel,
- clears state,
- disables auto TTS for linked chat.

### Task 10: Manual Discord verification

**Objective:** Prove the feature works in the real server.

**Commands:**

```bash
python -m py_compile gateway/run.py plugins/platforms/discord/adapter.py plugins/platforms/discord/voice_mixer.py plugins/platforms/discord/realtime_voice.py plugins/platforms/discord/realtime_tools.py
python -m pytest tests/gateway/test_discord_voice_realtime.py tests/gateway/test_discord_voice_mixer.py -q -o 'addopts='
hermes --profile jarvis-discord gateway restart
hermes --profile jarvis-discord gateway status
```

Discord manual test:

```text
/voice realtime
```

Speak:

```text
Jarvis, ¿me escuchas en realtime?
```

Expected:

- bot joins the user's voice channel,
- responds by voice with low latency,
- text trace appears if enabled,
- `/voice status` reports realtime,
- `/voice leave` disconnects cleanly.

### Task 11: Update project and operational docs

**Objective:** Preserve the runbook for future maintenance.

**Files:**
- Modify: `/home/jony/.hermes/jarvis/projects/Discord Realtime/PROJECT.md`
- Modify: `/home/jony/.hermes/skills/devops/jarvis-operations/references/discord-profile-operations.md` if implementation changes the Discord runbook.
- Modify: docs if user-facing commands change.

**Acceptance:**

- Project status reflects implemented/pending phases.
- Barge-in remains explicitly pending until implemented.
- `/proyects` dashboard is regenerated.

## Test strategy

Run narrow tests after each task:

```bash
python -m pytest tests/gateway/test_discord_voice_realtime.py -q -o 'addopts='
```

Run mixer regression when touching audio output:

```bash
python -m pytest tests/gateway/test_discord_voice_mixer.py -q -o 'addopts='
```

Run existing Discord voice tests before restart:

```bash
python -m pytest tests/gateway/test_discord_voice_mixer.py tests/gateway/test_discord_opus.py tests/gateway/test_discord_connect.py -q -o 'addopts='
```

Compile touched modules:

```bash
python -m py_compile gateway/run.py plugins/platforms/discord/adapter.py plugins/platforms/discord/voice_mixer.py plugins/platforms/discord/realtime_voice.py plugins/platforms/discord/realtime_tools.py
```

## Verification gates before saying done

- Unit tests pass.
- Existing `/voice join` still works.
- `/voice realtime` joins channel and starts session.
- `/voice leave` cleans realtime state.
- Text trace works or is explicitly disabled.
- Reminder tool can create one safe test reminder.
- Web search returns a short answer.
- Image generation sends media to linked channel.
- Barge-in is still marked pending, not implied complete.

## Open risks

- OpenAI Realtime exact event names/model slug may need adjustment against current API documentation during implementation.
- Discord inbound audio chunking may require tuning to avoid jitter.
- Echo/self-hearing must be validated in real Discord, not only unit tests.
- Cost must be monitored after first live tests.
- Barge-in needs separate VAD/cancel-buffer design and remains deferred.
