#!/usr/bin/env python3

"""Simple examples for using StreamValve"""

from dm_streamvalve.streamvalve import StreamValve

# Example 1: streaming complete Iterable

print("Ex 1 --------------------------------------------")
demotext = [
    "Hello\nWorld\n",
    "\nNice day for fishin', eh?",
    "\n",
    "\n\n",
    "\nFind that reference :-)\n",
]

s = StreamValve(demotext)
print(s.process()["text"])


# Example 2:
# - chunking the return into text with maximum of 2 paragraphs
# - restarting stream processing after it returned

print("Ex 2 --------------------------------------------")

s = StreamValve(demotext, max_paragraphs=2)
print(s.process()["text"])

print("Ex 3 --------------------------------------------")

# Example 3:
# - stopping at a repeated line. Here, max_linerepeats=3 means: on the 4th
#   apparition of a line already seen before, processing stops.
# - a string is also an iterable

s = StreamValve(
    """Here are african animals:

- Zebra
- Lion
- Zebra
- Elephant
- Zebra
- Gnu
- Zebra
- Antelope
""",
    max_linerepeats=3,
)

print(s.process()["text"])
print("*** Above are the first animals, from Zebra to Gnu, as the 4th Zebra triggered a stop.")
print("*** You can continue the processing.")
print(s.process()["text"])


print("Ex 4 --------------------------------------------")

# Example 4:
# - monitoring the Ollama stream live on stdout via callback
# - reconstructing text from streams of arbitrary type, e.g., Ollama ChatResponse

import ollama


def monitor(s: str):
    """Callback for streamvalve to monitor chat response"""
    print(s, end="", flush=True)


def extract_chat_response(cr: ollama.ChatResponse) -> str:
    return cr["message"]["content"]


ostream = ollama.chat(
    model="llama3.1",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Name 50 animals in a dashed list. One per line."},
    ],
    stream=True,
)

sv = StreamValve(
    ostream,
    callback_extract=extract_chat_response,
    callback_token=monitor,
    max_linerepeats=3,
    max_lines=200,
)

sv.process()
