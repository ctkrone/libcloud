Compute Examples
================

Example: Creating a Node
------------------------

.. literalinclude:: /examples/compute/create_node.py
   :language: python

Example: List Nodes Across Multiple Providers
---------------------------------------------

.. literalinclude:: /examples/compute/list_nodes_across_multiple_providers.py
   :language: python

Example: Bootstrapping Puppet on a Node
---------------------------------------

.. literalinclude:: /examples/compute/bootstrapping_puppet_on_node.py
   :language: python

Create an OpenStack node using trystack.org provider
----------------------------------------------------

`trystack.org`_ allows users to try out OpenStack for free. This example
demonstrates how to launch an OpenStack node on the ``trystack.org`` provider
using a generic OpenStack driver.

.. literalinclude:: /examples/compute/trystack.py
   :language: python

.. _`trystack.org`: http://trystack.org/

Create an OpenStack node using a local OpenStack provider
---------------------------------------------------------

This example shows how to create a node using a local OpenStack installation.
Don't forget to replace ``your_auth_username``, ``your_auth_password`` and
``ex_force_auth_url`` with the correct values specific to your installation.

.. note::
    This example works with Libcloud version 0.9.0 and above.

.. literalinclude:: /examples/compute/openstack_simple.py
   :language: python

Create a VMware vCloud v1.5 node using generic provider
-------------------------------------------------------

This example demonstrates how to launch a VMware vCloud v1.5 node on a
generic provider such as a test lab.

.. note::
    This example works with Libcloud version 0.10.1 and above.

.. literalinclude:: /examples/compute/vmware_vcloud_1.5.py
   :language: python
