import json
import sqlite3
import sys

from flask import Flask, request, jsonify
from flask_swagger import swagger
from flask_swagger_ui import get_swaggerui_blueprint

app = Flask(__name__)
dbpath = 'data.db'
conn = sqlite3.connect(dbpath, check_same_thread=False)

'''
inputs = (
    'customer_id',
    'first_name',
    'last_name',
    'address',
    'state',
    'zipcode',
    'status',
    'product_id',
    'product_name',
    'amount',
    'date_time'
)


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


# various database functions for customer/product (assumes know data_types)

def insert_customer(row):
    c = conn.cursor()
    query = "INSERT INTO Customer VALUES (%s,'%s','%s','%s','%s',%s);" % row
    c.execute(query)

def insert_product(row):
    c = conn.cursor()
    query = "INSERT INTO Product VALUES ('%s',%s,'%s','%s','%s',%s);" % row
    c.execute(query)

def update_customer(row):
    c = conn.cursor()
    query = "DELETE FROM Customer WHERE id = %s;" % row[0]
    c.execute(query)
    insert_customer(row)

def update_product(row):
    c = conn.cursor()
    query = "DELETE FROM Product WHERE status = '%s' AND id = %s;" % (row[0], row[1])
    c.execute(query)
    insert_product(row)

def check_customer(row):
    exists = query_table('Customer', {'id': row[0]})
    return True if exists else False

def check_product(row):
    exists = query_table('Product', {'id': row[1], 'status': row[0]})
    return True if exists else False

def upsert_customer(row):
    if check_customer(row):
        update_customer(row)
    else:
        insert_customer(row)

def upsert_product(row):
    if check_product(row):
        update_product(row)
    else:
        insert_product(row)

def upsert_db(cols):
    upsert_customer(tuple(cols[:6]))
    upsert_product(tuple(cols[6:] + [cols[0]]))
    conn.commit()


@app.route("/librarian/add", methods=["POST"])
def update_data():
    return jsonify(parse_data(request.data))
'''

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
        SELECT r.role
          FROM Roles r
         INNER JOIN Users u ON u.role_id = r.id
         WHERE u.name = '%s';
    """ % user
    role = select_query(query)
    if librarian and role[0].get('role') == 'librarian':
        return True
    elif not librarian and role:
        return True
    return False

# query all books
def query_books():
    query = 'SELECT * FROM Books;'
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

'''
Librarian Endpoints:
* An endpoint that generates a list of all overdue books.
'''

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
    # if request.args.get('details'):
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
    return {}

'''
User Endpoints:
* An endpoint to check out a book (assume a 2 week checkout period from time of call).  A User can check out any book except when:
  - They currently have 3 checked out books.
  - They are overdue on returning any book.
* An endpoint to return a checked out book to the library
* An endpoint that lists all currently checked out books for that user.
'''

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
    if not check_user(user, False):
        return {'Error': 'User (%s) does not have library card' % user}, 401
    if not query_book_id(book_id):
        return {'Error': 'Book (%d) does not exist in library' % book_id}, 404
    return {}

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
    return {}

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
        description: Book added
      401:
        description: User not valid
      403:
        description: Book not checked out
      404:
        description: Book does not exist
    '''
    user = request.headers.get('user')
    if not check_user(user, False):
        return {'Error': 'User (%s) does not have library card' % user}, 401
    return {}

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
    if not check_user(user, False):
        return {'Error': 'User (%s) does not have library card' % user}, 401
    return {}

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
