"""Streamlit entry point and MongoDB-backed library operations."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Any


class LibraryError(ValueError):
    """Raised when a requested library operation is invalid."""


def _required_text(value: str, field: str) -> str:
    text = value.strip()
    if not text:
        raise LibraryError(f"{field} is required.")
    return text


def add_book(
    books: Any, title: str, author: str, isbn: str, copies: int
) -> Any:
    title = _required_text(title, "Title")
    author = _required_text(author, "Author")
    isbn = isbn.strip()
    if copies < 1:
        raise LibraryError("Copies must be at least 1.")

    return books.insert_one(
        {
            "title": title,
            "author": author,
            "isbn": isbn,
            "copies": copies,
            "available_copies": copies,
            "created_at": datetime.now(timezone.utc),
        }
    )


def add_member(users: Any, name: str, email: str) -> Any:
    name = _required_text(name, "Name")
    email = _required_text(email, "Email").lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise LibraryError("Enter a valid email address.")

    return users.insert_one(
        {
            "name": name,
            "email": email,
            "created_at": datetime.now(timezone.utc),
        }
    )


def update_book(
    books: Any, book_id: Any, title: str, author: str, copies: int
) -> None:
    title = _required_text(title, "Title")
    author = _required_text(author, "Author")
    book = books.find_one({"_id": book_id})
    if book is None:
        raise LibraryError("Book not found.")
    if copies < 1 or copies < book["copies"] - book["available_copies"]:
        raise LibraryError("Copies cannot be fewer than the copies currently on loan.")

    result = books.update_one(
        {
            "_id": book_id,
            "copies": book["copies"],
            "available_copies": book["available_copies"],
        },
        {
            "$set": {
                "title": title,
                "author": author,
                "copies": copies,
                "available_copies": copies
                - (book["copies"] - book["available_copies"]),
            }
        },
    )
    if result.matched_count != 1:
        raise LibraryError("The book changed while being edited; refresh and try again.")


def delete_book(books: Any, loans: Any, book_id: Any) -> None:
    if loans.find_one({"book_id": book_id}) is not None:
        raise LibraryError("Books with borrowing history cannot be deleted.")
    book = books.find_one({"_id": book_id})
    if book is None:
        raise LibraryError("Book not found.")
    result = books.delete_one(
        {
            "_id": book_id,
            "available_copies": book["copies"],
        }
    )
    if result.deleted_count != 1:
        raise LibraryError("The book changed while being deleted; refresh and try again.")


def issue_book(
    books: Any, loans: Any, book_id: Any, user_id: Any, due_date: date
) -> Any:
    if due_date <= date.today():
        raise LibraryError("The due date must be in the future.")

    result = books.update_one(
        {"_id": book_id, "available_copies": {"$gt": 0}},
        {"$inc": {"available_copies": -1}},
    )
    if result.modified_count != 1:
        raise LibraryError("This book is not available.")

    try:
        return loans.insert_one(
            {
                "book_id": book_id,
                "user_id": user_id,
                "issued_at": datetime.now(timezone.utc),
                "due_date": due_date.isoformat(),
                "returned_at": None,
                "status": "issued",
            }
        )
    except Exception as error:
        rollback = books.update_one(
            {"_id": book_id}, {"$inc": {"available_copies": 1}}
        )
        if rollback.modified_count != 1:
            raise RuntimeError("Could not restore book availability after issue failed.") from error
        raise


def return_book(books: Any, loans: Any, loan_id: Any) -> None:
    loan = loans.find_one({"_id": loan_id, "status": "issued"})
    if loan is None:
        raise LibraryError("Active borrowing record not found.")

    returned_at = datetime.now(timezone.utc)
    result = loans.update_one(
        {"_id": loan_id, "status": "issued"},
        {"$set": {"status": "returned", "returned_at": returned_at}},
    )
    if result.modified_count != 1:
        raise LibraryError("This borrowing record has already been returned.")

    book_result = books.update_one(
        {"_id": loan["book_id"]}, {"$inc": {"available_copies": 1}}
    )
    if book_result.modified_count != 1:
        rollback = loans.update_one(
            {"_id": loan_id, "status": "returned"},
            {"$set": {"status": "issued"}, "$unset": {"returned_at": ""}},
        )
        if rollback.modified_count != 1:
            raise RuntimeError("Could not restore the borrowing record after return failed.")
        raise LibraryError("The book record is missing; the return was not recorded.")


def list_books(books: Any, query: str = "") -> list[dict[str, Any]]:
    search = query.strip()
    if not search:
        return list(books.find().sort("title", 1))
    pattern = re.escape(search)
    return list(
        books.find(
            {
                "$or": [
                    {"title": {"$regex": pattern, "$options": "i"}},
                    {"author": {"$regex": pattern, "$options": "i"}},
                    {"isbn": {"$regex": pattern, "$options": "i"}},
                ]
            }
        ).sort("title", 1)
    )


def _section_index(section: str | None, sections: list[str]) -> int:
    return sections.index(section) if section in sections else 0


def _database(uri: str, database_name: str) -> Any:
    from pymongo import MongoClient

    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    database = client[database_name]
    database.books.create_index(
        "isbn",
        unique=True,
        partialFilterExpression={"isbn": {"$type": "string", "$gt": ""}},
    )
    database.users.create_index("email", unique=True)
    return database


def run_app() -> None:
    import streamlit as st
    from pymongo.errors import PyMongoError

    try:
        _run_app()
    except PyMongoError as error:
        st.error(f"MongoDB operation failed: {error}")


def _run_app() -> None:
    import os

    import streamlit as st
    from pymongo.errors import DuplicateKeyError, PyMongoError

    st.set_page_config(page_title="LibNora", page_icon="📚", layout="wide")
    st.title("LibNora")
    st.caption("Library management")

    @st.cache_resource
    def get_database(uri: str, database_name: str) -> Any:
        return _database(uri, database_name)

    try:
        db = get_database(
            os.getenv("MONGODB_URI", "mongodb://localhost:27017"),
            os.getenv("MONGODB_DATABASE", "libnora"),
        )
    except PyMongoError as error:
        st.error(f"Could not connect to MongoDB: {error}")
        st.stop()

    sections = ["Dashboard", "Books", "Members", "Issue / Return"]
    section = st.sidebar.radio(
        "Navigation",
        sections,
        index=_section_index(st.query_params.get("section"), sections),
    )
    if st.query_params.get("section") != section:
        st.query_params["section"] = section
    books = db.books
    users = db.users
    loans = db.loans

    if section == "Dashboard":
        st.subheader("Library overview")
        col1, col2, col3 = st.columns(3)
        col1.metric("Titles", books.count_documents({}))
        col2.metric("Members", users.count_documents({}))
        col3.metric("Books on loan", loans.count_documents({"status": "issued"}))

    elif section == "Books":
        st.subheader("Books")
        with st.expander("Add a book"):
            with st.form("add_book"):
                title = st.text_input("Title")
                author = st.text_input("Author")
                isbn = st.text_input("ISBN (optional)")
                copies = st.number_input("Copies", min_value=1, step=1)
                submitted = st.form_submit_button("Add book")
            if submitted:
                try:
                    add_book(books, title, author, isbn, int(copies))
                    st.success("Book added.")
                except (LibraryError, DuplicateKeyError) as error:
                    st.error(str(error))

        search = st.text_input("Search by title, author, or ISBN")
        records = list_books(books, search)
        if records:
            st.dataframe(
                [
                    {
                        "Title": book["title"],
                        "Author": book["author"],
                        "ISBN": book.get("isbn", ""),
                        "Available": f'{book["available_copies"]}/{book["copies"]}',
                    }
                    for book in records
                ],
                use_container_width=True,
                hide_index=True,
            )
            options = {str(book["_id"]): book for book in records}
            selected_id = st.selectbox("Choose a book to edit or remove", options)
            selected = options[selected_id]
            with st.form("update_book"):
                title = st.text_input("Updated title", value=selected["title"])
                author = st.text_input("Updated author", value=selected["author"])
                copies = st.number_input(
                    "Total copies",
                    min_value=1,
                    value=int(selected["copies"]),
                    step=1,
                )
                update_submitted = st.form_submit_button("Save changes")
            if update_submitted:
                try:
                    update_book(books, selected["_id"], title, author, int(copies))
                    st.success("Book updated.")
                except LibraryError as error:
                    st.error(str(error))
            if st.button("Delete selected book"):
                try:
                    delete_book(books, loans, selected["_id"])
                    st.success("Book deleted.")
                except LibraryError as error:
                    st.error(str(error))
        else:
            st.info("No books match this search.")

    elif section == "Members":
        st.subheader("Members")
        with st.form("add_member"):
            name = st.text_input("Name")
            email = st.text_input("Email")
            submitted = st.form_submit_button("Add member")
        if submitted:
            try:
                add_member(users, name, email)
                st.success("Member added.")
            except (LibraryError, DuplicateKeyError) as error:
                st.error(str(error))

        members = list(users.find().sort("name", 1))
        if members:
            st.dataframe(
                [{"Name": member["name"], "Email": member["email"]} for member in members],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No members have been added yet.")

    else:
        st.subheader("Issue or return a book")
        available_books = list(books.find({"available_copies": {"$gt": 0}}).sort("title", 1))
        members = list(users.find().sort("name", 1))
        if not members:
            st.info("Add a member before issuing books.")
        elif not available_books:
            st.info("There are no books currently available.")
        else:
            book_options = {str(book["_id"]): book for book in available_books}
            member_options = {str(member["_id"]): member for member in members}
            with st.form("issue_book"):
                book_id = st.selectbox(
                    "Book",
                    book_options,
                    format_func=lambda key: (
                        f'{book_options[key]["title"]} '
                        f'({book_options[key]["available_copies"]} available)'
                    ),
                )
                user_id = st.selectbox(
                    "Member",
                    member_options,
                    format_func=lambda key: (
                        f'{member_options[key]["name"]} '
                        f'({member_options[key]["email"]})'
                    ),
                )
                due_date = st.date_input(
                    "Due date", value=date.today() + timedelta(days=14)
                )
                submitted = st.form_submit_button("Issue book")
            if submitted:
                try:
                    issue_book(
                        books,
                        loans,
                        book_options[book_id]["_id"],
                        member_options[user_id]["_id"],
                        due_date,
                    )
                    st.success("Book issued.")
                except LibraryError as error:
                    st.error(str(error))

        active_loans = list(loans.find({"status": "issued"}).sort("due_date", 1))
        if active_loans:
            st.markdown("#### Active loans")
            loan_labels: dict[str, Any] = {}
            for loan in active_loans:
                book = books.find_one({"_id": loan["book_id"]})
                member = users.find_one({"_id": loan["user_id"]})
                book_title = book["title"] if book else "Deleted book"
                member_name = member["name"] if member else "Deleted member"
                loan_labels[
                    f"{book_title} — {member_name} (due {loan['due_date']})"
                ] = loan["_id"]
            label = st.selectbox("Select a loan to return", loan_labels)
            if st.button("Record return"):
                try:
                    return_book(books, loans, loan_labels[label])
                    st.success("Book returned.")
                except LibraryError as error:
                    st.error(str(error))


if __name__ == "__main__":
    run_app()
