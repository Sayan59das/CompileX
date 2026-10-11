"""Claude API transport.

The one place that knows how to talk to Anthropic: client construction, the
missing-key message, request defaults, and turning SDK errors into something a
user can act on. Both generation stages go through `complete()`:

    lesson_plan.py   -> the lesson design   (JSON, schema-enforced)
    scene_writer.py  -> the Manim scene     (Python source)

Streaming is not stylistic here. The scene-writing stage asks for tens of
thousands of output tokens, and the SDK refuses non-streaming requests it
estimates will outlive the HTTP timeout.
"""

import json
import os
import sys

import anthropic

MODEL = "claude-opus-5"

# Server-side fallback: Claude Opus 5 runs safety classifiers that can decline a
# request outright. Benign topics (hash collisions, buffer traversal, "attack"
# framing in an algorithms lesson) occasionally trip them, so a declined request
# is re-run on Anthropic's recommended fallback model instead of killing the run.
_FALLBACK_BETA = "server-side-fallback-2026-07-01"

_KEY_HELP = """
error: ANTHROPIC_API_KEY is not set.

Execution stopped because this project generates both its lesson content and
its Manim scene code by calling the Claude API, and the API cannot be reached
without a key. Nothing was generated and no files were written.

Set the key, then run the command again.

  Command Prompt (cmd.exe):
      set ANTHROPIC_API_KEY=your_api_key_here

  PowerShell:
      $env:ANTHROPIC_API_KEY = "your_api_key_here"

To persist it across future sessions on Windows:
      setx ANTHROPIC_API_KEY "your_api_key_here"

Get a key at https://console.anthropic.com/settings/keys
"""


class ClaudeUnavailable(RuntimeError):
    """Raised with an actionable message instead of a raw SDK traceback."""


def require_key():
    """Exit with instructions if the key is unset.

    Called up front by the CLI so a missing key is reported before any work is
    announced, rather than surfacing halfway through a progress line.
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit(_KEY_HELP)


def client():
    """Construct the API client, or exit with instructions if the key is unset."""
    require_key()
    return anthropic.Anthropic(
        api_key=os.environ.get("ANTHROPIC_API_KEY")
    )


def _dots(enabled):
    """Tiny progress ticker so a three-minute generation does not look hung."""
    state = {"n": 0}

    def tick(chunk):
        if not enabled:
            return
        state["n"] += len(chunk)
        while state["n"] >= 500:
            state["n"] -= 500
            print(".", end="", flush=True)

    return tick


def _stream(cli, tick, **kw):
    """Stream a request, preferring the beta endpoint with refusal fallbacks.

    Older SDK builds do not know the `fallbacks` parameter. Rather than pin a
    version, fall through to the plain endpoint when the argument is rejected.
    """
    try:
        with cli.beta.messages.stream(
            betas=[_FALLBACK_BETA], fallbacks="default", **kw
        ) as stream:
            for chunk in stream.text_stream:
                tick(chunk)
            return stream.get_final_message()
    except TypeError:
        pass
    except anthropic.BadRequestError as exc:
        detail = str(exc).lower()
        if "fallback" not in detail and "beta" not in detail:
            raise

    with cli.messages.stream(**kw) as stream:
        for chunk in stream.text_stream:
            tick(chunk)
        return stream.get_final_message()


def complete(prompt, system, *, effort="high", schema=None, max_tokens=16000,
             model=MODEL, cache_system=True, progress=True):
    """One request. Returns a parsed dict when `schema` is given, else text.

    `cache_system` marks the system prompt as cacheable. Both stages send a
    large, byte-identical system prompt on every topic, so this turns the
    second and later renders within the cache window into cache reads.
    """
    cli = client()

    system_blocks = [{"type": "text", "text": system}]
    if cache_system:
        system_blocks[0]["cache_control"] = {"type": "ephemeral"}

    output_config = {"effort": effort}
    if schema is not None:
        output_config["format"] = {"type": "json_schema", "schema": schema}

    kwargs = dict(
        model=model,
        max_tokens=max_tokens,
        system=system_blocks,
        thinking={"type": "adaptive"},
        output_config=output_config,
        messages=[{"role": "user", "content": prompt}],
    )

    try:
        message = _stream(cli, _dots(progress), **kwargs)
    except anthropic.AuthenticationError as exc:
        raise ClaudeUnavailable(
            "ANTHROPIC_API_KEY was rejected. Check the key is current and was "
            "copied whole.\n"
            "  PowerShell:  $env:ANTHROPIC_API_KEY = \"your_api_key_here\""
        ) from exc
    except anthropic.NotFoundError as exc:
        raise ClaudeUnavailable(
            f"No model named '{model}'. Pass a valid one with --model "
            f"(default: {MODEL})."
        ) from exc
    except anthropic.RateLimitError as exc:
        raise ClaudeUnavailable(
            "Rate limited by the Claude API. Wait a moment and re-run; the "
            "saved plan is reused with --reuse-plan so nothing is lost."
        ) from exc
    except anthropic.APIConnectionError as exc:
        raise ClaudeUnavailable(
            f"Could not reach the Claude API ({exc}). Check your connection."
        ) from exc
    except anthropic.APIStatusError as exc:
        # Billing is a 400, not a 402, and reads like a malformed request unless
        # it is called out. Nothing about the payload is wrong.
        if "credit balance is too low" in str(exc).lower():
            raise ClaudeUnavailable(
                "This API account has no credits left, so no request can be "
                "made.\nAdd credits at "
                "https://console.anthropic.com/settings/billing and re-run.\n"
                "Saved plans and scenes still render offline with "
                "--reuse-plan --reuse-scene."
            ) from exc
        raise ClaudeUnavailable(
            f"Claude API error {exc.status_code}: {exc.message}"
        ) from exc
    finally:
        if progress:
            print()

    # Check the stop reason before touching content: a refusal has no text
    # blocks at all, so indexing straight into content would IndexError.
    if message.stop_reason == "refusal":
        category = getattr(getattr(message, "stop_details", None), "category", None)
        raise ClaudeUnavailable(
            "Claude declined this request"
            + (f" (category: {category})" if category else "")
            + ".\nTry rewording the topic; algorithm topics that read as "
              "security-adjacent occasionally trip the safety classifiers."
        )

    text = "".join(b.text for b in message.content if b.type == "text")
    if not text.strip():
        usage = getattr(message, "usage", None)
        out = getattr(usage, "output_tokens", "?")
        hint = ""
        if message.stop_reason == "max_tokens":
            hint = (f"\nThe {max_tokens} token budget was consumed before any "
                    f"output was written — adaptive thinking used all of it. "
                    f"Raise max_tokens, or lower --effort.")
        raise ClaudeUnavailable(
            f"Claude returned no text (stop_reason={message.stop_reason}, "
            f"output_tokens={out}).{hint}")

    if schema is None:
        return text

    # output_config.format guarantees schema-valid JSON, so a parse failure here
    # means truncation (max_tokens), not a malformed model reply.
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        if message.stop_reason == "max_tokens":
            raise ClaudeUnavailable(
                "Response was cut off by max_tokens before the JSON closed. "
                "Re-run, or reduce --sections."
            ) from exc
        raise ClaudeUnavailable(f"Could not parse the JSON response: {exc}") from exc
