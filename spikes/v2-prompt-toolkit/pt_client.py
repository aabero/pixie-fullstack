"""Candidate: prompt_toolkit PromptSession + patch_stdout. Throwaway spike code."""
import asyncio, os, sys, time
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout

LOG = os.environ["V2_LOG"]

def stamp(name):
    with open(LOG, "a") as f:
        f.write(f"{name} {time.time():.4f}\n")

async def stream():
    for i in range(40):
        print(f"stream token {i}")
        await asyncio.sleep(0.25)

async def update():
    await asyncio.sleep(3)
    stamp("UPDATE")
    print("UPDATE task-1 running")

async def main():
    session = PromptSession()
    with patch_stdout():
        bg = [asyncio.create_task(stream()), asyncio.create_task(update())]
        while True:
            try:
                line = await session.prompt_async("you> ")
            except (EOFError, KeyboardInterrupt):
                break
            if line.strip() == "/status":
                print("STATUS ok")
            elif line.strip() == "/approve":
                print("APPROVED ok")
            elif line.strip() == "/quit":
                break
        for t in bg:
            t.cancel()

asyncio.run(main())
