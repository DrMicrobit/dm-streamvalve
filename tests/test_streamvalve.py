"""Tests for streamvalve"""

import pytest

from dm_streamvalve.streamvalve import StopCriterion, StreamValve

# Pylint: ignore missing function docstrings
# pylint: disable = C0116


# test edge case: empty

retval_empty = {
    "text": "",
    "num_tokens": 0,
    "num_lines": 0,
    "num_paragraphs": 0,
    "stopcrit": StopCriterion.END_OF_STREAM,
    "stopmsg": "Stream ended.",
    "stopat": None,
}


@pytest.mark.parametrize(
    "parameter, expected_output",
    [
        ([], retval_empty),
        ([""], retval_empty),
        (["", ""], retval_empty),
        (["", ""], retval_empty),
    ],
)
def test_empty(parameter, expected_output):
    s = StreamValve(parameter)
    assert s.process() == expected_output


# Test everything I expect to be correct


def test_join():
    s = StreamValve(["He", "l", "", "lo"])
    assert s.process() == {
        "text": "Hello",
        "num_tokens": 3,
        "num_lines": 1,
        "num_paragraphs": 1,
        "stopcrit": StopCriterion.END_OF_STREAM,
        "stopmsg": "Stream ended.",
        "stopat": None,
    }


def test_counts():
    s = StreamValve(
        [
            "Hello\nWorld\n",
            "\nNice day for fishin', eh?",
            "\n",
            "\n\n",
            "\nFind that reference :-)\n",
        ]
    )
    assert s.process() == {
        "text": "Hello\nWorld\n\nNice day for fishin', eh?\n\n\n\nFind that reference :-)\n",
        "num_tokens": 9,
        "num_lines": 8,
        "num_paragraphs": 3,
        "stopcrit": StopCriterion.END_OF_STREAM,
        "stopmsg": "Stream ended.",
        "stopat": None,
    }


earlyterm_txt = ["Test line.rep\n", "\n", "rep\n", "rep\n\n", "rep", "\n", "\nLast line"]


def test_earlyterm_noterm():
    s = StreamValve(earlyterm_txt)
    assert s.process() == {
        "text": "Test line.rep\n\nrep\nrep\n\nrep\n\nLast line",
        "num_tokens": 9,
        "num_lines": 8,
        "num_paragraphs": 4,
        "stopcrit": StopCriterion.END_OF_STREAM,
        "stopmsg": "Stream ended.",
        "stopat": None,
    }


def test_earlyterm_maxlinerep():
    s = StreamValve(earlyterm_txt, max_linerepeats=2)
    assert s.process() == {
        "text": "Test line.rep\n\nrep\nrep\n\n",
        "num_tokens": 7,
        "num_lines": 5,
        "num_paragraphs": 2,
        "stopcrit": StopCriterion.MAX_LINEREPEATS,
        "stopat": "rep\n",
        "stopmsg": "Maximum number of exact repeated lines reached.",
    }


def test_earlyterm_maxpara():
    s = StreamValve(earlyterm_txt, max_paragraphs=2)
    assert s.process() == {
        "text": "Test line.rep\n\nrep\nrep\n\n",
        "num_tokens": 5,
        "num_lines": 5,
        "num_paragraphs": 2,
        "stopcrit": StopCriterion.MAX_PARAGRAPHS,
        "stopat": "rep",
        "stopmsg": "Maximum number of paragraphs reached.",
    }


def test_earlyterm_maxlines():
    s = StreamValve(earlyterm_txt, max_lines=2)
    assert s.process() == {
        "text": "Test line.rep\n\n",
        "num_tokens": 2,
        "num_lines": 2,
        "num_paragraphs": 1,
        "stopcrit": StopCriterion.MAX_LINES,
        "stopat": "rep\n",
        "stopmsg": "Maximum number of lines reached.",
    }


def test_earlyterm_maxlinetokens():
    toolong_txt = ["Line 1\n", "This", " ", "line", " ", "will", " ", "be", " ", "too", " ", "long"]
    s = StreamValve(toolong_txt, max_linetokens=8)
    assert s.process() == {
        "text": "Line 1\nThis line will be too",
        "num_tokens": 10,
        "num_lines": 2,
        "num_paragraphs": 1,
        "stopcrit": StopCriterion.MAX_LINETOKENS,
        "stopat": "too",
        "stopmsg": "Maximum number of tokens in a line reached.",
    }


# earlyterm_txt = ["Test line.rep\n", "\n", "rep\n", "rep\n\n", "rep", "\n", "\nLast line"]

# Test line.rep\n
# \n

# rep\n
# rep\n

# \n
# rep\n

# \n
# Last line


def test_continue_after_earlyterm():
    s = StreamValve(earlyterm_txt, max_lines=2)
    assert s.process() == {
        "text": "Test line.rep\n\n",
        "num_tokens": 2,
        "num_lines": 2,
        "num_paragraphs": 1,
        "stopcrit": StopCriterion.MAX_LINES,
        "stopat": "rep\n",
        "stopmsg": "Maximum number of lines reached.",
    }
    print("++++++++++++")
    assert s.process() == {
        "text": "rep\nrep\n",
        "num_tokens": 2,
        "num_lines": 2,
        "num_paragraphs": 1,
        "stopcrit": StopCriterion.MAX_LINES,
        "stopat": "\n",
        "stopmsg": "Maximum number of lines reached.",
    }
    print("++++++++++++")
    assert s.process() == {
        "text": "\nrep\n",
        "num_tokens": 3,
        "num_lines": 2,
        "num_paragraphs": 1,
        "stopcrit": StopCriterion.MAX_LINES,
        "stopat": "\n",
        "stopmsg": "Maximum number of lines reached.",
    }
    assert s.process() == {
        "text": "\nLast line",
        "num_tokens": 1,
        "num_lines": 1,
        "num_paragraphs": 1,
        "stopcrit": StopCriterion.END_OF_STREAM,
        "stopat": None,
        "stopmsg": "Stream ended.",
    }
    # Stream is exhausted by now, subsequent calls should get this
    assert s.process() == {
        "text": "",
        "num_tokens": 0,
        "num_lines": 0,
        "num_paragraphs": 0,
        "stopcrit": StopCriterion.END_OF_STREAM,
        "stopat": None,
        "stopmsg": "Stream ended.",
    }


# Test callable
# Define as test a stream of tuples to simulate a stream of customized elements
stream_tuples = [
    ("Test line.rep\n", 0),
    ("\n", 0),
    ("rep\n", 0),
    ("rep\n\n", 0),
    ("rep\n", 0),
    ("\nLast line", 0),
]


def test_callable_extractor():
    def extractor(tup: tuple[str, int]) -> str:
        # in our customized stream, the text is in first element of the tuple
        return tup[0]

    s = StreamValve(stream_tuples, callback_extract=extractor)
    assert s.process() == {
        "text": "Test line.rep\n\nrep\nrep\n\nrep\n\nLast line",
        "num_tokens": 8,
        "num_lines": 8,
        "num_paragraphs": 4,
        "stopcrit": StopCriterion.END_OF_STREAM,
        "stopmsg": "Stream ended.",
        "stopat": None,
    }


def test_callable_earlystop():
    def extractor(tup: tuple[str, int]) -> str | None:
        if tup[0] == "rep\n\n":
            return None
        return tup[0]

    s = StreamValve(stream_tuples, extractor)
    assert s.process() == {
        "text": "Test line.rep\n\nrep\n",
        "num_tokens": 3,
        "num_lines": 3,
        "num_paragraphs": 2,
        "stopcrit": StopCriterion.BY_CALLABLE,
        "stopat": None,
        "stopmsg": "Streamvalve stopped externally.",
    }


# for increasing coverage of the source
def test_callable_token_and_line():
    def cbtoken(token: str) -> None:
        # we could, e.g., print the token
        return

    def cbline(line: str) -> None:
        # we could, e.g., print the line
        return

    tsttxt = ["some ", "test"]
    s = StreamValve(tsttxt, callback_token=cbtoken, callback_line=cbline)
    assert s.process() == {
        "text": "some test",
        "num_tokens": 2,
        "num_lines": 1,
        "num_paragraphs": 1,
        "stopcrit": StopCriterion.END_OF_STREAM,
        "stopmsg": "Stream ended.",
        "stopat": None,
    }


# Test bug which happened:
def test_newline_not_repeat():
    s = StreamValve(["Test.\n", "\n", "\n", "\n", "\n", "Last line."], max_linerepeats=2)
    assert s.process() == {
        "text": "Test.\n\n\n\n\nLast line.",
        "num_tokens": 6,
        "num_lines": 6,
        "num_paragraphs": 2,
        "stopcrit": StopCriterion.END_OF_STREAM,
        "stopmsg": "Stream ended.",
        "stopat": None,
    }
