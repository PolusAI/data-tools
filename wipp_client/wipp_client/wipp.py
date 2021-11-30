#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Imports should be grouped into:
# Standard library imports
# Related third party imports
# Local application / relative imports
# in that order

# Standard library
import os
import json
import logging
from types import resolve_bases
from typing import Any, Tuple, Union
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

# Third party
import requests

# Relative

###############################################################################

log = logging.getLogger(__name__)

###############################################################################


class WippCollection:
    """Class for holding generic WIPP Collection"""

    def __init__(self, json):
        self.json = json

        self.id = self.json["id"]
        self.name = self.json["name"]

    def __str__(self):
        return f"{self.id}\t{self.name}"

    def __repr__(self):
        return str(self)


class MissingEnvironmentVariable(Exception):
    pass


class Wipp:
    """Class for interfacing with WIPP API"""

    def __init__(self):
        """Wipp class constructor
        Constructor does not take any arguments directly, but rather reads them from environment variables
        """

        try:
            self.api_route = os.environ["WIPP_API_INTERNAL_URL"]
        except KeyError as e:
            raise MissingEnvironmentVariable(
                "WIPP API URL environment variable is not set"
            )

        try:
            self.parsed_api_route = urlparse(self.api_route)
        except:
            raise ValueError("WIPP API URL is not valid")

    def __str__(self):
        return f"WIPP API @ {self.api_route}"

    def __repr__(self):
        return str(self)

    def build_request_url(
        self,
        plural: str,
        extra_path: Union[str, bytes, os.PathLike] = "",
        extra_query: dict = {},
    ):
        parsed_url = self.parsed_api_route

        parsed_query = parse_qs(parsed_url.query)
        parsed_query.update(extra_query)

        parsed_url = parsed_url._replace(
            path=os.path.join(parsed_url.path, plural, extra_path),
            query=urlencode(parsed_query, doseq=True),
        )

        return urlunparse(parsed_url)

    def check_api_is_live(self) -> dict:
        try:
            r = requests.get(self.api_route, timeout=1)
        except:
            return {
                "code": 500,
                "data": "WIPP API is not available",
            }

        if r.status_code == 200:
            if "_links" in r.json():
                return {
                    "code": 200, 
                    "data": "WIPP API is available",
                }

    def get_collections_summary(
        self,
        plural: str,
        extra_path: Union[str, bytes, os.PathLike] = "",
        extra_query: dict = {},
    ) -> tuple:
        """Get tuple with WIPP Collections' number of pages and page size"""

        r = requests.get(self.build_request_url(plural, extra_path, extra_query))
        if r.status_code == 200:
            response = r.json()
            total_pages = response["page"]["totalPages"]
            page_size = response["page"]["size"]

            return (total_pages, page_size)

    def get_collections_page(
        self,
        plural: str,
        index: int,
        extra_path: Union[str, bytes, os.PathLike] = "",
        extra_query: dict = {},
    ) -> tuple:
        """Get the page of WIPP Collections

        Keyword arguments:
        index -- page index starting from 0
        """

        r = requests.get(
            self.build_request_url(plural, extra_path, {"page": index} | extra_query)
        )
        if r.status_code == 200:
            collections_page = r.json()["_embedded"][plural]
            return [WippCollection(collection) for collection in collections_page]

    def get_collections_all_pages(
        self,
        plural: str,
        extra_path: Union[str, bytes, os.PathLike] = "",
        extra_query: dict = {},
    ) -> list:
        """Get list of all pages of WIPP Image Collections"""
        total_pages, _ = self.get_collections_summary(plural, extra_path, extra_query)
        return [
            self.get_collections_page(plural, page, extra_path, extra_query)
            for page in range(total_pages)
        ]

    def get_collections(
        self,
        plural: str,
        extra_path: Union[str, bytes, os.PathLike] = "",
        extra_query: dict = {},
    ) -> list:
        """Get list of all available WIPP Image Collection in JSON format"""
        return [
            collection
            for collection in sum(
                self.get_collections_all_pages(plural, extra_path, extra_query), []
            )
        ]

    # # Specialized methods for specific collection types

    def get_image_collections(self) -> list[dict]:
        """Get list of all available WIPP Image Collections in dictionary format"""
        return self.get_collections("imagesCollections")

    def get_csv_collections(self) -> list[dict]:
        """Get list of all available WIPP Csv Collections in dictionary format"""
        return self.get_collections("csvCollections")

    def get_plugins(self) -> list[dict]:
        """Get list of all available WIPP Plugins in dictionary format"""
        return self.get_collections("plugins")

    def search_image_collections(self, name) -> list[dict]:
        """Get list of all found WIPP Image Collection in dictionary format
        
        Keyword arguments:
        name -- string to search in WIPP Image Collections names
        """
        return self.get_collections("imagesCollections", "search/findByNameContainingIgnoreCase", {"name": name})
    
    def search_csv_collections(self, name):
        """Get list of all found WIPP Csv Collections in dictionary format
        
        Keyword arguments:
        name -- string to search in Csv Collection names
        """
        return self.get_collections("csvCollections", "search/findByNameContainingIgnoreCase", {"name": name})
    
    def search_plugins(self, name):
        """Get list of all found WIPP Plugins in dictionary format
        
        Keyword arguments:
        name -- string to search in Csv Collection names
        """
        return self.get_collections("plugins", "search/findByNameContainingIgnoreCase", {"name": name})