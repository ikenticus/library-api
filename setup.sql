DROP TABLE Books;
CREATE TABLE IF NOT EXISTS Books (
    id integer PRIMARY KEY,
    isbn text NOT NULL,
    title text NOT NULL
);
INSERT INTO Books(isbn, title) VALUES
    ('9781593079789', 'The Umbrella Academy Vol 1: The Apocalypse Suite'),
    ('9781595823458', 'The Umbrella Academy Vol 2: Dallas'),
    ('9781506711423', 'The Umbrella Academy Vol 3: Hotel Oblivion');

DROP TABLE Roles;
CREATE TABLE IF NOT EXISTS Roles (
    id integer PRIMARY KEY,
    role text NOT NULL
);
INSERT INTO Roles(role) VALUES('librarian'),('user');

DROP TABLE Users;
CREATE TABLE IF NOT EXISTS Users (
    id integer PRIMARY KEY,
    name text NOT NULL,
    role_id integer NOT NULL,
    FOREIGN KEY (role_id) REFERENCES Roles (id)
);
INSERT INTO Users(name, role_id)
VALUES ('Scrooge', 1),('Huey', 2),('Louie', 2),('Dewey', 2);

CREATE TABLE IF NOT EXISTS Borrowed (
    book_id integer,
    user_id integer,
    date_out date,
    date_due date,
    PRIMARY KEY (book_id, user_id),
    FOREIGN KEY (book_id) REFERENCES Books (id),
    FOREIGN KEY (user_id) REFERENCES Users (id)
);
