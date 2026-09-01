"""Tests that extracted document text stays aligned with document indices.

An empty paragraph occupies an index in the document. Dropping it from the
extracted text shifts every subsequent offset, so any index computed by
searching that text lands in the wrong place. Same for paragraph elements
that are not textRun.
"""

from gdocs.docs_helpers import (
    OBJECT_REPLACEMENT_CHAR,
    extract_text_from_elements,
)


def _para(*elements):
    return {"paragraph": {"elements": list(elements)}}


def _run(content, start=None, end=None):
    element = {"textRun": {"content": content}}
    if start is not None:
        element["startIndex"] = start
        element["endIndex"] = end
    return element


# Body is "Alpha", empty paragraph, "Bravo", empty paragraph — indices 1..15.
ALPHA_BRAVO_BODY = [
    _para(_run("Alpha\n")),
    _para(_run("\n")),
    _para(_run("Bravo\n")),
    _para(_run("\n")),
]


def test_empty_paragraphs_are_preserved():
    assert extract_text_from_elements(ALPHA_BRAVO_BODY) == "Alpha\n\nBravo\n\n"


def test_extracted_length_matches_document_span():
    """Body spans indices 1-15, i.e. 14 characters."""
    assert len(extract_text_from_elements(ALPHA_BRAVO_BODY)) == 15 - 1


def test_offset_of_later_text_matches_document_index():
    """'Bravo' starts at index 8; searching the extracted text must agree.

    The extracted text is 0-based while document indices start the body at 1,
    so the document index is the offset plus one.
    """
    text = extract_text_from_elements(ALPHA_BRAVO_BODY)
    assert text.index("Bravo") + 1 == 8


def test_paragraph_with_no_elements_still_contributes_nothing_but_is_not_dropped():
    body = [_para(_run("A\n")), {"paragraph": {}}, _para(_run("B\n"))]
    assert extract_text_from_elements(body) == "A\nB\n"


def test_page_break_occupies_its_index_span():
    body = [
        _para(_run("Alpha\n")),
        _para({"pageBreak": {}, "startIndex": 7, "endIndex": 8}, _run("\n")),
    ]
    text = extract_text_from_elements(body)
    assert text == "Alpha\n" + OBJECT_REPLACEMENT_CHAR + "\n"
    assert len(text) == 8


def test_inline_object_occupies_one_index():
    body = [
        _para(
            _run("a"),
            {"inlineObjectElement": {"inlineObjectId": "kix.1"}},
            _run("b\n"),
        )
    ]
    assert extract_text_from_elements(body) == "a" + OBJECT_REPLACEMENT_CHAR + "b\n"


def test_non_text_element_without_span_falls_back_to_one_char():
    body = [_para({"footnoteReference": {"footnoteId": "kix.f1"}}, _run("\n"))]
    assert extract_text_from_elements(body) == OBJECT_REPLACEMENT_CHAR + "\n"


def test_unknown_element_types_contribute_nothing():
    body = [_para(_run("a\n"), {"someFutureElement": {}})]
    assert extract_text_from_elements(body) == "a\n"


def test_tab_header_is_emitted_when_named():
    text = extract_text_from_elements(ALPHA_BRAVO_BODY, "My Tab", "t.abc")
    assert text.startswith("\n--- TAB: My Tab (ID: t.abc) ---\n")
    assert text.endswith("Alpha\n\nBravo\n\n")


def test_table_cell_text_is_included():
    body = [
        {
            "table": {
                "tableRows": [
                    {"tableCells": [{"content": [_para(_run("cell\n"))]}]},
                ]
            }
        }
    ]
    assert extract_text_from_elements(body) == "cell\n"


def test_recursion_is_bounded():
    assert extract_text_from_elements([_para(_run("x\n"))], depth=6) == ""
