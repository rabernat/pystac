from abc import (ABC, abstractmethod)

from pystac.catalog import Catalog
from pystac.collection import Collection
from pystac.item import Item
from pystac.extensions import ExtensionError


class ExtendedObject:
    """TODO: Documentation
    """
    def __init__(self, stac_object_class, extension_class):
        if stac_object_class is Catalog:
            if not issubclass(extension_class, CatalogExtension):
                raise ExtensionError(
                    "Classes extending catalogs must inheret from CatalogExtension")
        if stac_object_class is Collection:
            if not issubclass(extension_class, CollectionExtension):
                raise ExtensionError(
                    "Classes extending collections must inheret from CollectionExtension")
        if stac_object_class is Item:
            if not issubclass(extension_class, ItemExtension):
                raise ExtensionError("Classes extending item must inheret from ItemExtension")

        self.stac_object_class = stac_object_class
        self.extension_class = extension_class


class ExtensionDefinition:
    """TODO: Documentation

    Note about if an extension extends both Collection and Catalog, list the Collection
    extension first.
    """
    def __init__(self, extension_id, extended_objects):
        self.extension_id = extension_id
        self.extended_objects = extended_objects


class CatalogExtension(ABC):
    @classmethod
    def _from_object(cls, stac_object):
        return cls.from_catalog(stac_object)

    @classmethod
    @abstractmethod
    def from_catalog(cls, catalog):
        raise NotImplementedError("from_catalog")

    @classmethod
    @abstractmethod
    def _object_links(cls):
        raise NotImplementedError("_object_links")


class CollectionExtension(ABC):
    @classmethod
    def _from_object(cls, stac_object):
        return cls.from_collection(stac_object)

    @classmethod
    @abstractmethod
    def from_collection(cls, catalog):
        raise NotImplementedError("from_collection")

    @classmethod
    @abstractmethod
    def _object_links(cls):
        raise NotImplementedError("_object_links")


class ItemExtension(ABC):
    @classmethod
    def _from_object(cls, stac_object):
        return cls.from_item(stac_object)

    @classmethod
    @abstractmethod
    def from_item(cls, item):
        raise NotImplementedError("from_item")

    @classmethod
    @abstractmethod
    def _object_links(cls):
        raise NotImplementedError("_object_links")


class RegisteredSTACExtensions:
    def __init__(self, extension_definitions):
        self.extensions = dict([(e.extension_id, e) for e in extension_definitions])

    def is_registered_extension(self, extension_id):
        """Determines whether or not the given extension ID has been registered."""
        return extension_id in self.extensions

    def get_registered_extensions(self):
        """Returns the list of registered extension IDs."""
        return list(self.extensions.keys())

    def add_extension(self, extension_definition):
        e_id = extension_definition.extension_id
        if e_id in self.extensions:
            raise ExtensionError("ExtensionDefinition with id '{}' already exists.".format(e_id))

        self.extensions[e_id] = extension_definition

    def remove_extension(self, extension_id):
        """Remove an extension from PySTAC."""
        if extension_id not in self.extensions:
            raise ExtensionError(
                "ExtensionDefinition with id '{}' is not registered.".format(extension_id))
        del self.extensions[extension_id]

    def extend_object(self, stac_object, extension_id):
        ext = self.extensions.get(extension_id)
        if ext is None:
            raise ExtensionError("No ExtensionDefinition registered with id '{}'. "
                                 "Is the extension ID correct, or are you forgetting to call "
                                 "'add_extension' for a custom extension?".format(extension_id))

        stac_object_class = type(stac_object)

        ext_classes = [
            e.extension_class for e in ext.extended_objects
            if issubclass(stac_object_class, e.stac_object_class)
        ]

        ext_class = None
        if len(ext_classes) == 0:
            raise ExtensionError("Extension '{}' does not extend objects of type {}".format(
                extension_id, ext_class))
        elif len(ext_classes) == 1:
            ext_class = ext_classes[0]
        else:
            # Need to check collection extensions before catalogs.
            sort_key = {}
            for c in ext_classes:
                for i, base_cl in enumerate([ItemExtension, CollectionExtension, CatalogExtension]):
                    if issubclass(c, base_cl):
                        sort_key[c] = i
                        break
                if c not in sort_key:
                    sort_key[c] = -1

            ext_class = sorted(ext_classes, key=lambda c: sort_key[c])[0]

        return ext_class._from_object(stac_object)

    def get_extended_object_links(self, stac_object):
        if stac_object.stac_extensions is None:
            return []
        return [
            link_rel for e_id in stac_object.stac_extensions if e_id in self.extensions
            for e_obj in self.extensions[e_id].extended_objects
            if issubclass(type(stac_object), e_obj.stac_object_class)
            for link_rel in e_obj.extension_class._object_links()
        ]