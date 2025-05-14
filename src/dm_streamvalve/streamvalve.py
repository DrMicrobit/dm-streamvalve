"""Module with helper functions to easily reconstruct a text from an output stream
and eventually terminate the streaming early on different criteria
"""

from collections import defaultdict

# Jan 2025. Weird pylint bug, see https://github.com/pylint-dev/pylint/issues/10112
from collections.abc import Callable, Iterable, Iterator  # pylint: disable = E0401
from enum import Enum, auto
from typing import Any

# Return type for process()
StreamData = dict[str, Any]


class StopCriterion(Enum):
    """Enums for getting the streamvalve stop reason"""

    MAX_LINEREPEATS = auto()
    MAX_PARAGRAPHS = auto()
    MAX_LINES = auto()
    MAX_LINETOKENS = auto()
    BY_CALLABLE = auto()
    END_OF_STREAM = auto()


STOP_MESSAGES: dict[StopCriterion, str] = {
    StopCriterion.MAX_LINEREPEATS: "Maximum number of exact repeated lines reached.",
    StopCriterion.MAX_PARAGRAPHS: "Maximum number of paragraphs reached.",
    StopCriterion.MAX_LINES: "Maximum number of lines reached.",
    StopCriterion.MAX_LINETOKENS: "Maximum number of tokens in a line reached.",
    StopCriterion.BY_CALLABLE: "Streamvalve stopped externally.",
    StopCriterion.END_OF_STREAM: "Stream ended.",
}


class StreamValve:
    """
    The StreamValve class.
    Process an iterable of anything to reconstruct the text contained within.

    Allows early termination on repeated lines, maximum number of lines, maximum number
     of paragraphs, or a termination signal from the callback.

    Required args:
        ostream (Iterable):
            Iterable of Any to reconstruct the text from.
    Optional args:
        callback_extract : Callable[[Any], str | None]
            If None, calls 'str()' on each element of the iterable to get next string
             of the stream return type.
            If not None, calls the function given to extract the string
            If return value is None instead of a str, leads to early termination.
            Useful for, e.g., ollama where each element in the ostream
             is of type ollama.ChatResponse(), and the string of that is in
             ["message"]["content"] of each element
        callback_token : Callable[[str], None]
            Each time an element of the stream has been added to the result, i.e.,
             it did not lead to termination, this callback is called if not None.
            Can be used, e.g., to stream the processing as it happens.
            Unfortunately, the repeated line termination will have been streamed.
        callback_line : Callable[[str], None]
            Similar to callback token, but for each completed line. If the line
            did not trigger max_linerepeats, this callback is called.
            Can be used, e.g., to stream only fully accepted lines.
        max_linerepeats : int
            Maximum number of line repeats allowed. Defaults to 0 (no limit).
        max_lines : int
            Maximum number of lines allowed. Defaults to 0 (no limit).
        max_paragraphs : int
            Maximum number of paragraphs allowed. Defaults to 0 (no limit).
    """

    # Really, pylint and ruff, this is not what you need to check here;
    # R0902: Too many instance attributes  (too-many-instance-attributes)
    # R0913: Too many arguments (too-many-arguments)
    # R0917: Too many positional arguments (too-many-positional-arguments)
    # too-many-arguments (PLR0913)

    # pylint: disable=R0902, R0913, R0917
    def __init__(
        self,
        ostream: Iterable[Any],
        callback_extract: Callable[[Any], str | None] | None = None,
        callback_token: Callable[[str], None] | None = None,
        callback_line: Callable[[str], None] | None = None,
        max_linerepeats: int = 0,
        max_lines: int = 0,
        max_paragraphs: int = 0,
        max_linetokens: int = 0,
    ):
        self._p_ostream = ostream
        self._p_callback_extract = callback_extract
        self._p_callback_token = callback_token
        self._p_callback_line = callback_line
        self._p_max_linerepeats = max_linerepeats
        self._p_max_lines = max_lines
        self._p_max_linetokens = max_linetokens
        self._p_max_paragraphs = max_paragraphs

        # Iterator for the stream
        self._iterator: Iterator[Any] = iter(ostream)

        # State variables for line reconstruction and paragraph counting
        self._current_line: list[str]  # Buffer for reconstructing current line.
        self._completed_lines: list[str]  # All previously reconstructed lines.
        self._line_repcounts: defaultdict[str, int]  # Track occurrence of each line.
        self._nextchar_is_next_para: bool  # If true, next non-blank line initiates new paragraph
        self._num_paragraphs: int  # Track paragraph count.
        self._num_tokens: int  # Track total token count
        self._num_linetokens: int  # Track line token count

        # To allow restarting process() after an early termination()
        self._laststopat: str | None  # string last read from the stream but not yet processed

        # Initialise all state variables
        self.reset()

    def reset(self):
        """Completely reset a StreamValve internal state"""
        self._laststopat = None

    def _reset(self):
        """Resets the StreamValve except laststopat"""
        self._num_paragraphs = 0
        self._num_tokens = 0
        self._num_linetokens = 0
        self._line_repcounts = defaultdict(int)
        self._completed_lines = []
        self._current_line = []
        self._nextchar_is_next_para = True

    def _process_txtchunk(self, strchunk: str, retval: StreamData):  # noqa: PLR0912  # pylint: disable=R0912
        """Helper function for processing text chunks. Reads / writes variables of class
        and the retval which is passed on from process().

        As own function because needs to run within loop and once at end of loop of process()
        """

        lenstripchunk = len(strchunk.strip())
        if (
            self._p_max_lines > 0
            and len(strchunk) > 0
            and len(self._completed_lines) >= self._p_max_lines
        ):  # pylint: disable=R1716
            retval["stopcrit"] = StopCriterion.MAX_LINES
            retval["stopat"] = strchunk
            return
        if lenstripchunk and self._nextchar_is_next_para:
            self._num_paragraphs += 1
            self._nextchar_is_next_para = False
            if self._p_max_paragraphs > 0 and self._num_paragraphs > self._p_max_paragraphs:  # pylint: disable=R1716
                retval["stopcrit"] = StopCriterion.MAX_PARAGRAPHS
                retval["stopat"] = strchunk
                self._num_paragraphs -= 1
                return
        if len(strchunk) > 0:
            self._current_line.append(strchunk)
            self._num_tokens += 1
            self._num_linetokens += 1
            if self._p_callback_token is not None:
                self._p_callback_token(strchunk)
            if self._p_max_linetokens > 0 and self._num_linetokens > self._p_max_linetokens:  # pylint: disable=R1716
                retval["stopcrit"] = StopCriterion.MAX_LINETOKENS
                retval["stopat"] = strchunk
                # No return here ... we need to add what was collected till now
            elif strchunk[-1] != "\n":
                return

        if len(self._current_line) == 0:
            return

        # store the curent line as fully completed line
        full_line = "".join(self._current_line)
        self._completed_lines.append(full_line)
        self._current_line.clear()
        self._num_linetokens = 0

        lenstripline = len(full_line.strip())
        if lenstripline == 0:
            self._nextchar_is_next_para = True

        # hunt for repeats when asked for
        if self._p_max_linerepeats > 0 and lenstripline > 0:
            self._line_repcounts[full_line] += 1
            if self._line_repcounts[full_line] > self._p_max_linerepeats:
                retval["stopcrit"] = StopCriterion.MAX_LINEREPEATS
                retval["stopat"] = self._completed_lines.pop()
                if len(self._completed_lines[-1].strip()) == 0:
                    self._num_paragraphs -= 1
                return

        if self._p_callback_line is not None:
            self._p_callback_line(full_line)

        return

    # Disabled some R1716 (chained comparisons) as those made the code harder to read
    #  and understand (and probably were a tiny bit slower)
    #
    def process(self) -> StreamData:
        """
        Returns:
            StreamData, which is of type dict[str, Any]
            The following fields will be defined and set:
            dict{
                "text": str,
                "num_tokens": int,
                "num_lines": int,
                "num_paragraphs": int,
                "stopcrit": StopReason,
                "stopmsg": str,
                "stopat": None | str,
            }
            A dict containing reconstructed text, number of lines, number of paragraphs,
            and stop criterion and the string stopped at if an early termination occured. If
            termination was initiated by callable() returning None, stopat may be None if the
            signal by the callable was the only reason for stopping, else it contains the
            token/string which led to termination.
        """

        retval: StreamData = {
            "text": None,
            "num_tokens": None,
            "num_lines": None,
            "num_paragraphs": None,
            "stopcrit": None,
            "stopmsg": None,
            "stopat": None,
        }
        self._reset()

        if self._laststopat is not None:
            self._process_txtchunk(self._laststopat, retval)

        splitted: list[str] = []

        if retval["stopcrit"] is None:
            sentinel = object()

            # Manually iterate through the iterator using a sentinel
            while (chunk := next(self._iterator, sentinel)) is not sentinel:
                # call callback if user provided one
                txt = (
                    str(chunk)
                    if self._p_callback_extract is None
                    else self._p_callback_extract(chunk)
                )
                # go through that text chunk line by line
                if txt is not None:
                    splitted = txt.splitlines(keepends=True)
                    while len(splitted):
                        self._process_txtchunk(splitted.pop(0), retval)
                        if retval["stopcrit"]:
                            break
                else:
                    retval["stopcrit"] = StopCriterion.BY_CALLABLE

                if retval["stopcrit"]:
                    break

        # process last chunk into line (in case it did not end with \n)
        if retval["stopcrit"] is None and len(self._current_line):
            self._process_txtchunk("", retval)

        if retval["stopcrit"] is None:
            self._laststopat = None
            retval["stopcrit"] = StopCriterion.END_OF_STREAM
        else:
            # save the rejected str in case the processing is continued
            # also, we might have unprocessed pieces of the chunk in 'splitted'
            self._laststopat = f"{retval['stopat']}{''.join(splitted)}"

        # add human readable stop reason
        # Sorry mypy, you're getting it wrong here: stopcrit will never be None here
        #  therefore ignore
        retval["stopmsg"] = STOP_MESSAGES[retval["stopcrit"]]  # type: ignore

        # Add remaining values to retval dict
        retval["text"] = "".join(self._completed_lines)
        retval["num_tokens"] = self._num_tokens
        retval["num_lines"] = len(self._completed_lines)
        retval["num_paragraphs"] = self._num_paragraphs

        return retval
