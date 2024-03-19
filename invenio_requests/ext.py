# -*- coding: utf-8 -*-
#
# Copyright (C) 2021 CERN.
# Copyright (C) 2021 Northwestern University.
# Copyright (C) 2021 TU Wien.
# Copyright (C) 2023 Graz University of Technology.
#
# Invenio-Requests is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Invenio module for generic and customizable requests."""

from importlib_metadata import entry_points

from . import config
from .registry import TypeRegistry
from .resources import (
    RequestCommentsResource,
    RequestCommentsResourceConfig,
    RequestsResource,
    RequestsResourceConfig,
)
from .services import (
    RequestEventsService,
    RequestEventsServiceConfig,
    RequestsService,
    RequestsServiceConfig,
    UserModerationRequestService,
)


class InvenioRequests:
    """Invenio-Requests extension."""

    def __init__(self, app=None):
        """Extension initialization."""
        self.requests_service = None
        self.requests_resource = None
        self.request_comments_service = None
        self._schema_cache = {}
        self._events_schema_cache = {}
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Flask application initialization."""
        self.init_config(app)
        self.init_services(app)
        self.init_resources(app)
        self.init_registry(app)
        app.extensions["invenio-requests"] = self

    def init_config(self, app):
        """Initialize configuration."""
        for k in dir(config):
            if k.startswith("REQUESTS_"):
                app.config.setdefault(k, getattr(config, k))

    def service_configs(self, app):
        """Customized service configs."""

        class ServiceConfigs:
            requests = RequestsServiceConfig.build(app)
            request_events = RequestEventsServiceConfig.build(app)

        return ServiceConfigs

    def init_services(self, app):
        """Initialize the service and resource for Requests."""
        service_configs = self.service_configs(app)

        self.requests_service = RequestsService(
            config=service_configs.requests,
        )
        self.request_events_service = RequestEventsService(
            config=service_configs.request_events,
        )
        self.user_moderation_requests_service = UserModerationRequestService(
            requests_service=self.requests_service,
        )

    def init_resources(self, app):
        """Init resources."""
        self.requests_resource = RequestsResource(
            service=self.requests_service,
            config=RequestsResourceConfig.build(app),
        )

        self.request_events_resource = RequestCommentsResource(
            service=self.request_events_service,
            config=RequestCommentsResourceConfig,
        )

    def init_registry(self, app):
        """Initialize the registry for Requests per type."""
        self.request_type_registry = TypeRegistry(
            app.config["REQUESTS_REGISTERED_TYPES"]
        )
        self.event_type_registry = TypeRegistry(
            app.config["REQUESTS_REGISTERED_EVENT_TYPES"]
        )
        self.entity_resolvers_registry = TypeRegistry(
            app.config["REQUESTS_ENTITY_RESOLVERS"]
        )
        # Load from entry points
        register_entry_point(self.request_type_registry, "invenio_requests.types")
        register_entry_point(self.request_type_registry, "invenio_requests.event_types")
        register_entry_point(
            self.entity_resolvers_registry, "invenio_requests.entity_resolvers"
        )


def register_entry_point(registry, ep_name):
    """Register types from an entry point."""
    for ep in set(entry_points(group=ep_name)):
        type_cls = ep.load()
        registry.register_type(type_cls())


def finalize_app(app):
    """Finalize app.

    NOTE: replace former @record_once decorator
    """
    init(app)


def api_finalize_app(app):
    """Finalize app for api.

    NOTE: replace former @record_once decorator
    """
    init(app)


def init(app):
    """Register the module's services and indexers to the central registries."""
    svc_reg = app.extensions["invenio-records-resources"].registry
    idx_reg = app.extensions["invenio-indexer"].registry
    requests_ext = app.extensions["invenio-requests"]
    requests_service = requests_ext.requests_service
    events_service = requests_ext.request_events_service

    svc_reg.register(requests_service)
    svc_reg.register(events_service)

    idx_reg.register(requests_service.indexer, indexer_id="requests")
    idx_reg.register(events_service.indexer, indexer_id="events")
