# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
2-Way SSL Server
----------------

...
"""

from pyrolab.api import locate_ns, Proxy

with locate_ns(host="localhost") as ns:
    uri = ns.lookup("library")

with Proxy(uri) as catalog:
    books = {
        "The Hobbit": 3,
        "The Lord of the Rings": 2,
        "Harry Potter": 3,
        "The Lightning Thief": 2,
        "C Programming": 2,
    }

    for book, number in books.items():
        catalog.add_book(book, number)

    print("Initial Catalog...")
    print(catalog.get_catalog(), "\n")

    print("Checking out The Hobbit...")
    catalog.checkout("The Hobbit")
    print(catalog.get_catalog(), "\n")

    print("Checkout out two copies of C Programming...")
    catalog.checkout("C Programming", 2)
    print(catalog.get_catalog(), "\n")

    # Check out a book when all books are already checked out
    try:
        print("Checking out when all copies are already checked out...")
        catalog.checkout("C Programming")
    except ValueError as e:
        print(e, "\n")

    # Return a book not in the library's catalog
    try:
        print("Returning out a book not in the catalog...")
        catalog.checkin("Dune")
    except LookupError as e:
        print(e, "\n")

    # Check out a book not in the library's catalog
    try:
        print("Checking out a book not in the catalog...")
        catalog.checkout("Coding for Dummies")
    except LookupError as e:
        print(e)
