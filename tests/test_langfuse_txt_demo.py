from examples.langfuse_txt_demo import _known_values, _split_sections


def test_split_sections_groups_category_blocks() -> None:
    text = "A:\n1. one\n2. two\n\nB:\n1. three"

    assert _split_sections(text) == ["A:\n1. one\n2. two\n", "B:\n1. three"]


def test_known_values_extracts_numbered_examples() -> None:
    text = "EMAIL:\n1. Contact: jan@example.com.\n2. No prefix value.\n\nOTHER:\n3. Token: ABC-123."

    assert _known_values(text) == ["jan@example.com", "No prefix value", "ABC-123"]
