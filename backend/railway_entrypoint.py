"""Railway entrypoint that keeps the app reachable on both PORT and 8000.

Railway's public domain can remain pinned to an older target port even after
the container starts listening on the injected PORT (usually 8080). To keep
the service reachable while the domain config catches up, we run Uvicorn on the
injected PORT and expose a tiny TCP forwarder on 8000 when needed.
"""

import asyncio
import contextlib
import os
import signal
import sys

DEFAULT_PUBLIC_PORT = 8000
BUFFER_SIZE = 64 * 1024


async def _pipe_stream(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        while True:
            chunk = await reader.read(BUFFER_SIZE)
            if not chunk:
                break
            writer.write(chunk)
            await writer.drain()
    except (asyncio.CancelledError, ConnectionError, OSError):
        raise
    finally:
        with contextlib.suppress(Exception):
            writer.close()
            await writer.wait_closed()


async def _forward_connection(
    client_reader: asyncio.StreamReader,
    client_writer: asyncio.StreamWriter,
    upstream_port: int,
) -> None:
    try:
        upstream_reader, upstream_writer = await asyncio.open_connection(
            "127.0.0.1", upstream_port
        )
    except OSError:
        with contextlib.suppress(Exception):
            client_writer.close()
            await client_writer.wait_closed()
        return

    tasks = [
        asyncio.create_task(_pipe_stream(client_reader, upstream_writer)),
        asyncio.create_task(_pipe_stream(upstream_reader, client_writer)),
    ]
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    for task in pending:
        task.cancel()
    for task in done:
        with contextlib.suppress(asyncio.CancelledError, ConnectionError, OSError):
            await task


async def _start_compat_proxy(public_port: int, upstream_port: int):
    async def _handler(
        client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter
    ) -> None:
        await _forward_connection(client_reader, client_writer, upstream_port)

    return await asyncio.start_server(_handler, host="0.0.0.0", port=public_port)


async def main() -> int:
    target_port = int(os.environ.get("PORT", str(DEFAULT_PUBLIC_PORT)))
    public_port = int(
        os.environ.get("RAILWAY_PUBLIC_COMPAT_PORT", str(DEFAULT_PUBLIC_PORT))
    )
    workers = os.environ.get("UVICORN_WORKERS", "4")

    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "uvicorn",
        "backend.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        str(target_port),
        "--workers",
        workers,
    )

    server = None
    if public_port != target_port:
        server = await _start_compat_proxy(public_port, target_port)

    loop = asyncio.get_running_loop()

    def _shutdown() -> None:
        with contextlib.suppress(ProcessLookupError):
            proc.send_signal(signal.SIGTERM)

    for sig_name in ("SIGINT", "SIGTERM"):
        sig = getattr(signal, sig_name, None)
        if sig is not None:
            with contextlib.suppress(NotImplementedError):
                loop.add_signal_handler(sig, _shutdown)

    return_code = await proc.wait()

    if server is not None:
        server.close()
        await server.wait_closed()

    return return_code


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
