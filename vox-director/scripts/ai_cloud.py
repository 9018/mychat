#!/usr/bin/env python3
"""
OpenAI-compatible gateway client for vox-director.

Talks to the self-hosted newapi-style aggregator (OpenAI-compatible surface):

    POST {base}/chat/completions    chat  +  MiMo TTS (audio in message audio)
    POST {base}/images/generations  text-to-image (sync; returns asset URL)
    POST {base}/videos              text/image-to-video (async task)
    GET  {base}/videos/{id}         poll task status

Env (all explicit, nothing guessed):
    OPENAI_API_KEY    required  (sk-...)  — gateway key (newapi / 10.0.1.108:18901)
    OPENAI_BASE_URL   default http://10.0.1.108:18901/v1
    UPSTREAM_PROXY    optional but REQUIRED in this network: the 10.0.1.108 hosts
                      are only reachable through a SOCKS5 hop, e.g.
                      socks5h://192.168.99.3:1080  (also used for grok assets)
    GROK2API_BASE     grok-imagine-* assets live on the Grok2API media service
                      (e.g. http://10.0.1.108:8000 — explicit, no default)
    GROK2API_KEY      Client Key from the Grok2API console (explicit, no default)

Hard-won gotchas baked in (validated 2026-08-08 against the gateway):
  1. Image model outputs differ: agnes-image-2.1-flash returns a PUBLIC https URL
     (downloadable); grok-imagine-* returns a localhost URL
     (http://127.0.0.1:8000/v1/media/images/<id>) that only the Grok2API host can
     serve — submit_image() fetches it through GROK2API_BASE+KEY and returns a
     base64 data URI (usable everywhere: keyframes, video image param, frontend).
  2. Video (agnes-video-v2.0): `image` accepts a PUBLIC http(s) URL or base64 image
     data (localhost/private URLs are rejected upstream); `duration` is accepted
     (num_frames must be 8*n+1 if you pass it instead). Task id: task_id or id.
  3. Polling GET /v1/videos/{id} -> {status: queued|processing|completed|failed,
     progress, video_url, metadata.url}.
  4. TTS runs through chat/completions with an `audio` field — synchronous, returns
     base64 audio in choices[0].message.audio.data. Voice names for MiMo are
     Chinese for zh voices (e.g. '冰糖'), or 'mimo_default'.
  5. Every request MUST send a real User-Agent header.
"""
import base64
import json
import mimetypes
import os
import subprocess
import time
import urllib.error
import urllib.request

DEFAULT_BASE = "http://10.0.1.108:18901/v1"
UA = "vox-director/0.1 (+openai-gateway)"


class GatewayError(RuntimeError):
    pass


def _key() -> str:
    k = os.environ.get("OPENAI_API_KEY")
    if not k:
        raise GatewayError(
            "OPENAI_API_KEY is not set. Export it (or set in .env): "
            "export OPENAI_API_KEY=sk-...")
    return k


def base_url() -> str:
    return (os.environ.get("OPENAI_BASE_URL") or DEFAULT_BASE).rstrip("/")


def _headers(json_body: bool = True) -> dict:
    h = {"Authorization": f"Bearer {_key()}", "User-Agent": UA}
    if json_body:
        h["Content-Type"] = "application/json"
    return h


def _http_request(method: str, url: str, headers: dict, body: bytes = None,
                 timeout: int = 120) -> tuple:
    """Single HTTP round-trip -> (status, payload bytes).
    If UPSTREAM_PROXY is set (explicitly, e.g. socks5h://192.168.99.3:1080) all
    traffic (gateway + grok media) goes through it via curl; otherwise plain
    urllib keeps the script dependency-free."""
    proxy = (os.environ.get("UPSTREAM_PROXY") or "").strip()
    if not proxy:
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()
        except (urllib.error.URLError, TimeoutError) as e:
            raise GatewayError(f"{method} {url} -> {e}") from e
    args = ["/usr/bin/curl", "-sS", "--max-time", str(timeout), "-X", method,
            "--proxy", proxy, "--write-out", "|__STATUS__|%{http_code}"]
    for k, v in headers.items():
        args += ["-H", f"{k}: {v}"]
    if body is not None:
        args += ["--data-binary", "@-"]
    args.append(url)
    try:
        r = subprocess.run(args, input=body, capture_output=True, timeout=timeout + 20)
    except subprocess.TimeoutExpired:
        raise GatewayError(f"{method} {url} timed out (>{timeout}s)") from None
    if r.returncode != 0:
        raise GatewayError(f"{method} {url} -> curl rc={r.returncode}: "
                           f"{r.stderr.decode(errors='replace')[:200]}")
    marker = b"|__STATUS__|"
    i = r.stdout.rfind(marker)
    code = int(r.stdout[i + len(marker):i + len(marker) + 3] or 0)
    return code, r.stdout[:i]


def _post(path: str, payload: dict, timeout: int = 240) -> dict:
    code, body = _http_request("POST", base_url() + path, _headers(),
                               json.dumps(payload).encode(), timeout)
    text = body.decode(errors="replace")
    if code >= 400:
        try:
            msg = (json.loads(text).get("error", {}) or {}).get("message") or text[:300]
        except ValueError:
            msg = text[:300]
        raise GatewayError(f"POST {path} -> {code}: {msg}")
    try:
        return json.loads(text)
    except ValueError:
        raise GatewayError(f"POST {path} -> non-JSON body: {text[:300]}")


def _get(path: str, timeout: int = 60, retries: int = 3) -> dict:
    last = None
    for i in range(retries):
        try:
            code, body = _http_request("GET", base_url() + path,
                                       _headers(json_body=False), None, timeout)
            if code >= 400:
                try:
                    return json.loads(body)      # 上游已返回 JSON 错误体,直接透出
                except ValueError:
                    raise GatewayError(
                        f"GET {path} -> {code}: {body.decode(errors='replace')[:300]}")
            return json.loads(body)
        except GatewayError as e:
            if "curl rc" not in str(e) and "timed out" not in str(e) and code < 500:
                raise                     # 4xx: 不重试
            last = e
            time.sleep(2 ** i)
        except (urllib.error.URLError, TimeoutError) as e:
            last = e
            time.sleep(2 ** i)
    raise GatewayError(f"GET {path} failed after {retries} tries: {last}")


def _public_url(url: str) -> str:
    """Reject gateway-localhost asset URLs (unreachable from anywhere else)."""
    if not url:
        return None
    for bad in ("127.0.0.1", "localhost", "0.0.0.0", "10.", "192.168.", "172.16."):
        if bad in url:
            return None
    return url


def _grok2_url(url: str) -> str:
    """Fetch a Grok2API-localhost asset (http://127.0.0.1:8000/v1/media/...) back as a
    data URI so the pipeline can use it anywhere (video image param, downloads,
    frontend). REQUIRES EXPLICIT CONFIG — no address or key is guessed:
      GROK2API_BASE  the Grok2API console origin, e.g. http://<host>:<port>
      GROK2API_KEY   a Client Key from the Grok2API console
    Missing either -> clear error telling the user to configure them explicitly.
    """
    base = (os.environ.get("GROK2API_BASE") or "").rstrip("/")
    key = os.environ.get("GROK2API_KEY", "")
    missing = [v for v, ok in (("GROK2API_BASE", base), ("GROK2API_KEY", key)) if not ok]
    if missing:
        raise GatewayError(
            f"asset {url[:60]}... is served by the local Grok2API media service and is "
            f"not reachable as-is. Configure it explicitly: export GROK2API_BASE="
            f"http://<grok2api-host>:<port> GROK2API_KEY=<client-key> (missing: "
            f"{', '.join(missing)}) — or use agnes-image-2.1-flash (public urls) "
            f"for keyframes.")
    # keep the path (/v1/media/images/<id>) intact; swap only the origin
    origin_end = url.index("//") + 2
    path = url[url.index("/", origin_end):]
    u = base + path
    code, blob = _http_request("GET", u,
                             {"User-Agent": UA, "Authorization": f"Bearer {key}"},
                             None, 120)
    if code != 200:
        raise GatewayError(f"GROK2API media fetch failed ({code}) for {u[:80]}... "
                           f"check GROK2API_BASE / GROK2API_KEY")
    if not blob:
        raise GatewayError(f"GROK2API returned empty body for {u[:60]}...")
    return "data:image/jpeg;base64," + base64.b64encode(blob).decode()


def _grok2_request(method: str, path: str, body: bytes = None, timeout: int = 300) -> bytes:
    """Authenticated call into the Grok2API service (10.0.1.108:8000). Requires
    explicit GROK2API_BASE + GROK2API_KEY (Client Key from the console)."""
    base = (os.environ.get("GROK2API_BASE") or "").rstrip("/")
    key = os.environ.get("GROK2API_KEY", "")
    missing = [v for v, ok in (("GROK2API_BASE", base), ("GROK2API_KEY", key)) if not ok]
    if missing:
        raise GatewayError(
            f"Grok2API needs explicit config (missing: {', '.join(missing)}). "
            f"export GROK2API_BASE=http://<host>:<port> GROK2API_KEY=<client-key>")
    headers = {"User-Agent": UA, "Authorization": f"Bearer {key}"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    code, blob = _http_request(method, base + path, headers, body, timeout)
    for attempt in range(4):                  # 瞬态 5xx/429 重试(出口节点波动常见)
        if code < 400:
            return blob
        if code in (408, 429) or code >= 500:
            time.sleep(5 * (attempt + 1))
            code, blob = _http_request(method, base + path, headers, body, timeout)
            continue
        break
    raise GatewayError(
        f"GROK2API {method} {path} -> {code}: {blob.decode(errors='replace')[:200]}")


IS_GROK2_VIDEO = ("grok-",)   # models served directly by Grok2API, not the gateway


def grok2_submit_video(model: str, prompt: str, **params) -> str:
    """POST /v1/videos/generations (Grok2API v3.1.1 protocol) -> request_id.
    Fields: model, prompt, duration, aspect_ratio, resolution, image (or
    reference_images). `image` may be a public URL or base64 data URI; the API
    wants it as an object {"url": ...} (videoGenerationImage) — string inputs
    are wrapped automatically. Validated live: base64 data URI works."""
    p = dict(params)
    if isinstance(p.get("image"), str):
        p["image"] = {"url": p["image"]}
    if isinstance(p.get("reference_images"), list):
        p["reference_images"] = [{"url": i} if isinstance(i, str) else i
                                 for i in p["reference_images"]]
    body = {"model": model, "prompt": prompt, **p}
    blob = _grok2_request("POST", "/v1/videos/generations",
                          json.dumps(body).encode(), timeout=120)
    d = json.loads(blob.decode())
    rid = d.get("request_id") or d.get("id")
    if not rid:
        raise GatewayError(f"GROK2API submit_video({model}) no request_id: {blob[:200]!r}")
    return rid


def grok2_get_status(task_id: str) -> dict:
    """GET /v1/videos/{request_id} -> normalized status. Completed output is the
    content URL rewritten onto GROK2API_BASE (fetched with the key by download())."""
    raw = _grok2_request("GET", f"/v1/videos/{task_id}", timeout=60)
    d = json.loads(raw.decode())
    st = (d.get("status") or "").lower()
    if st == "done":
        video_url = (d.get("video") or {}).get("url", "")
        if not video_url:
            raise GatewayError(f"GROK2API video {task_id} done but no video.url: {raw[:200]!r}")
        # /v1/videos/<id>/content served at 127.0.0.1:8000 -> rewrite to GROK2API_BASE
        origin_end = video_url.index("//") + 2
        path = video_url[video_url.index("/", origin_end):]
        out = (os.environ.get("GROK2API_BASE") or "").rstrip("/") + path
        return {"status": "completed", "output": out, "error": None}
    if st == "failed":
        err = d.get("reason") or d.get("error") or str(d)[:200]
        return {"status": "failed", "output": None, "error": str(err)[:300]}
    return {"status": "pending", "output": None, "error": None}


# ---------------------------------------------------------------- image

def submit_image(model: str, prompt: str, **params) -> str:
    """Sync text-to-image; returns a usable asset. grok-imagine-image(-quality)
    go DIRECTLY to Grok2API /v1/images/generations (same as video — keeps the
    default grok chain off the gateway relay, which can 502 under load);
    everything else uses the gateway (agnes-* -> public URL, gpt-image-2 ->
    b64_json)."""
    body = {"model": model, "prompt": prompt, "n": 1, **params}
    if model.startswith("grok-imagine-image"):
        blob = _grok2_request("POST", "/v1/images/generations",
                              json.dumps(body).encode(), timeout=300)
        d = json.loads(blob.decode())
        item = (d.get("data") or [{}])[0]
        url = item.get("url") or (item.get("b64_json") and "data:image/png;base64," + item["b64_json"])
        if not url:
            raise GatewayError(f"submit_image({model}) no asset from Grok2API: {str(d)[:200]}")
        return _grok2_url(url) if not url.startswith("data:") else url
    d = _post("/images/generations", body, timeout=300)
    item = (d.get("data") or [{}])[0]
    url = _public_url(item.get("url"))
    if not url and item.get("b64_json"):
        url = "data:image/png;base64," + item["b64_json"]
    if not url:
        raise GatewayError(f"submit_image({model}) returned no usable asset")
    return url


# ---------------------------------------------------------------- video

def submit_video(model: str, prompt: str, **params) -> str:
    """Async text/image-to-video; returns job id.
    - gateway models (agnes-*): POST /videos -> task_id
    - grok-imagine-video: routed DIRECTLY to Grok2API /v1/videos/generations
      (requires explicit GROK2API_BASE + GROK2API_KEY) -> request_id"""
    if any(m in model for m in IS_GROK2_VIDEO):
        return grok2_submit_video(model, prompt, **params)
    body = {"model": model, "prompt": prompt, **params}
    d = _post("/videos", body, timeout=180)
    tid = d.get("task_id") or d.get("id")
    if not tid:
        raise GatewayError(f"submit_video({model}) returned no task id: {str(d)[:200]}")
    return tid


def get_status(task_id: str) -> dict:
    """Normalize to {status: pending|completed|failed, output, error}."""
    if str(task_id).startswith("video_"):        # Grok2API request_id
        return grok2_get_status(task_id)
    d = _get(f"/videos/{task_id}")
    st = (d.get("status") or "").lower()
    if st in ("completed", "succeeded"):
        out = _public_url(d.get("video_url")) or \
            _public_url((d.get("metadata") or {}).get("url"))
        return {"status": "completed", "output": out, "error": None}
    if st == "failed":
        err = d.get("error") or d.get("message") or str(d)[:200]
        if isinstance(err, dict):
            err = err.get("message") or str(err)
        return {"status": "failed", "output": None, "error": str(err)[:300]}
    return {"status": "pending", "output": None, "error": None}


def poll(task_id: str, interval: int = 4, timeout_s: int = 1200) -> str:
    """Poll a video task until done; return output URL (or raise)."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        time.sleep(interval)
        r = get_status(task_id)
        if r["status"] == "completed":
            return r["output"]
        if r["status"] == "failed":
            raise GatewayError(f"{task_id} failed: {r['error']}")
    raise GatewayError(f"{task_id} timed out after {timeout_s}s")


# ---------------------------------------------------------------- audio / TTS

def tts(model: str, text: str, *, voice: str = None, voice_desc: str = None,
        clone_sample_b64: str = None, audio_format: str = "mp3", **extra) -> bytes:
    """MiMo TTS through chat/completions. Returns raw audio bytes.
    - voice:      named voice (Chinese names for zh, e.g. '冰糖')
    - voice_desc: voicedesign mode — the design brief goes in the user message
    - clone_sample_b64: voiceclone mode — data-URI audio sample
    """
    messages = []
    if voice_desc:
        messages.append({"role": "user", "content": voice_desc})
    messages.append({"role": "assistant", "content": text})
    audio = {"format": audio_format}
    if clone_sample_b64:
        audio["voice"] = clone_sample_b64
    elif voice:
        audio["voice"] = voice
    body = {"model": model, "messages": messages, "audio": audio, **extra}
    d = _post("/chat/completions", body, timeout=240)
    data = ((d.get("choices") or [{}])[0].get("message", {}) or {}).get("audio", {}).get("data")
    if not data:
        raise GatewayError(f"TTS {model} returned no audio data: {str(d)[:200]}")
    return base64.b64decode(data)


# ---------------------------------------------------------------- chat / ASR

def chat(model: str, messages: list, **params) -> str:
    """OpenAI-compatible chat completion -> assistant text."""
    body = {"model": model, "messages": messages, **params}
    d = _post("/chat/completions", body, timeout=240)
    msg = (d.get("choices") or [{}])[0].get("message", {}) or {}
    return msg.get("content") or msg.get("reasoning") or ""


def transcribe(audio_url: str, **params):
    """ASR — NOT available on this gateway (no STT model provisioned)."""
    raise GatewayError(
        "transcribe(): this gateway has no STT model — A-roll (talking-head) mode "
        "is unavailable. Use B-roll (topic) mode, or add an STT model to the gateway "
        "and wire it here.")


# ---------------------------------------------------------------- upload / dl

def upload(file_path: str) -> str:
    """No upload endpoint on the gateway; the video API accepts base64 image data
    directly, so return a data URI (works wherever a media URL is expected)."""
    with open(file_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    mime = mimetypes.guess_type(file_path)[0] or "image/png"
    return f"data:{mime};base64,{b64}"


def download(url: str, dest: str) -> str:
    """Download an asset (public https) via urllib with a real UA; fall back to
    curl if urllib hits a TLS/host quirk."""
    if url.startswith("data:"):
        _, b64 = url.split(",", 1)
        with open(dest, "wb") as f:
            f.write(base64.b64decode(b64))
        return dest
    probe = url[:8].lower()
    if probe in ("data:im", "data:au", "data:vi"):   # already a data URI of any type
        with open(dest, "wb") as f:
            f.write(base64.b64decode(url.split(",", 1)[1]))
        return dest
    headers = {"User-Agent": UA}
    gbase = (os.environ.get("GROK2API_BASE") or "").rstrip("/")
    if gbase:
        try:
            if url.split("//", 1)[1].split("/", 1)[0] == gbase.split("//", 1)[1].split("/", 1)[0]:
                headers["Authorization"] = f"Bearer {os.environ.get('GROK2API_KEY', '')}"
        except Exception:
            pass
    code, blob = _http_request("GET", url, headers, None, 600)
    if code != 200 or not blob:
        raise GatewayError(f"download failed ({code}): {url[:80]}...")
    with open(dest, "wb") as f:
        f.write(blob)
    return dest


if __name__ == "__main__":
    import sys
    print("key:", "set" if os.environ.get("OPENAI_API_KEY") else "MISSING")
    print("base:", base_url())
    if "--ping" in sys.argv:
        print("chat:", chat("deepseek-v4-flash-free",
                            [{"role": "user", "content": "reply with exactly: OK"}]))
        print("image:", submit_image("grok-imagine-image",
                                     "a tiny red seal stamp on white paper",
                                     aspect_ratio="1:1"))
        print("tts bytes:", len(tts("mimo-v2.5-tts", "你好", voice="冰糖")))
