# dm-streamvalve

Python package to reconstruct text as a string from an Iterable with optional stopping criteria.

Nothing stellar, initially developed to work with the Ollama Python module to be able to stop the output after, e.g. two paragraphs. Or to stop the output when a model got stuck in an endless loop, constantly repeating some lines over and over again.

Stopping criteria can be:
- Maximum number of lines encountered
- Maximum number of paragraphs encountered. Paragraphs being text blocks separated by one or several blank lines
- Maximum number of lines with exact copies encountered previously

# Installation
If you haven't done so already, please install [uv](https://docs.astral.sh/uv/) as this Python package and project manager basically makes all headaches of Python package management go away in an instant.

With `uv`, adding *dm-streamvalve* to your project is as easy as
```shell
uv add dm-streamvalve
```

# Usage
You need to import StreamValve, instantiate an StreamValve object, and then call
`process()` to start processing the stream. Results, including information on the reason
for the processing having stopped, are returned in a dictionary

Processing can be restarted and will return either the next results of the stream or
the last result if the processing had been stopped because the stream was exhausted.

```python
from dm_streamvalve.streamvalve import StreamValve

sv = StreamValve(...)
result = sv.process()
print(result['text'])
print(result['stopmsg'])

result = sv.process()
...
```

## The StreamValve object
Allows to process an iterable of anything to reconstruct as string the text contained within.

Has optional callbacks to extract text from each element, as well as callbacks once a token or a
line has been accepted into the result.

Allows early stopping on repeated lines, maximum number of lines, maximum number of paragraphs, or a termination signal from the callback.

StreamValve(ostream, *callback_extract = None, callback_token = None, callback_line = None, max_linerepeats = 0, max_lines = 0, max_paragraphs = 0*)

Required args:

- **ostream : Iterable**  
Iterable of Any to reconstruct the text from.

Optional args:

- **callback_extract : Callable**  
If None, calls 'str()' on each element of the iterable to get next string of the stream
return type.  
If not None, calls the function to extract the string  
If return value is None instead of a str, leads to early termination.
Useful for, e.g., Ollama where each element in the ostream is of type
ollama.ChatResponse(), and the string of that is in ["message"]["content"] of each element
- **callback_token : Callable**  
Each time an element of the stream has been added to the result, i.e.,
 it did not lead to termination, this callback is called if not None.  
Can be used, e.g., to stream the processing as it happens.  
Unfortunately, the repeated line termination will have been streamed.
- **callback_line : Callable**  
Similar to callback token, but for each completed line. If the line
did not trigger max_linerepeats, this callback is called.  
Can be used, e.g., to stream only fully accepted lines.
- **max_linerepeats : int**  
Maximum number of line repeats allowed. Defaults to 0 (no limit).
- **max_lines : int**  
Maximum number of lines allowed. Defaults to 0 (no limit).
- **max_paragraphs : int**  
Maximum number of paragraphs allowed. Defaults to 0 (no limit).

## The process() function
Reads items from the Iterable of the StreamValve and returns a dict containing reconstructed text,
number of lines, number of paragraphs, and stop criterion and the string stopped at if an early
termination occurred.

Returns:
An object of type StreamData, which is of type dict[str, Any] The following fields will be defined and set:
- "text": str,
- "num_lines": int,
- "num_paragraphs": int,
- "stopcrit": StopReason,
- "stopmsg": str,
- "stopat": None | str,

If termination was initiated by callable() returning None, stopat may be None if the signal
by the callable was the only reason for stopping, else it contains the token/string
which led to termination.

# Usage examples

## Full example 1: get complete stream
This example shows streaming complete Iterable, in this case a list of strings.

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

## Example 2: Stopping criteria
Here, a stopping criterion is set to have at max 2 paragraphs.

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

> [!NOTE]
> The newlines at the end are part of the result as process() will stop only at the start of the next paragraph ("Find ...")

## Example 3: Restart reading stream after stopping
This example shows
- stopping at a repeated line. Here, `max_linerepeats=3` means: on the 4th apparition of a line already seen before, processing stops, the 4th repetition is not part of the result.
- one can continue the processing after an early stop.
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
> [!NOTE]
> Restarting processing resets the stopping criteria. E.g., in the example above but with a longer text, `process()` would read the stream again until it counted 3 more 'Zebra' and then encountered a 4th.

## Full Example 4: reconstructing text from streams of arbitrary type, e.g., Ollama ChatResponse
This example shows how to:
- monitor the output of Ollama on stdout as it is generated via having `callback_token` point to a function (here: `monitor`)
- extract the text from every element of the Ollama ChatResponse stream to make it available to StreamValve via `callback_extract`. 
- setting multiple stopping criteria as fail-safe 

> [!IMPORTANT]
> For the code below to work, you need to have (1) [Ollama](https://ollama.com) installed and running, the *llama3.1* model installed in Ollama (`ollama pull llama3.1`), and (3) your Python project needs to have the Ollama Python module installed via, e.g., `uv add ollama`.

```python
import ollama
from dm_streamvalve.streamvalve import StreamValve

def extract_chat_response(cr: ollama.ChatResponse) -> str:
    """Ollama ChatResponse `cr` is a dictionary of dictionaries, where the text of the
    current token is in cr["message"]["content"]"""
    return cr["message"]["content"]

def monitor(s: str):
    """Callback for streamvalve to monitor chat response"""
    print(s, end="", flush=True)

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
