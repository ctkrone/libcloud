# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Tests for Google Compute Engine Driver
"""
import sys
import unittest
import datetime

from libcloud.utils.py3 import httplib
from libcloud.compute.drivers.gce import (GCENodeDriver, API_VERSION,
                                          timestamp_to_datetime,
                                          GCEAddress, GCEFirewall, GCENetwork,
                                          GCENodeSize, GCEProject, GCEZone,
                                          GCEError, ResourceExistsError,
                                          QuotaExceededError)
from libcloud.common.google import (GoogleBaseAuthConnection,
                                    GoogleInstalledAppAuthConnection,
                                    GoogleBaseConnection)
from libcloud.test.common.test_google import GoogleAuthMockHttp
from libcloud.compute.base import (Node, NodeImage, NodeSize, NodeLocation,
                                   StorageVolume)

from libcloud.test import MockHttpTestCase, LibcloudTestCase
from libcloud.test.compute import TestCaseMixin
from libcloud.test.file_fixtures import ComputeFileFixtures

from libcloud.test.secrets import GCE_PARAMS, GCE_KEYWORD_PARAMS


class GCENodeDriverTest(LibcloudTestCase, TestCaseMixin):
    """
    Google Compute Engine Test Class.
    """
    # Mock out a few specific calls that interact with the user, system or
    # environment.
    GoogleBaseConnection._get_token_info_from_file = lambda x: None
    GoogleBaseConnection._write_token_info_to_file = lambda x: None
    GoogleInstalledAppAuthConnection.get_code = lambda x: '1234'
    GCEZone._now = lambda x: datetime.datetime(2013, 6, 26, 19, 0, 0)
    datacenter = 'us-central1-a'

    def setUp(self):
        GCEMockHttp.test = self
        GCENodeDriver.connectionCls.conn_classes = (GCEMockHttp, GCEMockHttp)
        GoogleBaseAuthConnection.conn_classes = (GoogleAuthMockHttp,
                                                 GoogleAuthMockHttp)
        GCEMockHttp.type = None
        kwargs = GCE_KEYWORD_PARAMS.copy()
        kwargs['auth_type'] = 'IA'
        kwargs['datacenter'] = self.datacenter
        self.driver = GCENodeDriver(*GCE_PARAMS, **kwargs)

    def test_timestamp_to_datetime(self):
        timestamp1 = '2013-06-26T10:05:19.340-07:00'
        datetime1 = datetime.datetime(2013, 6, 26, 17, 5, 19)
        self.assertEqual(timestamp_to_datetime(timestamp1), datetime1)
        timestamp2 = '2013-06-26T17:43:15.000-00:00'
        datetime2 = datetime.datetime(2013, 6, 26, 17, 43, 15)
        self.assertEqual(timestamp_to_datetime(timestamp2), datetime2)

    def test_find_zone(self):
        zone1 = self.driver._find_zone('libcloud-demo-np-node', 'instances')
        self.assertEqual(zone1, 'us-central1-a')
        zone2 = self.driver._find_zone('libcloud-demo-europe-np-node',
                                       'instances')
        self.assertEqual(zone2, 'europe-west1-a')
        region = self.driver._find_zone('libcloud-demo-address', 'addresses',
                                        region=True)
        self.assertEqual(region, 'us-central1')

    def test_match_images(self):
        project = 'debian-cloud'
        image = self.driver._match_images(project, 'debian-7')
        self.assertEqual(image.name, 'debian-7-wheezy-v20130617')
        image = self.driver._match_images(project, 'debian-6')
        self.assertEqual(image.name, 'debian-6-squeeze-v20130617')

    def test_ex_list_addresses(self):
        address_list = self.driver.ex_list_addresses()
        address_list_all = self.driver.ex_list_addresses('all')
        address_list_uc1 = self.driver.ex_list_addresses('us-central1')
        self.assertEqual(len(address_list), 2)
        self.assertEqual(len(address_list_all), 4)
        self.assertEqual(address_list[0].name, 'libcloud-demo-address')
        self.assertEqual(address_list_uc1[0].name, 'libcloud-demo-address')
        self.assertEqual(address_list_all[0].name, 'lcaddress')

    def test_ex_list_firewalls(self):
        firewalls = self.driver.ex_list_firewalls()
        self.assertEqual(len(firewalls), 4)
        self.assertEqual(firewalls[0].name, 'default-allow-internal')

    def test_list_images(self):
        local_images = self.driver.list_images()
        debian_images = self.driver.list_images(ex_project='debian-cloud')
        self.assertEqual(len(local_images), 1)
        self.assertEqual(len(debian_images), 10)
        self.assertEqual(local_images[0].name, 'debian-7-wheezy-v20130617')

    def test_list_locations(self):
        locations = self.driver.list_locations()
        self.assertEqual(len(locations), 5)
        self.assertEqual(locations[0].name, 'europe-west1-a')

    def test_ex_list_networks(self):
        networks = self.driver.ex_list_networks()
        self.assertEqual(len(networks), 3)
        self.assertEqual(networks[0].name, 'default')

    def test_list_nodes(self):
        nodes = self.driver.list_nodes()
        nodes_all = self.driver.list_nodes(ex_zone='all')
        nodes_uc1a = self.driver.list_nodes(ex_zone='us-central1-a')
        self.assertEqual(len(nodes), 5)
        self.assertEqual(len(nodes_all), 8)
        self.assertEqual(len(nodes_uc1a), 5)
        self.assertEqual(nodes[0].name, 'node-name')
        self.assertEqual(nodes_uc1a[0].name, 'node-name')
        self.assertEqual(nodes_all[0].name, 'libcloud-demo-persist-node')

    def test_list_sizes(self):
        sizes = self.driver.list_sizes()
        sizes_all = self.driver.list_sizes('all')
        self.assertEqual(len(sizes), 22)
        self.assertEqual(len(sizes_all), 100)
        self.assertEqual(sizes[0].name, 'f1-micro')
        self.assertEqual(sizes[0].extra['zone'].name, 'us-central1-a')
        self.assertEqual(sizes_all[0].name, 'n1-highmem-8')
        self.assertEqual(sizes_all[0].extra['zone'].name, 'us-central1-a')

    def test_list_volumes(self):
        volumes = self.driver.list_volumes()
        volumes_all = self.driver.list_volumes('all')
        volumes_uc1a = self.driver.list_volumes('us-central1-a')
        self.assertEqual(len(volumes), 3)
        self.assertEqual(len(volumes_all), 3)
        self.assertEqual(len(volumes_uc1a), 3)
        self.assertEqual(volumes[0].name, 'lcdisk')
        self.assertEqual(volumes_all[0].name, 'test-disk')
        self.assertEqual(volumes_uc1a[0].name, 'lcdisk')

    def test_ex_list_zones(self):
        zones = self.driver.ex_list_zones()
        self.assertEqual(len(zones), 5)
        self.assertEqual(zones[0].name, 'europe-west1-a')

    def test_ex_create_address(self):
        address_name = 'lcaddress'
        address = self.driver.ex_create_address(address_name)
        self.assertTrue(isinstance(address, GCEAddress))
        self.assertEqual(address.name, address_name)

    def test_ex_create_firewall(self):
        firewall_name = 'lcfirewall'
        allowed = [{'IPProtocol': 'tcp', 'ports': ['4567']}]
        source_tags = ['libcloud']
        firewall = self.driver.ex_create_firewall(firewall_name, allowed,
                                                  source_tags=source_tags)
        self.assertTrue(isinstance(firewall, GCEFirewall))
        self.assertEqual(firewall.name, firewall_name)

    def test_ex_create_network(self):
        network_name = 'lcnetwork'
        cidr = '10.11.0.0/16'
        network = self.driver.ex_create_network(network_name, cidr)
        self.assertTrue(isinstance(network, GCENetwork))
        self.assertEqual(network.name, network_name)
        self.assertEqual(network.cidr, cidr)

    def test_create_node_req(self):
        image = self.driver.ex_get_image('debian-7')
        size = self.driver.ex_get_size('n1-standard-1')
        location = self.driver.zone
        network = self.driver.ex_get_network('default')
        tags = ['libcloud']
        metadata = [{'key': 'test_key', 'value': 'test_value'}]
        boot_disk = self.driver.ex_get_volume('lcdisk')
        node_request, node_data = self.driver._create_node_req('lcnode', size,
                                                               image, location,
                                                               network, tags,
                                                               metadata,
                                                               boot_disk)
        self.assertEqual(node_request, '/zones/%s/instances' % location.name)
        self.assertEqual(node_data['metadata'][0]['key'], 'test_key')
        self.assertEqual(node_data['tags']['items'][0], 'libcloud')
        self.assertEqual(node_data['name'], 'lcnode')
        self.assertTrue(node_data['disks'][0]['boot'])

    def test_create_node(self):
        node_name = 'node-name'
        image = self.driver.ex_get_image('debian-7')
        size = self.driver.ex_get_size('n1-standard-1')
        node = self.driver.create_node(node_name, size, image)
        self.assertTrue(isinstance(node, Node))
        self.assertEqual(node.name, node_name)

    def test_create_node_existing(self):
        node_name = 'libcloud-demo-europe-np-node'
        image = self.driver.ex_get_image('debian-7')
        size = self.driver.ex_get_size('n1-standard-1', zone='europe-west1-a')
        self.assertRaises(ResourceExistsError, self.driver.create_node,
                          node_name, size, image, location='europe-west1-a')

    def test_ex_create_multiple_nodes(self):
        base_name = 'lcnode'
        image = self.driver.ex_get_image('debian-7')
        size = self.driver.ex_get_size('n1-standard-1')
        number = 2
        nodes = self.driver.ex_create_multiple_nodes(base_name, size, image,
                                                     number)
        self.assertEqual(len(nodes), 2)
        self.assertTrue(isinstance(nodes[0], Node))
        self.assertTrue(isinstance(nodes[1], Node))
        self.assertEqual(nodes[0].name, '%s-000' % base_name)
        self.assertEqual(nodes[1].name, '%s-001' % base_name)

    def test_create_volume(self):
        volume_name = 'lcdisk'
        size = 1
        volume = self.driver.create_volume(size, volume_name)
        self.assertTrue(isinstance(volume, StorageVolume))
        self.assertEqual(volume.name, volume_name)

    def test_ex_update_firewall(self):
        firewall_name = 'lcfirewall'
        firewall = self.driver.ex_get_firewall(firewall_name)
        firewall.source_ranges = ['10.0.0.0/16']
        firewall.source_tags = ['libcloud', 'test']
        firewall2 = self.driver.ex_update_firewall(firewall)
        self.assertTrue(isinstance(firewall2, GCEFirewall))

    def test_reboot_node(self):
        node = self.driver.ex_get_node('node-name')
        reboot = self.driver.reboot_node(node)
        self.assertTrue(reboot)

    def test_ex_set_node_tags(self):
        new_tags = ['libcloud']
        node = self.driver.ex_get_node('node-name')
        set_tags = self.driver.ex_set_node_tags(node, new_tags)
        self.assertTrue(set_tags)

    def test_attach_volume(self):
        volume = self.driver.ex_get_volume('lcdisk')
        node = self.driver.ex_get_node('node-name')
        attach = volume.attach(node)
        self.assertTrue(attach)

    def test_detach_volume(self):
        volume = self.driver.ex_get_volume('lcdisk')
        node = self.driver.ex_get_node('node-name')
        # This fails since the node is required
        detach = volume.detach()
        self.assertFalse(detach)
        # This should pass
        detach = self.driver.detach_volume(volume, node)
        self.assertTrue(detach)

    def test_ex_destroy_address(self):
        address = self.driver.ex_get_address('lcaddress')
        destroyed = address.destroy()
        self.assertTrue(destroyed)

    def test_ex_destroy_firewall(self):
        firewall = self.driver.ex_get_firewall('lcfirewall')
        destroyed = firewall.destroy()
        self.assertTrue(destroyed)

    def test_ex_destroy_network(self):
        network = self.driver.ex_get_network('lcnetwork')
        destroyed = network.destroy()
        self.assertTrue(destroyed)

    def test_destroy_node(self):
        node = self.driver.ex_get_node('node-name')
        destroyed = node.destroy()
        self.assertTrue(destroyed)

    def test_ex_destroy_multiple_nodes(self):
        nodes = []
        nodes.append(self.driver.ex_get_node('lcnode-000'))
        nodes.append(self.driver.ex_get_node('lcnode-001'))
        destroyed = self.driver.ex_destroy_multiple_nodes(nodes)
        for d in destroyed:
            self.assertTrue(d)

    def test_destroy_volume(self):
        address = self.driver.ex_get_address('lcaddress')
        destroyed = address.destroy()
        self.assertTrue(destroyed)

    def test_ex_get_address(self):
        address_name = 'lcaddress'
        address = self.driver.ex_get_address(address_name)
        self.assertEqual(address.name, address_name)
        self.assertEqual(address.address, '173.255.113.20')
        self.assertEqual(address.region, 'us-central1')
        self.assertEqual(address.extra['status'], 'RESERVED')

    def test_ex_get_firewall(self):
        firewall_name = 'lcfirewall'
        firewall = self.driver.ex_get_firewall(firewall_name)
        self.assertEqual(firewall.name, firewall_name)
        self.assertEqual(firewall.network.name, 'default')
        self.assertEqual(firewall.source_tags, ['libcloud'])

    def test_ex_get_image(self):
        partial_name = 'debian-7'
        image = self.driver.ex_get_image(partial_name)
        self.assertEqual(image.name, 'debian-7-wheezy-v20130617')
        # A 'debian-7' image exists in the local project
        self.assertTrue(image.extra['description'].startswith('Local'))

        partial_name = 'debian-6'
        image = self.driver.ex_get_image(partial_name)
        self.assertEqual(image.name, 'debian-6-squeeze-v20130617')
        self.assertTrue(image.extra['description'].startswith('Debian'))

    def test_ex_get_network(self):
        network_name = 'lcnetwork'
        network = self.driver.ex_get_network(network_name)
        self.assertEqual(network.name, network_name)
        self.assertEqual(network.cidr, '10.11.0.0/16')
        self.assertEqual(network.extra['gatewayIPv4'], '10.11.0.1')

    def test_ex_get_project(self):
        project = self.driver.ex_get_project()
        self.assertEqual(project.name, 'project_name')
        instances_quota = project.quotas[0]
        self.assertEqual(instances_quota['usage'], 7.0)
        self.assertEqual(instances_quota['limit'], 8.0)

    def test_ex_get_size(self):
        size_name = 'n1-standard-1'
        size = self.driver.ex_get_size(size_name)
        self.assertEqual(size.name, size_name)
        self.assertEqual(size.extra['zone'].name, 'us-central1-a')
        self.assertEqual(size.disk, 10)
        self.assertEqual(size.ram, 3840)
        self.assertEqual(size.extra['guestCpus'], 1)

    def test_ex_get_volume(self):
        volume_name = 'lcdisk'
        volume = self.driver.ex_get_volume(volume_name)
        self.assertEqual(volume.name, volume_name)
        self.assertEqual(volume.size, '1')
        self.assertEqual(volume.extra['status'], 'READY')

    def test_ex_get_zone(self):
        zone_name = 'us-central1-a'
        expected_time_until = datetime.timedelta(days=52)
        expected_duration = datetime.timedelta(days=15)
        zone = self.driver.ex_get_zone(zone_name)
        self.assertEqual(zone.name, zone_name)
        self.assertEqual(zone.time_until_mw, expected_time_until)
        self.assertEqual(zone.next_mw_duration, expected_duration)


class GCEMockHttp(MockHttpTestCase):
    fixtures = ComputeFileFixtures('gce')
    json_hdr = {'content-type': 'application/json; charset=UTF-8'}

    def _get_method_name(self, type, use_param, qs, path):
        api_path = '/compute/%s' % API_VERSION
        project_path = '/projects/%s' % GCE_KEYWORD_PARAMS['project']
        path = path.replace(api_path, '')
        # This replace is separate, since there is a call with a different
        # project name
        path = path.replace(project_path, '')
        # The path to get project information is the base path, so use a fake
        # '/project' path instead
        if not path:
            path = '/project'
        method_name = super(GCEMockHttp, self)._get_method_name(type,
                                                                use_param,
                                                                qs, path)
        return method_name

    def _aggregated_addresses(self, method, url, body, headers):
        body = self.fixtures.load('aggregated_addresses.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _aggregated_disks(self, method, url, body, headers):
        body = self.fixtures.load('aggregated_disks.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _aggregated_instances(self, method, url, body, headers):
        body = self.fixtures.load('aggregated_instances.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _aggregated_machineTypes(self, method, url, body, headers):
        body = self.fixtures.load('aggregated_machineTypes.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_firewalls(self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load('global_firewalls_post.json')
        else:
            body = self.fixtures.load('global_firewalls.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_firewalls_lcfirewall(self, method, url, body, headers):
        if method == 'DELETE':
            body = self.fixtures.load(
                'global_firewalls_lcfirewall_delete.json')
        elif method == 'PUT':
            body = self.fixtures.load('global_firewalls_lcfirewall_put.json')
        else:
            body = self.fixtures.load('global_firewalls_lcfirewall.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_images(self, method, url, body, headers):
        body = self.fixtures.load('global_images.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_networks(self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load('global_networks_post.json')
        else:
            body = self.fixtures.load('global_networks.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_networks_default(self, method, url, body, headers):
        body = self.fixtures.load('global_networks_default.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_networks_libcloud_demo_network(self, method, url, body,
                                               headers):
        body = self.fixtures.load('global_networks_libcloud-demo-network.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_networks_libcloud_demo_europe_network(self, method, url, body,
                                                      headers):
        body = self.fixtures.load(
            'global_networks_libcloud-demo-europe-network.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_networks_lcnetwork(self, method, url, body, headers):
        if method == 'DELETE':
            body = self.fixtures.load('global_networks_lcnetwork_delete.json')
        else:
            body = self.fixtures.load('global_networks_lcnetwork.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_operations_operation_global_firewalls_lcfirewall_delete(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_global_firewalls_lcfirewall_delete.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_operations_operation_global_firewalls_lcfirewall_put(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_global_firewalls_lcfirewall_put.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_operations_operation_global_firewalls_post(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_global_firewalls_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_operations_operation_global_networks_lcnetwork_delete(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_global_networks_lcnetwork_delete.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _global_operations_operation_global_networks_post(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_global_networks_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_us_central1_operations_operation_regions_us_central1_addresses_lcaddress_delete(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_regions_us-central1_addresses_lcaddress_delete.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_us_central1_operations_operation_regions_us_central1_addresses_post(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_regions_us-central1_addresses_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_operations_operation_zones_us_central1_a_disks_lcdisk_delete(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_zones_us-central1-a_disks_lcdisk_delete.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_operations_operation_zones_us_central1_a_disks_post(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_zones_us-central1-a_disks_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_operations_operation_zones_us_central1_a_instances_lcnode_000_delete(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_zones_us-central1-a_instances_lcnode-000_delete.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_operations_operation_zones_us_central1_a_instances_lcnode_001_delete(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_zones_us-central1-a_instances_lcnode-001_delete.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_operations_operation_zones_us_central1_a_instances_node_name_delete(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_zones_us-central1-a_instances_node-name_delete.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_operations_operation_zones_us_central1_a_instances_node_name_attachDisk_post(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_zones_us-central1-a_instances_node-name_attachDisk_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_operations_operation_zones_us_central1_a_instances_node_name_detachDisk_post(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_zones_us-central1-a_instances_node-name_detachDisk_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_operations_operation_zones_us_central1_a_instances_node_name_setTags_post(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_zones_us-central1-a_instances_node-name_setTags_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_operations_operation_zones_us_central1_a_instances_node_name_reset_post(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_zones_us-central1-a_instances_node-name_reset_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_europe_west1_a_operations_operation_zones_europe_west1_a_instances_post(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_zones_europe-west1-a_instances_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_operations_operation_zones_us_central1_a_instances_post(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'operations_operation_zones_us-central1-a_instances_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _project(self, method, url, body, headers):
        body = self.fixtures.load('project.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _projects_debian_cloud_global_images(self, method, url, body, headers):
        body = self.fixtures.load('projects_debian-cloud_global_images.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_us_central1_addresses(self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load(
                'regions_us-central1_addresses_post.json')
        else:
            body = self.fixtures.load('regions_us-central1_addresses.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _regions_us_central1_addresses_lcaddress(self, method, url, body,
                                                 headers):
        if method == 'DELETE':
            body = self.fixtures.load(
                'regions_us-central1_addresses_lcaddress_delete.json')
        else:
            body = self.fixtures.load(
                'regions_us-central1_addresses_lcaddress.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones(self, method, url, body, headers):
        body = self.fixtures.load('zones.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_disks(self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load('zones_us-central1-a_disks_post.json')
        else:
            body = self.fixtures.load('zones_us-central1-a_disks.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_disks_lcdisk(self, method, url, body, headers):
        if method == 'DELETE':
            body = self.fixtures.load(
                'zones_us-central1-a_disks_lcdisk_delete.json')
        else:
            body = self.fixtures.load('zones_us-central1-a_disks_lcdisk.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_europe_west1_a_instances(self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load(
                'zones_europe-west1-a_instances_post.json')
        else:
            body = self.fixtures.load('zones_europe-west1-a_instances.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_instances(self, method, url, body, headers):
        if method == 'POST':
            body = self.fixtures.load(
                'zones_us-central1-a_instances_post.json')
        else:
            body = self.fixtures.load('zones_us-central1-a_instances.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_instances_node_name(self, method, url, body,
                                                 headers):
        if method == 'DELETE':
            body = self.fixtures.load(
                'zones_us-central1-a_instances_node-name_delete.json')
        else:
            body = self.fixtures.load(
                'zones_us-central1-a_instances_node-name.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_instances_node_name_attachDisk(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'zones_us-central1-a_instances_node-name_attachDisk_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_instances_node_name_detachDisk(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'zones_us-central1-a_instances_node-name_detachDisk_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_instances_node_name_setTags(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'zones_us-central1-a_instances_node-name_setTags_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_instances_node_name_reset(
            self, method, url, body, headers):
        body = self.fixtures.load(
            'zones_us-central1-a_instances_node-name_reset_post.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_instances_lcnode_000(self, method, url, body,
                                                  headers):
        if method == 'DELETE':
            body = self.fixtures.load(
                'zones_us-central1-a_instances_lcnode-000_delete.json')
        else:
            body = self.fixtures.load(
                'zones_us-central1-a_instances_lcnode-000.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_instances_lcnode_001(self, method, url, body,
                                                  headers):
        if method == 'DELETE':
            body = self.fixtures.load(
                'zones_us-central1-a_instances_lcnode-001_delete.json')
        else:
            body = self.fixtures.load(
                'zones_us-central1-a_instances_lcnode-001.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a(self, method, url, body, headers):
        body = self.fixtures.load('zones_us-central1-a.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_machineTypes(self, method, url, body, headers):
        body = self.fixtures.load('zones_us-central1-a_machineTypes.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_europe_west1_a_machineTypes_n1_standard_1(self, method, url,
                                                         body, headers):
        body = self.fixtures.load(
            'zones_europe-west1-a_machineTypes_n1-standard-1.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])

    def _zones_us_central1_a_machineTypes_n1_standard_1(self, method, url,
                                                        body, headers):
        body = self.fixtures.load(
            'zones_us-central1-a_machineTypes_n1-standard-1.json')
        return (httplib.OK, body, self.json_hdr, httplib.responses[httplib.OK])


if __name__ == '__main__':
    sys.exit(unittest.main())
