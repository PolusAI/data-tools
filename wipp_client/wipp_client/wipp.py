#!/usr/bin/env python
# -*- coding: utf-8 -*-

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


class WippEntity:
    """Class for holding generic WIPP Entity"""

    def __init__(self, json):
        self.json = json


class WippAbstractCollection(WippEntity):
    """Class for holding generic WIPP Collection"""

    def __init__(self, json):
        super().__init__(json)

        self.id = self.json.get("id", None)
        self.name = self.json["name"]
        self.creationDate = self.json.get("creationDate", None)
        self.locked = self.json.get(
            "locked", None
        )  # Only present in the old version of the API
        self.sourceJob = self.json.get("sourceJob", None)

        # Only supported in the new version of the API
        # self.owner = self.json["owner"]
        # self.publiclyShared = self.json["publiclyShared"]

    def __str__(self):
        return f"{self.id}\t{self.name}"

    def __repr__(self):
        return str(self)


class WippImageCollection(WippAbstractCollection):
    """Class for holding WIPP Image Collection"""

    def __init__(self, json):
        super().__init__(json)

        self.imagesTotalSize = self.json["imagesTotalSize"]
        self.importMethod = self.json["importMethod"]
        self.metadataFilesTotalSize = self.json["metadataFilesTotalSize"]
        self.notes = self.json["notes"]
        self.numberImportingImages = self.json["numberImportingImages"]
        self.numberOfImages = self.json["numberOfImages"]
        self.numberOfImportErrors = self.json["numberOfImportErrors"]
        self.numberOfMetadataFiles = self.json["numberOfMetadataFiles"]
        self.pattern = self.json["pattern"]
        self.sourceCatalog = self.json["sourceCatalog"]

        self.images = []

    def __iter__(self):
        for image in self.images:
            yield image


class WippImage(WippEntity):
    """Class for holding WIPP Image"""

    def __init__(self, json):
        super().__init__(json)

        self.fileName = self.json["fileName"]
        self.originalFileName = self.json["originalFileName"]
        self.fileSize = self.json["fileSize"]
        self.importing = self.json["importing"]
        self.importError = self.json["importError"]

    def __str__(self):
        return f"{self.fileName}\t{self.fileSize}"

    def __repr__(self):
        return str(self)


class WippCsvCollection(WippAbstractCollection):
    """Class for holding generic WIPP Collection"""

    def __init__(self, json):
        super().__init__(json)

        self.csvTotalSize = self.json.get("csvTotalSize", None)
        self.numberImportingCsv = self.json.get("numberImportingCsv", None)
        self.numberOfCsvFiles = self.json.get("numberOfCsvFiles", None)
        self.numberOfImportErrors = self.json.get("numberOfImportErrors", None)

        self.csvs = []

    def __iter__(self):
        for csv in self.csvs:
            yield csv


class WippCsv(WippEntity):
    """Class for holding WIPP CSV"""

    def __init__(self, json):
        super().__init__(json)

        self.fileName = self.json["fileName"]
        self.originalFileName = self.json["originalFileName"]
        self.fileSize = self.json["fileSize"]
        self.importing = self.json["importing"]
        self.importError = self.json["importError"]

    def __str__(self):
        return f"{self.fileName}\t{self.fileSize}"

    def __repr__(self):
        return str(self)


class WippGenericDataCollection(WippAbstractCollection):
    """Class for holding generic WIPP Collection"""

    def __init__(self, json):
        super().__init__(json)

        self.description: str = self.json["description"]
        self.fileTotalSize: int = self.json["fileTotalSize"]
        self.metadata: str = self.json["metadata"]
        self.numberOfFiles: int = self.json["numberOfFiles"]
        self.type: str = self.json["type"]

        self.data = []

    def __iter__(self):
        for data in self.data:
            yield data


class WippGenericDataFile(WippEntity):
    """Class for holding WIPP Generic Data File"""

    def __init__(self, json):
        super().__init__(json)

        self.fileName: str = self.json["fileName"]
        self.originalFileName: str = self.json["originalFileName"]
        self.fileSize: int = self.json["fileSize"]

    def __str__(self):
        return f"{self.fileName}\t{self.fileSize}"

    def __repr__(self):
        return str(self)


class WippPlugin(WippEntity):
    """Class for holding WIPP Plugin"""

    def __init__(self, json):
        super().__init__(json)

        self.author: str = self.json["author"]
        self.citation: str = self.json["citation"]
        self.container_id: str = self.json["containerId"]
        self.creation_date: str = self.json.get("creationDate", None)
        self.description: str = self.json["description"]
        self.id: str = self.json.get("id", None)
        self.inputs: list = self.json["inputs"]
        self.institution: str = self.json["institution"]
        self.name: str = self.json["name"]
        self.outputs: list = self.json["outputs"]
        self.repository: str = self.json["repository"]
        self.title: str = self.json["title"]
        self.ui: list = self.json["ui"]
        self.version: str = self.json["version"]
        self.website: str = self.json["website"]

    def __str__(self):
        return f"{self.id}\t{self.name}\t{self.version}"

    def __repr__(self):
        return str(self)


# TODO: Add more classes describing WIPP entities


class MissingEnvironmentVariable(Exception):
    pass


class Wipp:
    """Class for interfacing with WIPP API"""

    def __init__(self):
        """WIPP client class constructor
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

        api_is_live = self.check_api_is_live()
        if api_is_live["code"] != 200:
            raise Exception(api_is_live["data"])

        # Authorization headers for Keycloak
        self._auth_headers = None

    def __str__(self):
        return f"WIPP API @ {self.api_route}"

    def __repr__(self):
        return str(self)

    @property
    def auth_headers(self):
        return self._auth_headers

    @auth_headers.setter
    def auth_headers(self, keycloak_token):
        self._auth_headers = {"Authorization": f"Bearer {keycloak_token}"}

    def build_request_url(
        self,
        plural: str,
        path_prefix: Union[str, bytes, os.PathLike] = "",
        path_suffix: Union[str, bytes, os.PathLike] = "",
        extra_query: dict = {},
    ):
        """
        Build request URL for WIPP API
        
        Keyword arguments:
        plural -- plural of the resource (such as "imagesCollections")
        path_suffix -- extra path to be added to the request URL (such as "search/findByNameContainingIgnoreCase")
        extra_query -- extra query parameters to be added to the request URL (such as {"name": "test"})
        """
        parsed_url = self.parsed_api_route

        parsed_query = parse_qs(parsed_url.query)
        parsed_query.update(extra_query)

        parsed_url = parsed_url._replace(
            path=os.path.join(parsed_url.path, path_prefix, plural, path_suffix),
            query=urlencode(parsed_query, doseq=True),
        )

        return urlunparse(parsed_url)

    def check_api_is_live(self) -> dict:
        """Check if WIPP API is live"""
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

    def get_entities_summary(
        self,
        plural: str,
        path_prefix: Union[str, bytes, os.PathLike] = "",
        path_suffix: Union[str, bytes, os.PathLike] = "",
        extra_query: dict = {},
    ) -> tuple:

        """Get tuple with WIPP entities' number of pages and page size"""
        r = requests.get(
            self.build_request_url(plural, path_prefix, path_suffix, extra_query),
            headers=self._auth_headers,
        )
        if r.status_code == 200:
            response = r.json()
            total_pages = response["page"]["totalPages"]
            page_size = response["page"]["size"]

            return (total_pages, page_size)

    def get_entities_page(
        self,
        plural: str,
        index: int,
        path_prefix: Union[str, bytes, os.PathLike] = "",
        path_suffix: Union[str, bytes, os.PathLike] = "",
        extra_query: dict = {},
    ) -> list[WippEntity]:
        """Get the page of WIPP Collections

        Keyword arguments:
        index -- page index starting from 0
        """

        r = requests.get(
            self.build_request_url(
                plural, path_prefix, path_suffix, {"page": index} | extra_query
            ),
            headers=self._auth_headers,
        )
        if r.status_code == 200:

            # Fix for inconsistent plural names in CSV
            # See https://github.com/usnistgov/WIPP-backend/issues/176
            # TODO: Remove this when WIPP API is fixed
            key = plural
            if plural == "csv":
                key = "csvs"
            elif plural == "genericFile":
                key = "genericFiles"

            entities_page = r.json()["_embedded"][key]

            # Parse into the base or child class (if implemented for the entity)
            if plural == "imagesCollections":
                return [WippImageCollection(entity) for entity in entities_page]
            elif plural == "images":
                return [WippImage(entity) for entity in entities_page]
            elif plural == "csvCollections":
                return [WippCsvCollection(entity) for entity in entities_page]
            elif plural == "csv":
                return [WippCsv(entity) for entity in entities_page]
            elif plural == "genericDatas":
                return [WippGenericDataCollection(entity) for entity in entities_page]
            elif plural == "genericFile":
                return [WippGenericDataFile(entity) for entity in entities_page]
            elif plural == "plugins":
                return [WippPlugin(entity) for entity in entities_page]
            else:
                return [WippEntity(entity) for entity in entities_page]

    def get_entities_all_pages(
        self,
        plural: str,
        path_prefix: Union[str, bytes, os.PathLike] = "",
        path_suffix: Union[str, bytes, os.PathLike] = "",
        extra_query: dict = {},
    ) -> list[list[WippEntity]]:
        """Get list of all pages of WIPP Image Collections"""

        total_pages, _ = self.get_entities_summary(
            plural, path_prefix, path_suffix, extra_query
        )
        return [
            self.get_entities_page(plural, page, path_prefix, path_suffix, extra_query)
            for page in range(total_pages)
        ]

    def get_entities(
        self,
        plural: str,
        path_prefix: Union[str, bytes, os.PathLike] = "",
        path_suffix: Union[str, bytes, os.PathLike] = "",
        extra_query: dict = {},
    ) -> list[WippEntity]:
        """Get list of all available WIPP Image Collection in JSON format"""

        return [
            entity
            for entity in sum(
                self.get_entities_all_pages(
                    plural, path_prefix, path_suffix, extra_query
                ),
                [],
            )
        ]

    def create_entity(
        self,
        plural: str,
        entity: WippEntity,
        path_prefix: Union[str, bytes, os.PathLike] = "",
        path_suffix: Union[str, bytes, os.PathLike] = "",
        extra_query: dict = {},
    ) -> WippEntity:
        """Create a WIPP entity

        Keyword arguments:
        entity -- the entity object to be created
        """

        r = requests.post(
            self.build_request_url(plural, path_prefix, path_suffix, extra_query),
            headers=self._auth_headers,
            json=entity.json,
        )
        if r.status_code == 201:
            if plural == "imagesCollections":
                return WippImageCollection(r.json())
            elif plural == "images":
                return WippImage(r.json())
            elif plural == "csvCollections":
                return WippCsvCollection(r.json())
            elif plural == "csv":
                return WippCsv(r.json())
            elif plural == "genericDatas":
                return WippGenericDataCollection(r.json())
            elif plural == "genericFile":
                return WippGenericDataFile(r.json())
            elif plural == "plugins":
                return WippPlugin(r.json())
            else:
                return WippEntity(r.json())
        else:
            print(r)
            print(r.text)
            return None

    ### Query methods
    # Specialized methods for entities
    def get_csv_collections(self) -> list[WippEntity]:
        """Get list of all available WIPP Csv Collection objects"""
        return self.get_entities("csvCollections")

    def get_generic_datas(self) -> list[WippEntity]:
        """Get list of all available WIPP Generic Data objects"""
        return self.get_entities("genericDatas")

    def get_image_collections(self) -> list[WippImageCollection]:
        """Get list of all available WIPP Image Collection objects"""
        return self.get_entities("imagesCollections")

    def get_jobs(self) -> list[WippEntity]:
        """Get list of all available WIPP Job objects"""
        return self.get_entities("jobs")

    def get_notebooks(self) -> list[WippEntity]:
        """Get list of all available WIPP Notebook objects"""
        return self.get_entities("notebooks")

    def get_plugins(self) -> list[WippEntity]:
        """Get list of all available WIPP Plugin objects"""
        return self.get_entities("plugins")

    def get_pyramid_annotations(self) -> list[WippEntity]:
        """Get list of all available WIPP Pyramid Annotation objects"""
        return self.get_entities("pyramidAnnotations")

    def get_pyramids(self) -> list[WippEntity]:
        """Get list of all available WIPP Pyramid objects"""
        return self.get_entities("pyramids")

    def get_stitching_vectors(self) -> list[WippEntity]:
        """Get list of all available WIPP Stitching Vector objects"""
        return self.get_entities("stitchingVectors")

    def get_tensorboard_logs(self) -> list[WippEntity]:
        """Get list of all available WIPP Tensorboard Log objects"""
        return self.get_entities("tensorboardLogs")

    def get_tensorflow_models(self) -> list[WippEntity]:
        """Get list of all available WIPP Tensorflow Model objects"""
        return self.get_entities("tensorflowModels")

    def get_visualizations(self) -> list[WippEntity]:
        """Get list of all available WIPP Visualization objects"""
        return self.get_entities("visualizations")

    def get_workflows(self) -> list[WippEntity]:
        """Get list of all available WIPP Workflow objects"""
        return self.get_entities("workflows")

    # Search methods
    def search_csv_collections(self, name) -> list[WippEntity]:
        """Get list of all found WIPP CSV Collection objects
        
        Keyword arguments:
        name -- string to search in CSV Collection names
        """
        return self.get_entities(
            "csvCollections",
            path_suffix="search/findByNameContainingIgnoreCase",
            extra_query={"name": name},
        )

    def search_generic_datas(self, name) -> list[WippEntity]:
        """Get list of all found WIPP Generic Data objects
        
        Keyword arguments:
        name -- string to search in Generic Data names
        """
        return self.get_entities(
            "genericDatas",
            path_suffix="search/findByNameContainingIgnoreCase",
            extra_query={"name": name},
        )

    def search_image_collections(self, name) -> list[WippImageCollection]:
        """Get list of all found WIPP Image Collection objects
        
        Keyword arguments:
        name -- string to search in WIPP Image Collections names
        """
        return self.get_entities(
            "imagesCollections",
            path_suffix="search/findByNameContainingIgnoreCase",
            extra_query={"name": name},
        )

    def search_jobs(self, name) -> list[WippEntity]:
        """Get list of all found WIPP Job objects
        
        Keyword arguments:
        name -- string to search in WIPP Job names
        """
        return self.get_entities(
            "jobs",
            path_suffix="search/findByNameContainingIgnoreCase",
            extra_query={"name": name},
        )

    def search_notebooks(self, name) -> list[WippEntity]:
        """Get list of all found WIPP Notebook objects
        
        Keyword arguments:
        name -- string to search in WIPP Notebook names
        """
        return self.get_entities(
            "notebooks",
            path_suffix="search/findByNameContainingIgnoreCase",
            extra_query={"name": name},
        )

    def search_plugins(self, name) -> list[WippEntity]:
        """Get list of all found WIPP Plugin objects
        
        Keyword arguments:
        name -- string to search in Csv Collection names
        """
        return self.get_entities(
            "plugins",
            path_suffix="search/findByNameContainingIgnoreCase",
            extra_query={"name": name},
        )

    def search_pyramid_annotations(self, name: str) -> list[WippEntity]:
        """Get list of all found WIPP Pyramid Annotation objects
        
        Keyword arguments:
        name -- string to search in Pyramid Annotations names
        """
        return self.get_entities(
            "pyramidAnnotations",
            path_suffix="search/findByNameContainingIgnoreCase",
            extra_query={"name": name},
        )

    def search_pyramids(self, name: str) -> list[WippEntity]:
        """Get list of all found WIPP Pyramid objects
        
        Keyword arguments:
        name -- string to search in Pyramids names
        """
        return self.get_entities(
            "pyramids",
            path_suffix="search/findByNameContainingIgnoreCase",
            extra_query={"name": name},
        )

    def search_pyramids(self, name: str) -> list[WippEntity]:
        """Get list of all found WIPP Pyramid objects
        
        Keyword arguments:
        name -- string to search in Pyramids names
        """
        return self.get_entities(
            "pyramids",
            path_suffix="search/findByNameContainingIgnoreCase",
            extra_query={"name": name},
        )

    def search_stitching_vectors(self, name: str) -> list[WippEntity]:
        """Get list of all found WIPP Stitching Vector objects
        
        Keyword arguments:
        name -- string to search in Stitching Vectors names
        """
        return self.get_entities(
            "stitchingVectors",
            path_suffix="search/findByNameContainingIgnoreCase",
            extra_query={"name": name},
        )

    def search_tensorboard_logs(self, name: str) -> list[WippEntity]:
        """Get list of all found WIPP Tensorboard Log objects
        
        Keyword arguments:
        name -- string to search in Tensorboard Logs names
        """
        return self.get_entities(
            "tensorboardLogs",
            path_suffix="search/findByNameContainingIgnoreCase",
            extra_query={"name": name},
        )

    def search_tensorflow_models(self, name: str) -> list[WippEntity]:
        """Get list of all found WIPP Tensorflow Model objects
        
        Keyword arguments:
        name -- string to search in Tensorflow Models names
        """
        return self.get_entities(
            "tensorflowModels",
            path_suffix="search/findByNameContainingIgnoreCase",
            extra_query={"name": name},
        )

    def search_visualizations(self, name: str) -> list[WippEntity]:
        """Get list of all found WIPP Visualization objects
        
        Keyword arguments:
        name -- string to search in Visualizations names
        """
        return self.get_entities(
            "visualizations",
            path_suffix="search/findByNameContainingIgnoreCase",
            extra_query={"name": name},
        )

    def search_workflows(self, name: str) -> list[WippEntity]:
        """Get list of all found WIPP Workflow objects
        
        Keyword arguments:
        name -- string to search in Workflows names
        """
        return self.get_entities(
            "workflows",
            path_suffix="search/findByNameContainingIgnoreCase",
            extra_query={"name": name},
        )

    # Image Collection methods
    def get_image_collections_images(self, collection_id: str) -> list[WippImage]:
        """Get list of all images in a WIPP Image Collection"""
        return self.get_entities(
            "images", path_prefix="imagesCollections/" + collection_id
        )

    # CSV Collection methods
    def create_csv_collection(self, csv_collection: WippCsvCollection):
        """Create a new WIPP CSV Collection
        
        Keyword arguments:
        csv_collection -- WippCsvCollection object to create
        """
        return self.create_entity("csvCollections", csv_collection)

    def get_csv_collections_csv_files(self, collection_id: str) -> list[WippCsv]:
        """Get list of all CSV files in a WIPP CSV Collection"""
        return self.get_entities("csv", path_prefix="csvCollections/" + collection_id)

    # Generic Data methods
    def get_generic_data_files(self, generic_data_id: str) -> list[WippGenericDataFile]:
        """Get list of all files in a WIPP Generic Data"""
        return self.get_entities(
            "genericFile", path_prefix="genericDatas/" + generic_data_id
        )

    # Plugin methods
    def create_plugin(self, plugin: WippPlugin):
        """Create a new WIPP Plugin

        Keyword arguments:
        plugin -- WippPlugin object to create
        """
        return self.create_entity("plugins", plugin)

    def delete_plugin(self, plugin_id: str):
        r = requests.delete(
            self.build_request_url("plugins/" + plugin_id), headers=self._auth_headers
        )
        if r.status_code == 204:
            log.info("Plugin deleted")
