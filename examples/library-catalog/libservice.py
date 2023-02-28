# -*- coding: utf-8 -*-
#
# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Library Catalog Service
=======================

A class that implements an example service for a library catalog.
"""

from typing import Dict

from pyrolab.api import Service, behavior, expose



@behavior(instance_mode="single")
@expose
class LibraryCatalog(Service):
    """
    Simulates a library catalog, provides a way to check out and check in books.

    It's a bad library; it doesn't know who checked out the books, or how many
    books are missing from its collection. It just knows how many it has.

    Parameters
    ----------
    catalog : Dict[str, int]
        A dictionary of book titles and their quantities.
    """
    def __init__(self, catalog: Dict[str, int] = {}) -> None:
        self.catalog = catalog

    def get_catalog(self) -> Dict[str, int]:
        """
        Get the current catalog of books and their available quantities.

        Returns
        -------
        catalog : Dict[str, int]
            A dictionary of book titles and their quantities.
        """
        return self.catalog
    
    def checkout(self, title: str, quantity: int = 1) -> None:
        """
        Check out a book title.
        
        Parameters
        ----------
        title : str
            The title of the book to check out.
        quantity : int
            The number of copies to check out (default 1).
        """
        if title not in self.catalog:
            raise LookupError(f"Cannot checkout: Book '{title}' not found.")
        if self.catalog[title] < quantity:
            raise ValueError(f"Cannot checkout: Not enough copies of {title}.")
        self.catalog[title] -= quantity

    def checkin(self, title: str, quantity: int = 1) -> None:
        """
        Check in a book title.
        
        Parameters
        ----------
        title : str
            The title of the book to check in.
        quantity : int
            The number of copies to check in (default 1).
        """
        if title not in self.catalog:
            raise LookupError(f"Cannot checkin: Book '{title}' not found.")
        self.catalog[title] += quantity

    def add_book(self, title: str, quantity: int = 1) -> None:
        """
        Add a book to the catalog.

        Parameters
        ----------
        title : str
            The title of the book to add.
        quantity : int
            The number of copies to add (default 1).
        """
        self.catalog[title] = quantity

    def remove_book(self, title: str) -> None:
        """
        Permanently remove a book from the catalog.

        Parameters
        ----------
        title : str
            The title of the book to remove.
        """
        if title not in self.catalog:
            raise LookupError(f"Cannot remove: Book '{title}' not found.")
        del self.catalog[title]


if __name__ == "__main__":
    # Test the library code outside of the context of pyrolab
    books = {
        "The Hobbit": 3,
        "The Lord of the Rings": 2,
        "Harry Potter": 3,
        "The Lightning Thief": 2,
        "C Programming": 2,
    }

    catalog = LibraryCatalog(books)
    print(catalog.get_catalog())
    
    catalog.checkout("The Hobbit")
    print(catalog.get_catalog())

    catalog.checkout("C Programming", 2)
    print(catalog.get_catalog())

    try:
        catalog.checkout("C Programming")
    except ValueError as e:
        print(e)

    try:
        catalog.checkin("Dune")
    except ValueError as e:
        print(e)

    try: 
        catalog.checkout("Coding for Dummies")
    except ValueError as e:
        print(e)
