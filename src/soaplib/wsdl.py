
#
# soaplib - Copyright (C) Soaplib contributors.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301
#

import logging
from lxml import etree

import soaplib



logger = logging.getLogger("soaplib._base")

class WSDL():

    """ A standalone wsdl """

    def __init__(self, soap_application, ns_tns, url, with_partner_link=False):


        self.nsmap = dict(soaplib.const_nsmap)
        self.prefmap = dict(soaplib.const_prefmap)
        self.ns_tns = ns_tns
        self.pref_tns = 'tns'
        self.application = soap_application
        self.application.url = url.replace('.wsdl', '')
        self.url = self.application.url
        self._with_plink = with_partner_link
        self.service_node_dict = {}
        self.bindings_dict = {}
        self.port_type_dict = {}
        self.soap_bindings_dict = {}
        self.service_port_dict = {}

        self.elements= None


    def to_string(self,
                  pretty_print=False,
                  xml_declaration=True,
                  encoding="UTF-8"
    ):
        """Returns a string reprensation of the  wsdl as fornatted xml."""

        if self.elements is None:
            self.build_wsdl()

        return etree.tostring(
            self.elements,
            encoding=encoding,
            xml_declaration=xml_declaration,
            pretty_print=pretty_print
        )


    def _build_root(self):
        ''' Build ths root element of the wsdl '''

        self.application.set_namespace_prefix(self.ns_tns, self.pref_tns)
        self.root = etree.Element(
            "{%s}definitions" % soaplib.ns_wsdl,
            nsmap=self.application.nsmap
        )

        self.root.set('targetNamespace', self.ns_tns)
        self.root.set('name', self.application.name)


    def _build_types(self):
        ''' Builds the wsdl:types elemement  '''

        self.application.types = etree.SubElement(
            self.root,
            "{%s}types" % soaplib.ns_wsdl
        )

        self.application.build_schema(self.application.types)


    def build_messages(self):
        ''' Builds the wsdl:message elements '''

        self.application.messages = set()

        for s in self.application.services:
           s = self.application.get_service(s,None)
           s.add_messages_for_methods(
               self.application,
               self.root,
               self.application.messages
           )


    def _build_plink(self, service_name):
        ''' Builds partnerlinks '''

        self.plink = etree.SubElement(
            self.root,
            '{%s}partnerLinkType' % soaplib.ns_plink
        )

        self.plink.set('name', service_name)
        self.application.__add_partner_link(
            self.root,
            service_name,
            self.application.types,
            self.application.url,
            self.plink
        )


    def _get_or_create_service_node(self, service_name):
        ''' Builds a wsdl:service element. '''

        ser = None
        if not self.service_node_dict.has_key(service_name):

            ser = etree.SubElement(self.root, '{%s}service' % soaplib.ns_wsdl)
            ser.set('name', service_name)            
            self.service_node_dict[service_name] = ser

        else:
            ser = self.service_node_dict[service_name]
           
        return ser


    def _add_port_to_service(self, service, port_name, pt_name):

        """ Builds a wsdl:port for a service and binding"""

        pref_tns = self.application.get_namespace_prefix(
            self.application.get_tns()
        )

        wsdl_port = etree.SubElement(service, '{%s}port' % soaplib.ns_wsdl)
        wsdl_port.set('name', port_name)
        wsdl_port.set('binding', '%s:%s' % (pref_tns, pt_name))

        addr = etree.SubElement(wsdl_port, '{%s}address' % soaplib.ns_soap)
        addr.set('location', self.application.url)

    
    def _get_or_create_port_type(self, pt_name):
        """ Creates a wsdl:portType element. """

        pt = None
        
        if not self.port_type_dict.has_key(pt_name):

            pt = etree.SubElement(self.root, '{%s}portType' % soaplib.ns_wsdl)
            pt.set('name', pt_name)
            self.port_type_dict[pt_name] = pt
        else:
            pt = self.port_type_dict[pt_name]

        return pt


    def _get_or_create_binding(self, binding_name, port_type_name):
        ''' Creates a wsdl:binding element for a portType. '''

        binding = None
        if not self.bindings_dict.has_key(binding_name):
            binding = etree.SubElement(
                self.root,
                '{%s}binding' % soaplib.ns_wsdl
            )

            binding.set('name', binding_name)
            binding.set('type', '%s:%s'% (self.pref_tns, port_type_name))
            self.bindings_dict[binding_name] = binding
        else:
            binding = self.bindings_dict[binding_name]

        return binding
    

    def _get_or_create_soap_binding(self, binding):
        """ Creates a soap:binding element for a binding. """
        binding_name = binding.get('name')
        soap_binding = None

        if not self.soap_bindings_dict.has_key(binding_name):
            soap_binding = etree.SubElement(
                binding,
                '{%s}binding' % soaplib.ns_soap
            )

            soap_binding.set('style', 'document')
            soap_binding.set('transport', self.application.transport)
            self.soap_bindings_dict[binding_name] = soap_binding
        else:
            soap_binding = self.soap_bindings_dict[binding_name]

        return soap_binding


    def _build_entry_points(self):
        """ Iterates over the soaplib service objects in the application and
            constructs the wsdl elements used for representing operations.
        """

        default_service_name = self.application.get_name()
        applied_service_name = None
        for service in self.application.services:
            ser = None
            cb_binding = None

            if service.get_service_interface() is None:
                # This is the default behavior. i.e. no service interface is
                # defined in the service heading
                applied_service_name = default_service_name
            else:
                applied_service_name = service.get_service_interface()

            ser = self._get_or_create_service_node(applied_service_name)

            port_type_list = service.get_port_types()
            if len(port_type_list) != 0:

                pt = None
                for port_type in port_type_list:

                    pt = self._get_or_create_port_type(port_type)
                    pt_name = pt.get('name')
                    self._add_port_to_service(ser, pt_name, pt_name)
                    binding = self._get_or_create_binding(pt_name, pt_name)
                    soap_binding = self._get_or_create_soap_binding(binding)

                    s=self.application.get_service(service)
                    s.add_port_type(
                        self.application,
                        self.root,
                        ser.get('name'),
                        self.application.types,
                        self.application.url,
                        pt
                    )

                    cb_binding = s.add_bindings_for_methods(
                        self.application,
                        self.root,
                        service.get_service_class_name(),
                        self.application.types,
                        self.application.url,
                        binding,
                        cb_binding
                    )

            else:

                pt = self._get_or_create_port_type(applied_service_name)
                pt_name = pt.get('name')
                self._add_port_to_service(ser, pt_name, pt_name )
                binding = self._get_or_create_binding(pt_name, pt_name)
                soap_binding = self._get_or_create_soap_binding(binding)
                s=self.application.get_service(service)
                s.add_port_type(
                    self.application,
                    self.root,
                    ser.get('name'),
                    self.application.types,
                    self.application.url,
                    pt
                )

                cb_binding = s.add_bindings_for_methods(
                    self.application,
                    self.root,
                    service.get_service_class_name(),
                    self.application.types,
                    self.application.url,
                    binding,
                    cb_binding
                )


    def build_wsdl(self):
        ''' Construct the elements for the wsdl. '''

        self._build_root()
        self._build_types()
        self.build_messages()


        if self._with_plink:
            self._build_plink(self.application.name)

        self._build_entry_points()
        self.elements = self.root
        return self.root