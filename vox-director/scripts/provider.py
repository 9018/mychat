#!/usr/bin/env python3
"""
Provider abstraction — the pluggable media backend the pipeline stages talk to.

The OpenAI-compatible aggregator gateway is the only backend (default). Stages
call a Provider (submit_image/submit_video/tts/remove_bg/get_status/upload/
download) instead of a concrete client. Pick a backend per project with
beats.json `{"provider": "openai"}` (default).

TTS on this gateway is SYNCHRONOUS (chat/completions audio protocol), so stages
use `provider.tts(...)` directly instead of the submit+poll dance. Image and
video stages still use submit_* + run_jobs polling.
"""
import time
from abc import ABC, abstractmethod

import ai_cloud


class ProviderError(RuntimeError):
    pass


class Provider(ABC):
    """The surface the stages need. get_status normalizes every backend's polling
    response to {status: pending|completed|failed, output: <url|None>, error}."""
    name = "base"

    @abstractmethod
    def submit_image(self, model, prompt, **params): ...
    @abstractmethod
    def submit_video(self, model, prompt, **params): ...
    @abstractmethod
    def tts(self, model, text, **params): ...
    @abstractmethod
    def remove_bg(self, model, image_url, **params): ...
    @abstractmethod
    def get_status(self, job_id): ...
    @abstractmethod
    def upload(self, path): ...
    @abstractmethod
    def download(self, url, dest): ...


class OpenAIProvider(Provider):
    """Self-hosted OpenAI-compatible aggregator (newapi style)."""
    name = "openai"

    def submit_image(self, model, prompt, **params):
        return ai_cloud.submit_image(model, prompt, **params)

    def submit_video(self, model, prompt, **params):
        return ai_cloud.submit_video(model, prompt, **params)

    def tts(self, model, text, **params):
        """Synchronous TTS -> raw audio bytes. Accepts voice=, voice_desc=,
        clone_sample_b64=, audio_format= (see ai_cloud.tts)."""
        return ai_cloud.tts(model, text, **params)

    def remove_bg(self, model, image_url, **params):
        raise ProviderError(
            "remove_bg(): gateway has no background-removal model — the "
            "advanced cut-out/motion-collage path (extract_elements.py, C-roll "
            "anchors) is unavailable on this gateway.")

    def get_status(self, job_id):
        try:
            return ai_cloud.get_status(job_id)
        except ai_cloud.GatewayError as e:
            return {"status": "failed", "output": None, "error": str(e)}

    def upload(self, path):
        return ai_cloud.upload(path)

    def download(self, url, dest):
        return ai_cloud.download(url, dest)


_REGISTRY = {"openai": OpenAIProvider,
             "atlas_cloud": OpenAIProvider}   # legacy name -> same gateway


def get_provider(name=None):
    """Return a Provider instance by name (default 'openai')."""
    name = (name or "openai").lower()
    if name not in _REGISTRY:
        raise ProviderError(f"unknown provider '{name}'; available: {list(_REGISTRY)}")
    return _REGISTRY[name]()


def run_jobs(prov, specs, *, poll_s=5, stall_s=240, max_retries=2, deadline_s=1200):
    """Submit + poll a batch of jobs, resubmitting any that FAIL or STALL.

    specs: dict of key -> submit() callable returning a job id. A job that fails,
    or stays pending past `stall_s`, is resubmitted (fresh id) up to `max_retries`
    times — this is what stops one stuck prediction from wasting the whole deadline.
    Returns key -> output URL (or None).
    """
    st = {}
    for key, submit in specs.items():
        st[key] = {"pid": submit(), "t": time.time(), "tries": 0}
        print(f"[{key}] submitted {st[key]['pid']}")

    done = {}
    deadline = time.time() + deadline_s
    while len(done) < len(specs) and time.time() < deadline:
        time.sleep(poll_s)
        now = time.time()
        for key, submit in specs.items():
            if key in done:
                continue
            s = st[key]
            r = prov.get_status(s["pid"])
            status = r["status"]
            if status == "completed":
                done[key] = r["output"]
                print(f"[{key}] done")
            elif status == "failed" or (status == "pending" and now - s["t"] > stall_s):
                if s["tries"] < max_retries:
                    s["tries"] += 1
                    s["pid"] = submit()
                    s["t"] = time.time()
                    why = "failed" if status == "failed" else f"stalled>{int(stall_s)}s"
                    print(f"[{key}] {why} -> resubmit #{s['tries']} ({s['pid']})")
                elif status == "failed":
                    done[key] = None
                    print(f"[{key}] FAILED: {(r.get('error') or '')[:120]}")
                # stalled + out of retries: keep waiting until the deadline
    for key in specs:
        done.setdefault(key, None)
    return done