# dm-ollama

Python package to reconstruct text from an Iterable with optional termination criteria,

Nothing stellar, initially developped to work with the Ollama Python module to be able to stop the output after, e.g. two paragraphs. Or to stop the output when a model
got stuck in an endless loop, constantly repeating the same lines over and over again.

Termination criteria can be:
- Maximum number of lines encountered
- Maximum number of paragraphs encountered. Paragraphs being text blocks separated by one or several blank lines
- Maximum number of lines with exact copies encountered previously

# Installation
## Installation via PyPi
Not yet, TBD
## Installation from source
TBD

# Usage examples

## Full example 1: get complete stream
- Streaming complete Iterable

```python
from dm_streamvalve.streamvalve import StreamValve

demotext = [
    "Hello\nWorld\n",
    "\nNice day for fishin', eh?",
    "\n",
    "\n\n",
    "\nFind that reference :-)\n",
]

sv = StreamValve(demotext)
print(sv.process()["text"])
```

This will print:

```
Hello
World

Nice day for fishin', eh?



Find that reference :-)
```

## Example 2: Termination criteria
Here, termination criterium is set to have at max 2 paragraphs.

```python
sv = StreamValve(demotext, max_paragraphs=2)
print(sv.process()["text"])
```

This will print:

```
Hello
World

Nice day for fishin', eh?



```

Note the newlines at the end are part of the result as process() will stop only at the start of the next paragraph ("Find ...")

## Example 3: Restart reading stream after a termination
This example shows
- stopping at a repeated line. Here, max_linerepeats=3 means: on the 4th apparition of a line already seen before, processing stops.
- one can continue the processing after an early termination
- a string is also an iterable
```python
sv = StreamValve(
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
    max_linerepeats=3, # include max 3 copies if identical lines
)

print(sv.process()["text"])

print("*** Above are the first animals, from Zebra to Gnu, as the 4th Zebra triggered a stop.")
print("*** You can continue the processing.")

print(sv.process()["text"])
```

This will print:

```
Here are african animals:

- Zebra
- Lion
- Zebra
- Elephant
- Zebra
- Gnu

*** Above are the first animals, from Zebra to Gnu, as the 4th Zebra triggered a stop.
*** As previously, you can continue the processing.
- Zebra
- Antelope
```
## Full Example 4: reconstructing text from streams of arbitrary type, e.g., Ollama ChatResponse
This example shows how to:
- monitor the output of Ollama on stdout as it is generated via having `callback_token` point to a function (here: `monitor`)
- extract the text from every element of the Ollama ChatResponse stream to make it available to StreamValve via `callback_extract`. The Ollama ChatResponse `cr` is a dictionary of dictinaries, where the text of the current token is in `cr["message"]["content"]`
- setting multiple termination criteria as failsafe 

```python
import ollama
from dm_streamvalve.streamvalve import StreamValve

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
    max_linerepeats=3, # include max 3 copies if identical lines
    max_lines=200,     # max of 200 lines
)

sv.process()
```
This should result in an output on stdout similar to this one:
```
- Lion
- Elephant
- Gorilla
- Kangaroo
...
```

# Notes
The GitHub repository comes with all files I currently use for Python development across multiple platforms. Notably:

- configuration of the Python environment via `uv`: pyproject.toml and uv.lock
- configuration for linter and code formatter `ruff`: ruff.toml
- configuration for `pylint`: .pylintrc
- git ignore files: .gitignore
- configuration for `pre-commit`: .pre-commit-config.yaml. The script used to check `git commit` summary message is in devsupport/check_commitsummary.py
- configuration for VSCode editor: .vscode directory
