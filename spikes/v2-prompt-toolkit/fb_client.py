"""Fallback: plain input() in a worker thread; output printed from the event loop."""
import asyncio, os, sys, time

LOG = os.environ["V2_LOG"]

def stamp(name):
    with open(LOG, "a") as f:
        f.write(f"{name} {time.time():.4f}\n")

async def stream():
    for i in range(40):
        print(f"stream token {i}", flush=True)
        await asyncio.sleep(0.25)

async def update():
    await asyncio.sleep(3)
    stamp("UPDATE")
    print("UPDATE task-1 running", flush=True)

async def main():
    loop = asyncio.get_running_loop()
    bg = [asyncio.create_task(stream()), asyncio.create_task(update())]
    while True:
        try:
            line = await loop.run_in_executor(None, input, "you> ")
        except EOFError:
            break
        if line.strip() == "/status":
            print("STATUS ok", flush=True)
        elif line.strip() == "/approve":
            print("APPROVED ok", flush=True)
        elif line.strip() == "/quit":
            break
    for t in bg:
        t.cancel()

asyncio.run(main())
