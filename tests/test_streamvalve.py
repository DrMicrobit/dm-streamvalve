"""Tests for streamvalve"""

import pytest

from dm_streamvalve.streamvalve import StopCriterion, StreamValve

# Pylint: ignore missing function docstrings
# pylint: disable = C0116


# test edge case: empty

retval_empty = {
    "text": "",
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
        "num_lines": 8,
        "num_paragraphs": 3,
        "stopcrit": StopCriterion.END_OF_STREAM,
        "stopmsg": "Stream ended.",
        "stopat": None,
    }


# Test early termination
# earlyterm_txt = [
#    (
#        "The sky appears blue to our eyes due to a phenomenon called Rayleigh"
#        " scattering, named after the British physicist Lord Rayleigh who first"
#        " described it in the late 19th century. This scattering occurs when"
#        " sunlight enters Earth's atmosphere and encounters tiny molecules"
#        " of gases such as nitrogen and oxygen.\n"
#    ),
#    "\n",
#    (
#        "As sunlight travels through the atmosphere, it collides with these gas"
#        " molecules. The shorter (blue) wavelengths are scattered more than the"
#        " longer (red) wavelengths by the smaller molecules. This is because the"
#        " smaller molecules can change direction more easily due to their size"
#        " and mass. As a result, the blue light is dispersed in all directions,"
#        " giving the sky its blue color.\n"
#    ),
#    "\n",
#    "And so on, and so on ...\n",
# ]
#

earlyterm_txt = ["Test line.rep\n", "\n", "rep\n", "rep\n\n", "rep", "\n", "\nLast line"]


def test_earlyterm_noterm():
    s = StreamValve(earlyterm_txt)
    assert s.process() == {
        "text": "Test line.rep\n\nrep\nrep\n\nrep\n\nLast line",
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
        "num_lines": 2,
        "num_paragraphs": 1,
        "stopcrit": StopCriterion.MAX_LINES,
        "stopat": "rep\n",
        "stopmsg": "Maximum number of lines reached.",
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
        "num_lines": 2,
        "num_paragraphs": 1,
        "stopcrit": StopCriterion.MAX_LINES,
        "stopat": "rep\n",
        "stopmsg": "Maximum number of lines reached.",
    }
    print("++++++++++++")
    assert s.process() == {
        "text": "rep\nrep\n",
        "num_lines": 2,
        "num_paragraphs": 1,
        "stopcrit": StopCriterion.MAX_LINES,
        "stopat": "\n",
        "stopmsg": "Maximum number of lines reached.",
    }
    print("++++++++++++")
    assert s.process() == {
        "text": "\nrep\n",
        "num_lines": 2,
        "num_paragraphs": 1,
        "stopcrit": StopCriterion.MAX_LINES,
        "stopat": "\n",
        "stopmsg": "Maximum number of lines reached.",
    }
    assert s.process() == {
        "text": "\nLast line",
        "num_lines": 1,
        "num_paragraphs": 1,
        "stopcrit": StopCriterion.END_OF_STREAM,
        "stopat": None,
        "stopmsg": "Stream ended.",
    }
    # Stream is be exhausted by now, subsequent calls should get this
    assert s.process() == {
        "text": "",
        "num_lines": 0,
        "num_paragraphs": 0,
        "stopcrit": StopCriterion.END_OF_STREAM,
        "stopat": None,
        "stopmsg": "Stream ended.",
    }


# Test callable

stream_tuples = [
    ("Test line.rep\n", 0),
    ("\n", 0),
    ("rep\n", 0),
    ("rep\n\n", 0),
    ("rep\n", 0),
    ("\nLast line", 0),
]


def test_callable():
    def extractor(tup: tuple[str, int]) -> str:
        return tup[0]

    s = StreamValve(stream_tuples, extractor)
    assert s.process() == {
        "text": "Test line.rep\n\nrep\nrep\n\nrep\n\nLast line",
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
        "num_lines": 3,
        "num_paragraphs": 2,
        "stopcrit": StopCriterion.BY_CALLABLE,
        "stopat": None,
        "stopmsg": "Streamvalve stopped externally.",
    }


# Test bug which happened:
def test_newline_not_repeat():
    s = StreamValve(["Test.\n", "\n", "\n", "\n", "\n", "Last line."], max_linerepeats=2)
    assert s.process() == {
        "text": "Test.\n\n\n\n\nLast line.",
        "num_lines": 6,
        "num_paragraphs": 2,
        "stopcrit": StopCriterion.END_OF_STREAM,
        "stopmsg": "Stream ended.",
        "stopat": None,
    }
