# Library API

Your task is to build a simple API to manage a library's book inventory.  There are two main components of this API: management endpoints (to be used by the Librarians) and user facing endpoints for end-user actions.

Books are referenced by their ISBN.  The library can have more than 1 copy of any given book (multiple copies of the same ISBN).

API Endpoints to be built:

Librarian Endpoints:
* An endpoint to add a book (by ISBN) to the library.
* An endpoint to remove a book (by its internal Id) from the library
* An endpoint that generates a list of all overdue books.

User Endpoints:
* An endpoint to check out a book (assume a 2 week checkout period from time of call).  A User can check out any book except when:
  - They currently have 3 checked out books.
  - They are overdue on returning any book.
* An endpoint to return a checked out book to the library
* An endpoint that lists all currently checked out books for that user.

For the purposes of this exercise, we can assume there is a Librarian user (userId 1)  and three regular users (userids, 2, 3, 4).  You can hardcode this table.  Also, no need to worry about authentication, etc.

-----

## Getting Started

1. Install your favorite virtual environment to avoid affecting your main python environment
`pip install virtualenv`
1. create virtual environment
`virtualenv library`
1. activate virtual envionment:
`source library/bin/activate`
1. Install python dependencies
`pip install -r requirements.txt`
1. Initialize the SQLite database
`sqlite3 data.db < setup.sql`


## Usage

Activate your virtual environment (if desired) and start the API by running:
```
python api.py
```

Where you can upload data via curl (or via tools like Postman):
```
curl http://localhost:5000/<endpoint> -H 'User: <Name>' -X <Method>
```

The available users are:
* Scrooge (user1, librarian)
* Huey (user2)
* Louie (user2)
* Dewey (user3)

The available endpoints are:
* `POST ​/librarian​/book` Add Book by ISBN {"isbn": X, "title": Y}
* `DELETE ​/librarian​/book​/:book_id` Delete Book by ID (see /librarian/catalog)
* `GET ​/librarian​/catalog` List All Books (?details=1 for verbose)
* `GET /librarian​/overdue` List Overdue Books
* `GET /user​/available` List Available Books
* `GET /user​/borrowed` List Available Books
* `GET /user​/checkout​/:book_id` Checkout Book by ID (see /user/borrowed)
* `GET /user​/return​/:book_id` Return Book by ID (see /user/borrowed)

But since swagger was built into the code, you can interactively use:
```
http://localhost:5000/api/docs
```
and click "Try it out" in your browser. Note that Scrooge is only set as the default User on `/librarian` endpoints that do not alter the DB, while Dewey is default for all other endpoints.


## Additional Thoughts

* Deliberately utilized various methods (GET, POST, DELETE) and parameters (path, query, header) to ensure that the API was not one-trick pony. The use of `User: <Name>` header also illustrates how it can easily be converted to Basic Auth or Token String authentication.
* Originally wanted to build it using Chalice and DynamoDB so that it can be deployed to AWS Lambda, but would have required documenting all the IAM policy/role commands in order to easily deploy
* Currently, the Books table does not track multiple copies of the same book or ISBN number, should add logic to handle that
* Obviously, in a larger implementation of a Library API, the use of a messaging queue would ensure that the system can be used by a great many librarians and users --- however, to reach that point, the architecture should probably incorporate library "branches" as well.
