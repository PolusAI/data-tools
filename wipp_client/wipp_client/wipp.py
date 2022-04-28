#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Standard library
import os
import json
import logging
from types import resolve_bases
from datetime import datetime
from typing import Any, List, Tuple, Union, Optional
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

# Third party
import requests
from pydantic import BaseModel

# Relative

###############################################################################

log = logging.getLogger(__name__)


def snake_case_to_lower_camel_case(string: str) -> str:
    words = list(filter(None, string.split("_")))
    return words[0] + "".join(word.capitalize() for word in words[1:])


###############################################################################


class WippEntity(BaseModel):
    """Class for holding generic WIPP Entity
    When dict() or json() is need in WIPP format, call
    .dict(by_alias=True)
    .json(by_alias=True)
    """

    class Config:
        # Automatically convert lowerCamelCase from WIPP JSONs to snake_case in pydantic models
        alias_generator = snake_case_to_lower_camel_case


class WippAbstractCollection(WippEntity):
    id: Optional[str]
    name: str
    creation_date: Optional[datetime]
    locked: Optional[bool]
    source_job: Optional[str]
    # Only supported in the new version of the API
    # owner: str
    # publicly_shared: bool
    """Class for holding generic WIPP Collection"""

    def __str__(self):
        return f"{self.id}\t{self.name}"

    def __repr__(self):
        return str(self)


class WippImageCollection(WippAbstractCollection):
    images_total_size: Optional[int]
    import_method: Optional[str]
    metadata_files_total_size: Optional[int]
    notes: Optional[str]
    number_importing_images: Optional[int]
    number_of_images: Optional[int]
    number_of_import_errors: Optional[int]
    number_of_metadata_files: Optional[int]
    pattern: Optional[str]
    source_catalog: Optional[str]
    """Class for holding WIPP Image Collection"""

    def __iter__(self):
        for image in self.images:
            yield image


class WippImage(WippEntity):
    file_name: str
    original_file_name: Optional[str]
    file_size: int
    importing: Optional[bool]
    import_error: Optional[str]
    """Class for holding WIPP Image"""

    def __str__(self):
        return f"{self.file_name}\t{self.file_size}"

    def __repr__(self):
        return str(self)


class WippCsvCollection(WippAbstractCollection):
    csv_total_size: Optional[int]
    number_importing_csv: Optional[int]
    number_of_csv_files: Optional[int]
    number_of_import_errors: Optional[int]
    """Class for holding generic WIPP Collection"""

    def __iter__(self):
        for csv in self.csvs:
            yield csv


class WippCsv(WippEntity):
    file_name: str
    original_file_name: Optional[str]
    file_size: int
    importing: Optional[bool]
    import_error: Optional[str]
    """Class for holding WIPP CSV"""

    def __str__(self):
        return f"{self.fileName}\t{self.fileSize}"

    def __repr__(self):
        return str(self)


class WippGenericDataCollection(WippAbstractCollection):
    description: Optional[str]
    file_total_size: Optional[int]
    metadata: Optional[str]
    number_of_files: Optional[int]
    type: Optional[str]
    """Class for holding generic WIPP Collection"""

    def __iter__(self):
        for data in self.data:
            yield data


class WippGenericDataFile(WippEntity):
    file_name: str
    original_file_name: Optional[str]
    file_size: int
    """Class for holding WIPP Generic Data File"""

    def __str__(self):
        return f"{self.file_name}\t{self.file_size}"

    def __repr__(self):
        return str(self)


class WippPlugin(WippEntity):
    author: Optional[str]
    citation: Optional[str]
    container_id: str
    creation_date: Optional[datetime]
    description: str
    id: Optional[str]
    inputs = list
    institution: Optional[str]
    name: str
    outputs: List
    repository: Optional[str]
    title: str
    ui: list
    version: str
    website: Optional[str]
    """Class for holding WIPP Plugin"""

    def __str__(self):
        return f"{self.id}\t{self.name}\t{self.version}"

    def __repr__(self):
        return str(self)


# TODO: Add more classes describing WIPP entities


# Exception classes
class MissingEnvironmentVariable(Exception):
    pass


class WippAuthenticationError(Exception):
    def __init__(self, message, errors):
        super().__init__(message)
        log.error(
            "Authentication failed. Please provide a valid Keycloak token. If you have a Keycloak token, you might need to renew it"
        )


class WippForbiddenError(Exception):
    def __init__(self, message, errors):
        super().__init__(message)
        log.error("You are not authorized to access this resource")


class WippNotFoundError(Exception):
    def __init__(self, message, errors):
        super().__init__(message)
        log.error("The requested resource was not found")


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
                return [WippImageCollection(**entity) for entity in entities_page]
            elif plural == "images":
                return [WippImage(**entity) for entity in entities_page]
            elif plural == "csvCollections":
                return [WippCsvCollection(**entity) for entity in entities_page]
            elif plural == "csv":
                return [WippCsv(**entity) for entity in entities_page]
            elif plural == "genericDatas":
                return [WippGenericDataCollection(**entity) for entity in entities_page]
            elif plural == "genericFile":
                return [WippGenericDataFile(**entity) for entity in entities_page]
            elif plural == "plugins":
                return [WippPlugin(**entity) for entity in entities_page]
            else:
                return [WippEntity(**entity) for entity in entities_page]

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
        """Get list of all available WIPP entities"""

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
            json=entity.dict(by_alias=True),
        )
        if r.status_code == 201:
            entity = r.json()
            log.info(f"Created {plural}: {entity['name']}")
            if plural == "imagesCollections":
                return WippImageCollection(**entity)
            elif plural == "images":
                return WippImage(**entity)
            elif plural == "csvCollections":
                return WippCsvCollection(**entity)
            elif plural == "csv":
                return WippCsv(**entity)
            elif plural == "genericDatas":
                return WippGenericDataCollection(**entity)
            elif plural == "genericFile":
                return WippGenericDataFile(**entity)
            elif plural == "plugins":
                return WippPlugin(**entity)
            else:
                return WippEntity(**entity)
        elif r.status_code == 401:
            raise WippAuthenticationError()
        elif r.status_code == 403:
            raise WippForbiddenError()
        elif r.status_code == 404:
            raise WippNotFoundError()
        else:
            log.error(r)
            log.error(r.text)
            return None

    def delete_entity(
        self,
        plural: str,
        entity_id: str,
        path_prefix: Union[str, bytes, os.PathLike] = "",
        extra_query: dict = {},
    ) -> None:
        r = requests.delete(
            self.build_request_url(plural, path_prefix, entity_id, extra_query),
            headers=self._auth_headers,
        )
        if r.status_code == 200 or r.status_code == 204:
            log.info(f"Deleted {plural} {entity_id}")
            return None

    ### Query methods
    # Specialized methods for entities
    def get_csv_collections(self) -> list[WippCsvCollection]:
        """Get list of all available WIPP Csv Collection objects"""
        return self.get_entities("csvCollections")

    def get_generic_datas(self) -> list[WippGenericDataCollection]:
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

    def get_plugins(self) -> list[WippPlugin]:
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
    def search_csv_collections(self, name) -> list[WippCsvCollection]:
        """Get list of all found WIPP CSV Collection objects

        Keyword arguments:
        name -- string to search in CSV Collection names
        """
        return self.get_entities(
            "csvCollections",
            path_suffix="search/findByNameContainingIgnoreCase",
            extra_query={"name": name},
        )

    def search_generic_datas(self, name) -> list[WippGenericDataCollection]:
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

    def search_plugins(self, name) -> list[WippPlugin]:
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
    def create_image_collection(
        self, image_collection: WippImageCollection
    ) -> WippImageCollection:
        """Create a new WIPP Image Collection

        Keyword arguments:
        image_collection -- WIPP Image Collection object to create
        """
        return self.create_entity("imagesCollections", image_collection)

    def delete_image_collection(self, image_collection_id: str) -> None:
        """Delete a WIPP Image Collection

        Keyword arguments:
        image_collection_id -- WIPP Image Collection id to delete
        """
        self.delete_entity("imagesCollections", image_collection_id)

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

    def delete_csv_collection(self, csv_collection_id: str) -> None:
        """Delete a WIPP CSV Collection

        Keyword arguments:
        csv_collection_id -- WIPP CSV Collection ID to delete
        """
        self.delete_entity("csvCollections", csv_collection_id)

    def get_csv_collections_csv_files(self, collection_id: str) -> list[WippCsv]:
        """Get list of all CSV files in a WIPP CSV Collection"""
        return self.get_entities("csv", path_prefix="csvCollections/" + collection_id)

    # Generic Data methods
    def create_generic_data_collection(self, generic_data: WippGenericDataCollection):
        """Create a new WIPP Generic Data

        Keyword arguments:
        generic_data -- WippGenericData object to create
        """
        return self.create_entity("genericDatas", generic_data)

    def delete_generic_data_collection(self, generic_data_id: str) -> None:
        """Delete a WIPP Generic Data

        Keyword arguments:
        generic_data_id -- WIPP Generic Data Collection ID to delete
        """
        self.delete_entity("genericDatas", generic_data_id)

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
        """Delete a WIPP Plugin

        Keyword arguments:
        plugin_id -- WIPP Plugin ID to delete
        """
        self.delete_entity("plugins", plugin_id)
