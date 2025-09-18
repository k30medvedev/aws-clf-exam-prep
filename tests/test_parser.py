import textwrap

from core import parse_options, parse_exam, Option


def test_parse_options_handles_letters_and_bullets():
    raw = textwrap.dedent("""
        A. First option
        B) Second option
        - C. Third option (with dash)
        - Just a bullet without letter
    """).strip()
    opts = parse_options(raw)
    assert [o.letter for o in opts] == ["A", "B", "C", "D"]
    assert opts[0] == Option(letter="A", text="First option")
    assert opts[3].text == "Just a bullet without letter"


def test_parse_exam_extracts_questions_and_correct_letters():
    md = textwrap.dedent("""
        1. Which two are correct?
        A. Alpha
        B. Beta
        C. Gamma
        <details><summary>Answer</summary>
        Correct answer: A, C
        </details>

        2. Single correct?
        - A. Apple
        - B. Banana
        - C. Cherry
        <details><summary>Answer</summary>
        Correct answer: b
        </details>
    """).strip()
    qs = parse_exam(md)
    assert len(qs) == 2
    assert [o.letter for o in qs[0].options] == ["A", "B", "C"]
    assert qs[0].correct == ["A", "C"]
    assert qs[1].correct == ["B"]
