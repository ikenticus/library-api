import datetime
import json
import sqlite3
import sys

from flask import Flask, request, jsonify
from flask_swagger import swagger
from flask_swagger_ui import get_swaggerui_blueprint

app = Flask(__name__)
dbpath = 'data.db'
conn = sqlite3.connect(dbpath, check_same_thread=False)

# maximum number of borrowed books allowed
max_books = 2


def select_query(query):
    c = conn.cursor()
    c.execute(query)
    cols = [c[0] for c in c.description]
    rows = [row for row in c.fetchall()]
    data = [dict(zip(cols, row)) for row in rows]
    return data


# check valid user
def check_user(user, librarian=False):
    query = """
        SELECT r.role AS role, u.id AS user_id
          FROM Roles r
         INNER JOIN Users u ON u.role_id = r.id
         WHERE u.name = '%s';
    """ % user
    role = select_query(query)
    if librarian and role[0].get('role') == 'librarian':
        return role[0].get('user_id')
    elif not librarian and role:
        return role[0].get('user_id')
    return False


# query all books
def query_books():
    query = 'SELECT * FROM Books;'
    return select_query(query)


# query all books with details
def query_details():
    query = """
        SELECT u.id AS user_id,
               u.name AS user_name,
               b.id AS book_id,
               b.isbn AS ISBN,
               b.title AS Title,
               x.date_out AS 'Checked Out',
               x.date_due AS 'Due Date'
          FROM Books b
          LEFT OUTER JOIN Borrowed x ON x.book_id = b.id
          LEFT OUTER JOIN Users u ON u.id = x.user_id;
    """
    return select_query(query)


# query book by ID
def query_book_id(id):
    query = 'SELECT * FROM Books WHERE id = %d;' % id
    return select_query(query)


# delete book by ID
def delete_book_id(id):
    query = 'DELETE FROM Books WHERE id = %d;' % id
    c = conn.cursor()
    c.execute(query)
    return conn.commit()


# insert book by ISBN and Title
def insert_book(book):
    query = """
        INSERT INTO Books(isbn, title)
        VALUES ('%s', '%s')
    """ % (book.get('isbn'), book.get('title'))
    c = conn.cursor()
    c.execute(query)
    conn.commit()
    return c.lastrowid


# query book by ISBN
def query_book_isbn(isbn):
    query = "SELECT * FROM Books WHERE isbn = '%s';" % isbn
    return select_query(query)


# check ISBN
def check_isbn(isbn):
    if not isbn.isnumeric():
        return False
    if len(isbn) == 10 or len(isbn) == 13:
        return True
    return False


# checkout book by IDs
def checkout_book_id(user_id, book_id):
    now_date = datetime.datetime.now().strftime('%Y-%m-%d')
    due_date = (datetime.datetime.now() + datetime.timedelta(days=14)).strftime('%Y-%m-%d')
    # use the following to similate overdue books:
    # due_date = (datetime.datetime.now() - datetime.timedelta(days=21)).strftime('%Y-%m-%d')
    query = """
        INSERT INTO Borrowed(user_id, book_id, date_out, date_due)
        VALUES (%d, %d, '%s', '%s');
    """ % (user_id, book_id, now_date, due_date)
    c = conn.cursor()
    c.execute(query)
    return conn.commit()


# return book by IDs
def return_book_id(user_id, book_id):
    query = """
        DELETE FROM Borrowed
         WHERE user_id = %d AND book_id = %s;
    """ % (user_id, book_id)
    c = conn.cursor()
    c.execute(query)
    return conn.commit()


# query borrowed book by User ID
def query_borrowed(user_id):
    query = """
        SELECT b.id,
               b.isbn AS ISBN,
               b.title AS Title,
               x.date_out AS 'Checked Out',
               x.date_due AS 'Due Date'
          FROM Borrowed x
         INNER JOIN Books b ON b.id = x.book_id
         INNER JOIN Users u ON u.id = x.user_id
         WHERE u.id = %d;
    """ % user_id
    return select_query(query)


# query overdue books by
def query_overdue():
    query = """
        SELECT u.id AS user_id,
               u.name AS user_name,
               b.id AS book_id,
               b.isbn AS ISBN,
               b.title AS Title,
               x.date_out AS 'Checked Out',
               x.date_due AS 'Due Date'
          FROM Borrowed x
         INNER JOIN Books b ON b.id = x.book_id
         INNER JOIN Users u ON u.id = x.user_id
         WHERE x.date_due <= strftime('%Y-%m-%d', 'now');
    """
    return select_query(query)


# check if user has overdue books
def check_overdue(user_id):
    overdue = query_overdue()
    for book in overdue:
        if user_id == book.get('user_id'):
            return True
    return False


# query available books
def query_available():
    query = """
        SELECT isbn AS ISBN, title AS Title
          FROM Books
         WHERE id NOT IN (
            SELECT book_id FROM Borrowed
         );
    """
    return select_query(query)


# verify that user has borrowed book, return number of borrowed books
def verify_borrowed(user_id, book_id):
    borrowed = query_borrowed(user_id)
    for book in borrowed:
        if book_id == book.get('id'):
            return True, borrowed
    return False, borrowed


@app.route("/spec")
def spec():
    library = swagger(app)
    library.update({
        'info': {
            'version': '1.0',
            'title': 'Library API',
        },
    })
    return jsonify(library)


@app.route("/librarian/book", methods=["POST"])
def add_book():
    '''
    Add Book by ISBN
    ---
    parameters:
      - in: header
        name: user
        required: true
        default: 'Dewey'
        description: Name of user
      - in: body
        name: body
        schema:
          id: Book
          required:
            - isbn
            - title
          properties:
            isbn:
              type: string
              description: ISBN of Book
            title:
              type: string
              description: Title of Book
    responses:
      200:
        description: Book added successfully
      401:
        description: User does not have librarian privileges
      403:
        description: Book already exists
      406:
        description: ISBN invalid
    '''
    user = request.headers.get('user')
    if not check_user(user, True):
        return {'Error': 'User (%s) does not have librarian privileges' % user}, 401
    isbn = request.json.get('isbn')
    if not check_isbn(isbn):
        return {'Error': 'ISBN (%s) is invalid, must be 10 or 13 numbers' % isbn}, 406
    if query_book_isbn(isbn):
        return {'Error': 'ISBN (%s) already exists in library' % isbn}, 403
    book_id = insert_book(request.json)
    if book_id:
        return {'Success': 'ISBN (%s) added to library as Book (%d)' % (isbn, book_id)}, 200
    return {'Error': 'Failed to insert ISBN (%s)' % isbn}, 500


@app.route("/librarian/book/<int:book_id>", methods=["DELETE"])
def remove_book(book_id):
    '''
    Delete Book by ID
    ---
    parameters:
      - in: header
        name: user
        required: true
        default: 'Dewey'
        description: Name of user
      - in: path
        name: book_id
        required: true
        description: ID of book (see /librarian/catalog)
    responses:
      200:
        description: Book deleted successfully
      401:
        description: User does not have librarian privileges
      404:
        description: Book does not exist
    '''
    user = request.headers.get('user')
    if not check_user(user, True):
        return {'Error': 'User (%s) does not have librarian privileges' % user}, 401
    if not query_book_id(book_id):
        return {'Error': 'Book (%d) does not exist in library' % book_id}, 404
    error = delete_book_id(book_id)
    if not error:
        return {'Success': 'Book (%d) deleted successfully' % book_id}, 200
    return {'Error': 'Failed to delete book (%d)' % book_id}, 500


@app.route("/librarian/catalog", methods=["GET"])
def list_catalog():
    '''
    List All Books
    ---
    parameters:
      - in: header
        name: user
        required: true
        default: 'Scrooge'
        description: Name of user
      - in: query
        name: details
        description: Display checkout details of each book
    responses:
      200:
        description: List of all books
      401:
        description: User does not have librarian privileges
      404:
        description: No books found
    '''
    user = request.headers.get('user')
    if not check_user(user, True):
        return {'Error': 'User (%s) does not have librarian privileges' % user}, 401
    catalog = query_books()
    if not catalog:
        return {'Error': 'Library currently has no books'}, 404
    if request.args.get('details'):
        return jsonify(query_details())
    return jsonify(catalog)


@app.route("/librarian/overdue", methods=["GET"])
def list_overdue():
    '''
    List Overdue Books
    ---
    parameters:
      - in: header
        name: user
        required: true
        default: 'Scrooge'
        description: Name of user
    responses:
      200:
        description: List of overdue books
      401:
        description: User does not have librarian privileges
    '''
    user = request.headers.get('user')
    if not check_user(user, True):
        return {'Error': 'User (%s) does not have librarian privileges' % user}, 401
    return jsonify(query_overdue())


@app.route("/user/checkout/<int:book_id>", methods=["GET"])
def checkout_book(book_id):
    '''
    Checkout Book by ID
    ---
    parameters:
      - in: header
        name: user
        required: true
        default: 'Dewey'
        description: Name of user
      - in: path
        name: book_id
        required: true
        description: ID of book (see /user/available)
    responses:
      200:
        description: Book successfully checked out
      401:
        description: User not valid
      403:
        description: User cannot check out
      404:
        description: Book does not exist
      423:
        description: Book already checked out
    '''
    user = request.headers.get('user')
    user_id = check_user(user, False)
    if not user_id:
        return {'Error': 'User (%s) does not have library card' % user}, 401
    if not query_book_id(book_id):
        return {'Error': 'Book (%d) does not exist in library' % book_id}, 404
    borrowed, books = verify_borrowed(user_id, book_id)
    if borrowed:
        return {'Error': 'Book (%d) was already checked out by User (%s)' % (book_id, user)}, 423
    if len(books) >= max_books:
        return {'Error': 'User (%s) already has max books (%d) checked out' % (user, max_books)}, 403
    if check_overdue(user_id):
        return {'Error': 'User (%s) has overdue book(s) and cannot check out' % (user)}, 403
    error = checkout_book_id(user_id, book_id)
    if not error:
        return {'Success': 'User (%s) has checked out Book (%d)' % (user, book_id)}, 200
    return {'Error': 'Failed to checkout book (%d)' % book_id}, 500


@app.route("/user/available", methods=["GET"])
def list_available():
    '''
    List Available Books
    ---
    parameters:
      - in: header
        name: user
        required: true
        default: 'Dewey'
        description: Name of user
    responses:
      200:
        description: List of all available books
      401:
        description: User not valid
      404:
        description: No books found
    '''
    user = request.headers.get('user')
    if not check_user(user, False):
        return {'Error': 'User (%s) does not have library card' % user}, 401
    avail = query_available()
    if not avail:
        return {'Error': 'All library books appear to be checked out'}, 404
    return jsonify(avail)


@app.route("/user/return/<int:book_id>", methods=["GET"])
def return_book(book_id):
    '''
    Return Book by ID
    ---
    parameters:
      - in: header
        name: user
        required: true
        default: 'Dewey'
        description: Name of user
      - in: path
        name: book_id
        required: true
        description: ID of book (see /user/borrowed)
    responses:
      200:
        description: Book returned
      401:
        description: User not valid
      403:
        description: Book not checked out
      404:
        description: Book does not exist
    '''
    user = request.headers.get('user')
    user_id = check_user(user, False)
    if not user_id:
        return {'Error': 'User (%s) does not have library card' % user}, 401
    if not query_book_id(book_id):
        return {'Error': 'Book (%d) does not exist in library' % book_id}, 404
    borrowed, books = verify_borrowed(user_id, book_id)
    if not borrowed:
        return {'Error': 'Book (%d) was not checked out by User (%s)' % (book_id, user)}, 403
    error = return_book_id(user_id, book_id)
    if not error:
        return {'Success': 'User (%s) has returned Book (%d)' % (user, book_id)}, 200
    return {'Error': 'Failed to return book (%d)' % book_id}, 500


@app.route("/user/borrowed", methods=["GET"])
def list_borrowed():
    '''
    List Borrowed Books
    ---
    parameters:
      - in: header
        name: user
        required: true
        default: 'Dewey'
        description: Name of user
    responses:
      200:
        description: List of all borrowed books
      401:
        description: User not valid
    '''
    user = request.headers.get('user')
    user_id = check_user(user, False)
    if not user_id:
        return {'Error': 'User (%s) does not have library card' % user}, 401
    return jsonify(query_borrowed(user_id))


if __name__ == '__main__':
    SWAGGER_URL = '/api/docs'
    API_URL = '/spec'
    swaggerui_blueprint = get_swaggerui_blueprint(
        SWAGGER_URL,
        API_URL,
        config={'app_name': 'Library API'},
    )
    app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)
    app.run(debug=True, host='0.0.0.0')
