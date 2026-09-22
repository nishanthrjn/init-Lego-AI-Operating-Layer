"""Small intake consumer over explicitly supplied text; no repository I/O."""

from legoai_engineering.repository.api import inspect_text
from legoai_engineering.repository.values import InspectionRequest, RepositoryText


def main() -> None:
    # A later acquisition adapter must govern real filesystem input separately.
    supplied = (
        RepositoryText("README.md", "A small Python application.\n"),
        RepositoryText("pyproject.toml", '[project]\nrequires-python = ">=3.14"\n'),
    )
    result = inspect_text(InspectionRequest(supplied, "requires-python", 10))
    for match in result.matches:
        print(f"{match.path}:{match.line}:{match.column}")


if __name__ == "__main__":
    main()
