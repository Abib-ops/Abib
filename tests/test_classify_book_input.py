from scripture import classify_book_input


def test_classify_exact_match_full_name():
    out = classify_book_input("Amos")
    assert out["status"] == "exact"
    assert out["book_id"] == 30


def test_classify_short_with_separator_variants():
    # Space separator
    out = classify_book_input("am 1:1")
    assert out["status"] == "short_with_sep" and out["book_id"] == 30
    # Dot separator
    out = classify_book_input("am.1:1")
    assert out["status"] == "short_with_sep" and out["book_id"] == 30
    # Colon separator
    out = classify_book_input("am:1")
    assert out["status"] == "short_with_sep" and out["book_id"] == 30
    # Hyphen separator
    out = classify_book_input("am-1:1")
    assert out["status"] == "short_with_sep" and out["book_id"] == 30


def test_classify_ambiguous_prefix_person_name():
    out = classify_book_input("Amaziah")
    assert out["status"] == "ambiguous_prefix"
    # Should propose Amos via 'am'
    assert out["book_id"] == 30


def test_classify_none_for_empty():
    out = classify_book_input("")
    assert out["status"] == "none"
