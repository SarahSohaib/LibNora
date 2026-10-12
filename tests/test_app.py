from datetime import date, datetime, timedelta, timezone

import pytest

from app import (
    LibraryError,
    add_book,
    add_member,
    delete_book,
    issue_book,
    list_books,
    return_book,
    _section_index,
    update_book,
)


class Result:
    def __init__(self, matched_count=0, modified_count=0, deleted_count=0):
        self.matched_count = matched_count
        self.modified_count = modified_count
        self.deleted_count = deleted_count


class InsertResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id


class Cursor(list):
    def sort(self, key, direction):
        return Cursor(
            sorted(
                self,
                key=lambda item: (
                    item[key].casefold()
                    if isinstance(item[key], str)
                    else item[key]
                ),
                reverse=direction < 0,
            )
        )


class MemoryCollection:
    def __init__(self):
        self.documents = []
        self.next_id = 1

    def insert_one(self, document):
        stored = dict(document)
        stored["_id"] = self.next_id
        self.next_id += 1
        self.documents.append(stored)
        return InsertResult(stored["_id"])

    def find_one(self, query):
        return next((doc for doc in self.documents if self._matches(doc, query)), None)

    def find(self, query=None):
        return Cursor(
            doc for doc in self.documents if self._matches(doc, query or {})
        )

    def update_one(self, query, update):
        document = self.find_one(query)
        if document is None:
            return Result()
        before = dict(document)
        for key, value in update.get("$set", {}).items():
            document[key] = value
        for key, value in update.get("$inc", {}).items():
            document[key] = document.get(key, 0) + value
        for key in update.get("$unset", {}):
            document.pop(key, None)
        return Result(1, int(document != before))

    def delete_one(self, query):
        document = self.find_one(query)
        if document is None:
            return Result()
        self.documents.remove(document)
        return Result(deleted_count=1)

    @staticmethod
    def _matches(document, query):
        for key, expected in query.items():
            if key == "$or":
                if not any(
                    MemoryCollection._matches(document, condition)
                    for condition in expected
                ):
                    return False
                continue
            actual = document.get(key)
            if isinstance(expected, dict):
                if "$gt" in expected:
                    if actual is None or not actual > expected["$gt"]:
                        return False
                if "$regex" in expected:
                    import re

                    if not isinstance(actual, str):
                        return False
                    flags = (
                        re.IGNORECASE
                        if "i" in expected.get("$options", "")
                        else 0
                    )
                    if not re.search(expected["$regex"], actual, flags):
                        return False
            elif actual != expected:
                return False
        return True


def setup_collections():
    return MemoryCollection(), MemoryCollection(), MemoryCollection()


def test_add_book_normalizes_fields_and_sets_availability():
    books = MemoryCollection()

    created_before = datetime.now(timezone.utc)
    result = add_book(books, "  Dune ", " Frank Herbert ", " 123 ", 2)
    created_after = datetime.now(timezone.utc)
    book = books.find_one({"_id": result.inserted_id})
    assert book is not None
    created_at = book["created_at"]

    assert book["title"] == "Dune"
    assert book["author"] == "Frank Herbert"
    assert book["isbn"] == "123"
    assert book["copies"] == 2
    assert book["available_copies"] == 2
    assert created_before <= created_at <= created_after
    assert created_at.tzinfo is not None


@pytest.mark.parametrize(
    ("title", "author", "copies"),
    [("", "Author", 1), ("Title", "", 1), ("Title", "Author", 0)],
)
def test_add_book_rejects_invalid_fields(title, author, copies):
    with pytest.raises(LibraryError):
        add_book(MemoryCollection(), title, author, "", copies)


def test_add_member_validates_and_normalizes_email():
    users = MemoryCollection()

    add_member(users, "  Alex Doe ", " ALEX@example.com ")

    assert users.documents[0]["name"] == "Alex Doe"
    assert users.documents[0]["email"] == "alex@example.com"
    with pytest.raises(LibraryError):
        add_member(users, "Alex", "not-an-email")


def test_update_book_preserves_issued_copy_count():
    books = MemoryCollection()
    book_id = add_book(books, "Dune", "Frank Herbert", "", 3).inserted_id
    books.update_one({"_id": book_id}, {"$inc": {"available_copies": -1}})
    books.update_one({"_id": book_id}, {"$inc": {"available_copies": -1}})

    update_book(books, book_id, "Dune Messiah", "Frank Herbert", 4)

    book = books.find_one({"_id": book_id})
    assert book is not None
    assert book["copies"] == 4
    assert book["available_copies"] == 2
    with pytest.raises(LibraryError):
        update_book(books, book_id, "Dune Messiah", "Frank Herbert", 1)
    with pytest.raises(LibraryError, match="not found"):
        update_book(books, "missing", "Dune", "Frank Herbert", 1)


def test_issue_failure_restores_book_availability():
    books = MemoryCollection()
    book_id = add_book(books, "Dune", "Frank Herbert", "", 1).inserted_id

    class BrokenLoans:
        @staticmethod
        def insert_one(document):
            assert document["status"] == "issued"
            raise RuntimeError("database write failed")

    with pytest.raises(RuntimeError, match="database write failed"):
        issue_book(
            books,
            BrokenLoans(),
            book_id,
            "member-id",
            date.today() + timedelta(days=7),
        )

    book = books.find_one({"_id": book_id})
    assert book is not None
    assert book["available_copies"] == 1


def test_issue_and_return_update_availability_and_loan_status():
    books, users, loans = setup_collections()
    book_id = add_book(books, "Dune", "Frank Herbert", "", 1).inserted_id
    user_id = add_member(users, "Alex Doe", "alex@example.com").inserted_id

    loan_id = issue_book(
        books, loans, book_id, user_id, date.today() + timedelta(days=7)
    ).inserted_id
    book = books.find_one({"_id": book_id})
    assert book is not None
    assert book["available_copies"] == 0

    with pytest.raises(LibraryError, match="not available"):
        issue_book(books, loans, book_id, user_id, date.today() + timedelta(days=7))

    return_book(books, loans, loan_id)
    book = books.find_one({"_id": book_id})
    assert book is not None
    assert book["available_copies"] == 1
    loan = loans.find_one({"_id": loan_id})
    assert loan is not None
    assert loan["status"] == "returned"
    with pytest.raises(LibraryError, match="not found"):
        return_book(books, loans, loan_id)


def test_issue_rejects_past_due_date_without_changing_availability():
    books = MemoryCollection()
    loans = MemoryCollection()
    book_id = add_book(books, "Dune", "Frank Herbert", "", 1).inserted_id

    with pytest.raises(LibraryError, match="future"):
        issue_book(books, loans, book_id, "member-id", date.today())

    book = books.find_one({"_id": book_id})
    assert book is not None
    assert book["available_copies"] == 1
    assert loans.find() == []


def test_return_missing_book_restores_active_loan_state():
    books, users, loans = setup_collections()
    book_id = add_book(books, "Dune", "Frank Herbert", "", 1).inserted_id
    user_id = add_member(users, "Alex Doe", "alex@example.com").inserted_id
    loan_id = issue_book(
        books, loans, book_id, user_id, date.today() + timedelta(days=7)
    ).inserted_id
    books.delete_one({"_id": book_id})

    with pytest.raises(LibraryError, match="book record is missing"):
        return_book(books, loans, loan_id)

    loan = loans.find_one({"_id": loan_id})
    assert loan is not None
    assert loan["status"] == "issued"
    assert "returned_at" not in loan


def test_delete_book_rejects_any_borrowing_history():
    books, users, loans = setup_collections()
    book_id = add_book(books, "Dune", "Frank Herbert", "", 1).inserted_id
    user_id = add_member(users, "Alex Doe", "alex@example.com").inserted_id
    issue_book(
        books, loans, book_id, user_id, date.today() + timedelta(days=7)
    )

    with pytest.raises(LibraryError, match="history"):
        delete_book(books, loans, book_id)

    unborrowed_book_id = add_book(
        books, "Foundation", "Isaac Asimov", "", 1
    ).inserted_id
    delete_book(books, MemoryCollection(), unborrowed_book_id)
    assert books.find_one({"_id": unborrowed_book_id}) is None


def test_book_search_matches_title_and_author_without_regex_injection():
    books = MemoryCollection()
    add_book(books, "Dune", "Frank Herbert", "", 1)
    add_book(books, "Foundation", "Isaac Asimov", "", 1)

    assert [book["title"] for book in list_books(books, "herbert")] == ["Dune"]
    assert list_books(books, ".*") == []


def test_book_search_results_are_sorted_case_insensitively():
    books = MemoryCollection()
    add_book(books, "zebra", "Author", "", 1)
    add_book(books, "Apple", "Author", "", 1)
    add_book(books, "mango", "Author", "", 1)

    assert [book["title"] for book in list_books(books)] == [
        "Apple",
        "mango",
        "zebra",
    ]


def test_section_index_restores_view_after_browser_refresh():
    sections = ["Dashboard", "Books", "Members", "Issue / Return"]

    assert _section_index("Books", sections) == 1
    assert _section_index("Members", sections) == 2
    assert _section_index(None, sections) == 0
    assert _section_index("invalid", sections) == 0
