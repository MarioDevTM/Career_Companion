"""Async network cancellation with a synchronous iterator for Streamlit.

No Streamlit APIs are used in the worker. Closing the consumer cancels the
request, including a blocked network read. Redirects are deliberately disabled.
"""
import asyncio
import json
import queue
import threading
import time
import httpx


class EndpointHTTPError(Exception):
    def __init__(self, status):
        self.status = status
        super().__init__(f"Ollama returned HTTP {status}")


def response_lines(url, payload, headers, *, connect, first, idle, total, transport=None):
    events = queue.Queue(maxsize=128)
    stop = threading.Event()
    control = {}

    async def send(value):
        while not stop.is_set():
            try:
                events.put_nowait(value)
                return
            except queue.Full:
                await asyncio.sleep(0.01)
        raise asyncio.CancelledError

    async def run():
        control["loop"] = asyncio.get_running_loop()
        control["task"] = asyncio.current_task()
        try:
            async with asyncio.timeout(total):
                deadline = time.monotonic() + first
                seen_content = False
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(connect, read=None), headers=headers,
                    follow_redirects=False, transport=transport,
                ) as client:
                    context = client.stream("POST", url, json={**payload, "stream": True})
                    response = await asyncio.wait_for(context.__aenter__(), max(0.01, deadline - time.monotonic()))
                    try:
                        if response.status_code >= 300:
                            raise EndpointHTTPError(response.status_code)
                        lines = response.aiter_lines().__aiter__()
                        while not stop.is_set():
                            remaining = deadline - time.monotonic()
                            if remaining <= 0:
                                raise TimeoutError("Ollama first-response or idle deadline exceeded")
                            try:
                                line = await asyncio.wait_for(anext(lines), remaining)
                            except StopAsyncIteration:
                                break
                            if not line:
                                continue
                            if len(line) > 1_000_000:
                                raise ValueError("Ollama event too large")
                            event = json.loads(line)
                            if not isinstance(event, dict):
                                raise ValueError("Invalid Ollama event")
                            chunk = event.get("message", {}).get("content") or event.get("response")
                            if chunk:
                                seen_content = True
                                deadline = time.monotonic() + idle
                            # Heartbeats/thinking must not indefinitely postpone first text.
                            await send(line)
                            if event.get("done") or event.get("error"):
                                break
                    finally:
                        await context.__aexit__(None, None, None)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            await send(exc)
        finally:
            if not stop.is_set():
                await send(None)

    worker = threading.Thread(target=lambda: asyncio.run(run()), daemon=True)
    worker.start()
    deadline = time.monotonic() + total + 2
    try:
        while True:
            try:
                item = events.get(timeout=max(0.01, deadline - time.monotonic()))
            except queue.Empty:
                raise TimeoutError("Ollama total request budget exceeded") from None
            if item is None:
                return
            if isinstance(item, Exception):
                raise item
            yield item
    finally:
        stop.set()
        loop, task = control.get("loop"), control.get("task")
        if loop and task and not loop.is_closed():
            try:
                loop.call_soon_threadsafe(task.cancel)
            except RuntimeError:
                pass
        worker.join(timeout=1)
