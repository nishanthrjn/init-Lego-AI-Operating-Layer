from pager.pages import page_count


def test_page_count_for_full_pages() -> None:
    assert page_count(10, 5) == 2
