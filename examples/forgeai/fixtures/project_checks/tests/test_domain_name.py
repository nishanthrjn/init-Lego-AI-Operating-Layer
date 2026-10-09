from domain_name import ascii_hostname


def test_unicode_hostname() -> None:
    assert ascii_hostname("bücher.example") == "xn--bcher-kva.example"
