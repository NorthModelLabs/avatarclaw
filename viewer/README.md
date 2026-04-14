# Local viewer (planned)

**Goal:** a small **default UI** you run on your machine (e.g. `http://127.0.0.1:…`) that:

1. Reads **`livekit_url`**, **`token`**, and **`room`** from `POST /v1/realtime/session` (same JSON as today).
2. Lets **you join with mic** and talk to the avatar — no Google Meet tab.

**How to get there:** host a static or Next.js page that uses **[@northmodellabs/atlas-react](https://www.npmjs.com/package/@northmodellabs/atlas-react)** (or your own LiveKit client) and mints or receives the session payload from a tiny local API you control.

This folder is reserved for that app. Until it lands, use **`python3 skills/atlas-avatar/scripts/atlas_session.py start …`** and any HTTPS viewer you already deploy.

## Passthrough mode — persistent audio track

If your viewer uses **passthrough** mode (you bring your own LLM + TTS), use the **persistent audio track pattern** for freeze-free lip-sync. **Do not** call `session.publishAudio()` directly — it tears down the track after each call, causing the avatar to freeze between messages.

```typescript
import { useEffect, useRef } from "react";
import { useAtlasSession } from "@northmodellabs/atlas-react";
import { LocalAudioTrack, Track } from "livekit-client";

const session = useAtlasSession({
  autoEnableMic: false,
  createSession: async (face) => {
    const form = new FormData();
    if (face) form.append("face", face);
    form.append("mode", "passthrough");
    const res = await fetch("/api/session", { method: "POST", body: form });
    return res.json();
  },
});

// Refs for the persistent audio pipeline
const audioCtxRef = useRef<AudioContext | null>(null);
const destRef = useRef<MediaStreamAudioDestinationNode | null>(null);
const ttsSourceRef = useRef<AudioBufferSourceNode | null>(null);

// Publish ONE persistent audio track when connected
useEffect(() => {
  if (session.status !== "connected" || !session.room) return;

  const audioCtx = new AudioContext();
  const dest = audioCtx.createMediaStreamDestination();
  const lkTrack = new LocalAudioTrack(dest.stream.getAudioTracks()[0]);

  audioCtxRef.current = audioCtx;
  destRef.current = dest;

  session.room.localParticipant.publishTrack(lkTrack, {
    name: "tts-audio",
    source: Track.Source.Unknown,
  });

  return () => {
    ttsSourceRef.current?.stop();
    session.room?.localParticipant.unpublishTrack(lkTrack);
    lkTrack.stop();
    audioCtx.close();
  };
}, [session.status, session.room]);

// Play TTS audio through the persistent track
function playTtsAudio(base64Audio: string) {
  const audioCtx = audioCtxRef.current;
  const dest = destRef.current;
  if (!audioCtx || !dest) return;

  ttsSourceRef.current?.stop(); // cancel previous if still playing

  const binary = atob(base64Audio);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);

  audioCtx.decodeAudioData(bytes.buffer.slice(0)).then((buf) => {
    const source = audioCtx.createBufferSource();
    source.buffer = buf;
    source.connect(dest);
    ttsSourceRef.current = source;
    source.onended = () => { source.disconnect(); ttsSourceRef.current = null; };
    source.start();
  });
}
```

**How it works:**
- One track, never torn down — silence when idle, TTS audio when speaking
- Idle → GPU renders idle animation (avatar stays alive)
- TTS plays → `BufferSource` connects to same destination → avatar lip-syncs
- TTS ends → `BufferSource` disconnects → back to idle

Full example app: **[atlas-realtime-example](https://github.com/NorthModelLabs/atlas-realtime-example)** | API docs: **[northmodellabs.com/api](https://www.northmodellabs.com/api)**
