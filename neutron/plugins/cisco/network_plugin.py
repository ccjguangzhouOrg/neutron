# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2012 Cisco Systems, Inc.  All rights reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# @author: Sumit Naiksatam, Cisco Systems, Inc.

import logging

import webob.exc as wexc

from neutron.api import extensions as neutron_extensions
from neutron.api.v2 import base
from neutron.db import db_base_plugin_v2
from neutron.openstack.common import importutils
from neutron.plugins.cisco.common import cisco_exceptions as cexc
from neutron.plugins.cisco.common import config
from neutron.plugins.cisco.db import network_db_v2 as cdb
from neutron.plugins.cisco import extensions

LOG = logging.getLogger(__name__)


class PluginV2(db_base_plugin_v2.NeutronDbPluginV2):
    """Meta-Plugin with v2 API support for multiple sub-plugins."""
    supported_extension_aliases = ["credential", "Cisco qos"]
    _methods_to_delegate = ['create_network',
                            'delete_network', 'update_network', 'get_network',
                            'get_networks',
                            'create_port', 'delete_port',
                            'update_port', 'get_port', 'get_ports',
                            'create_subnet',
                            'delete_subnet', 'update_subnet',
                            'get_subnet', 'get_subnets', ]

    CISCO_FAULT_MAP = {
        cexc.NetworkSegmentIDNotFound: wexc.HTTPNotFound,
        cexc.NoMoreNics: wexc.HTTPBadRequest,
        cexc.NetworkVlanBindingAlreadyExists: wexc.HTTPBadRequest,
        cexc.VlanIDNotFound: wexc.HTTPNotFound,
        cexc.VlanIDNotAvailable: wexc.HTTPNotFound,
        cexc.QosNotFound: wexc.HTTPNotFound,
        cexc.QosNameAlreadyExists: wexc.HTTPBadRequest,
        cexc.CredentialNotFound: wexc.HTTPNotFound,
        cexc.CredentialNameNotFound: wexc.HTTPNotFound,
        cexc.CredentialAlreadyExists: wexc.HTTPBadRequest,
        cexc.NexusComputeHostNotConfigured: wexc.HTTPNotFound,
        cexc.NexusConnectFailed: wexc.HTTPServiceUnavailable,
        cexc.NexusConfigFailed: wexc.HTTPBadRequest,
        cexc.NexusPortBindingNotFound: wexc.HTTPNotFound,
        cexc.PortVnicBindingAlreadyExists: wexc.HTTPBadRequest,
        cexc.PortVnicNotFound: wexc.HTTPNotFound}

    def __init__(self):
        """Load the model class."""
        self._model = importutils.import_object(config.CISCO.model_class)
        native_bulk_attr_name = ("_%s__native_bulk_support"
                                 % self._model.__class__.__name__)
        self.__native_bulk_support = getattr(self._model,
                                             native_bulk_attr_name, False)

        if hasattr(self._model, "supported_extension_aliases"):
            self.supported_extension_aliases.extend(
                self._model.supported_extension_aliases)

        neutron_extensions.append_api_extensions_path(extensions.__path__)

        # Extend the fault map
        self._extend_fault_map()

        LOG.debug(_("Plugin initialization complete"))

    def __getattribute__(self, name):
        """Delegate core API calls to the model class.

        Core API calls are delegated directly to the configured model class.
        Note: Bulking calls will be handled by this class, and turned into
        non-bulking calls to be considered for delegation.
        """
        methods = object.__getattribute__(self, "_methods_to_delegate")
        if name in methods:
            return getattr(object.__getattribute__(self, "_model"),
                           name)
        else:
            return object.__getattribute__(self, name)

    def __getattr__(self, name):
        """Delegate calls to the extensions.

        This delegates the calls to the extensions explicitly implemented by
        the model.
        """
        if hasattr(self._model, name):
            return getattr(self._model, name)
        else:
            # Must make sure we re-raise the error that led us here, since
            # otherwise getattr() and even hasattr() doesn't work corretly.
            raise AttributeError(
                _("'%(model)s' object has no attribute '%(name)s'") %
                {'model': self._model, 'name': name})

    def _extend_fault_map(self):
        """Extend the Neutron Fault Map for Cisco exceptions.

        Map exceptions which are specific to the Cisco Plugin
        to standard HTTP exceptions.

        """
        base.FAULT_MAP.update(self.CISCO_FAULT_MAP)

    """
    Extension API implementation
    """
    def get_all_qoss(self, tenant_id):
        """Get all QoS levels."""
        LOG.debug(_("get_all_qoss() called"))
        qoslist = cdb.get_all_qoss(tenant_id)
        return qoslist

    def get_qos_details(self, tenant_id, qos_id):
        """Get QoS Details."""
        LOG.debug(_("get_qos_details() called"))
        return cdb.get_qos(tenant_id, qos_id)

    def create_qos(self, tenant_id, qos_name, qos_desc):
        """Create a QoS level."""
        LOG.debug(_("create_qos() called"))
        qos = cdb.add_qos(tenant_id, qos_name, str(qos_desc))
        return qos

    def delete_qos(self, tenant_id, qos_id):
        """Delete a QoS level."""
        LOG.debug(_("delete_qos() called"))
        return cdb.remove_qos(tenant_id, qos_id)

    def rename_qos(self, tenant_id, qos_id, new_name):
        """Rename QoS level."""
        LOG.debug(_("rename_qos() called"))
        return cdb.update_qos(tenant_id, qos_id, new_name)

    def get_all_credentials(self):
        """Get all credentials."""
        LOG.debug(_("get_all_credentials() called"))
        credential_list = cdb.get_all_credentials()
        return credential_list

    def get_credential_details(self, credential_id):
        """Get a particular credential."""
        LOG.debug(_("get_credential_details() called"))
        return cdb.get_credential(credential_id)

    def rename_credential(self, credential_id, new_name, new_password):
        """Rename the particular credential resource."""
        LOG.debug(_("rename_credential() called"))
        return cdb.update_credential(credential_id, new_name,
                                     new_password=new_password)
