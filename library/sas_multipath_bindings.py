# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# originally copied from  module to bring this functionality
# into Core

#from __future__ import annotations


DOCUMENTATION = r'''
---
module: sas_multipath_facts
short_description: Return list of SAS disks sorted by controllers.
description:
     - Returns list of SAS disks sorted in two groups by controllers (primary, secondary). The module also returns a variable to be used as user_friendly_name in dm-multipath.
version_added: "2.15"
requirements: ["Device Mapper Multipath on Linux kernel with sysfs and exactly two SAS controllers"]
attributes:
    check_mode:
        support: full
    diff_mode:
        support: none
    facts:
        support: full
    platform:
        platforms: linux
notes:
  - When accessing the RV(ansible_facts.dm_multipath_facts) facts collected by this module,
    it is recommended to not use "dot notation" because services can have a C(-)
    character in their name which would result in invalid "dot notation", such as
    C(ansible_facts.services.zuul-gateway). It is instead recommended to
    using the string value of the service name as the key in order to obtain
    the fact data value like C(ansible_facts.services['zuul-gateway'])
author:
  - Benedikt Braunger (@zsn342)
'''

EXAMPLES = r'''
- name: Populate SAS multipath facts
  ansible.builtin.sas_multipath_facts:

- name: Print service facts
  ansible.builtin.debug:
    var: ansible_facts.sas_multipath_facts
'''

#RETURN = r'''
#ansible_facts:
#  description: Facts to add to ansible_facts about the services on the system
#  returned: always
#  type: complex
#  contains:
#    services:
#      description: States of the services with service name as key.
#      returned: always
#      type: list
#      elements: dict
#      contains:
#        source:
#          description:
#          - Init system of the service.
#          - One of V(rcctl), V(systemd), V(sysv), V(upstart), V(src).
#          returned: always
#          type: str
#          sample: sysv
#'''


import os
import glob
from ansible.module_utils.basic import AnsibleModule


class SAS_JBODS(object):

    def __init__(self, module):
        self.module = module

    def gather_controllers(self):
        controllers = {}
        ctrl_class = "0x010700"
        for path in glob.glob("/sys/devices/*/*/*/", recursive=True):
            try:
                with open(os.path.join(path, "class"), "r") as f:
                    device_class = f.readline().rstrip()
                    if device_class == ctrl_class:
                        ctrls[path] = {}
                    f.close()
            except FileNotFoundError:
                pass
        return controllers

    def gather_jbods(self):
        jbods = {}
        for ctrl in ctrls:
            for port in ctrls[ctrl]:
                for jbod in glob.glob(os.path.join(port, 'expander-*/port-*0/end_device*/target*/*:*/'), recursive=True):
                    try:
                        with open(os.path.join(jbod, "wwid"), "r") as f:
                            wwid = f.readline().rstrip()
                            ctrls[ctrl][port] = { "JBOD": wwid }
                            jbods.setdefault(wwid, {"ports": []})
                            jbods[wwid]["ports"] += [jbod]
                            f.close()
                    except FileNotFoundError:
                        pass
        return jbods

    def add_controller_ports(self):
        for ctrl in ctrls:
            for port in glob.glob(os.path.join(ctrl, 'host*/port-*'), recursive=True):
                ctrls[ctrl][port] = {}


def main():
    module = AnsibleModule(argument_spec=dict(), supports_check_mode=True)
    controllers = {}
    jbods_with_disks = {}

    module_args = dict(
            primary=dict(type='string', required=False, default=False),
            secondary=dict(type='string', required=False, default=False)
    )

    controllers = gather_controllers()

    if len(controllers) == 0:
        results = dict(skipped=True, msg="Failed to find any SAS controllers. This can be due to privileges or some other configuration issue.")
    else:
        results = dict(ansible_facts=dict(sas_jbods=jbods_with_disks))
    module.exit_json(**results)


if __name__ == '__main__':
    main()
