# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# originally copied from  module to bring this functionality
# into Core

#from __future__ import annotations


DOCUMENTATION = r'''
---
module: sas_multipath_facts
short_description: Return list of SAS disks sorted by controllers.
description:
     - Returns list of SAS disks sorted in two groups by controllers (primary, secondary).
     - The module also returns a variable to be used as user_friendly_name in dm-multipath.
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
        self.ctrls = {}
        self.jbods = {}
        self.ctrl_glob = glob.glob("/sys/devices/*/*/*/", recursive=True)

    def gather_controllers(self):
        ctrl_class = "0x010700"
        for path in self.ctrl_glob:
            try:
                with open(os.path.join(path, "class"), "r") as f:
                    device_class = f.readline().rstrip()
                    if device_class == ctrl_class:
                        self.ctrls[path] = {}
                    f.close()
            except FileNotFoundError:
                pass

    def gather_jbods(self):
        for ctrl in self.ctrls:
            for port in self.ctrls[ctrl]:
                for jbod in glob.glob(os.path.join(port, 'expander-*/port-*0/end_device*/target*/*:*/'), recursive=True):
                    try:
                        with open(os.path.join(jbod, "wwid"), "r") as f:
                            wwid = f.readline().rstrip().replace("naa.", "3")
                            self.ctrls[ctrl][port] = { "jbod": wwid }
                            self.jbods.setdefault(wwid, {"ports": []})
                            self.jbods[wwid]["ports"] += [jbod]
                            f.close()
                    except FileNotFoundError:
                        pass

    def add_controller_ports(self):
        for ctrl in self.ctrls:
            for port in glob.glob(os.path.join(ctrl, 'host*/port-*'), recursive=True):
                self.ctrls[ctrl][port] = {}

    def gather_disks_by_jbods(self):
        for jbod in self.jbods:
            disk_basepath = os.path.normpath(self.jbods[jbod]["ports"][0]).rsplit(os.sep, maxsplit=4)[0]
            disk_glob = os.path.join(disk_basepath, "port-*/expander*/port-*/end_device-*/target*/*:*/")
            for disk_path in glob.glob(disk_glob):
                try:
                    with open(os.path.join(disk_path, "wwid"), "r") as f:
                        wwid = f.readline().rstrip().replace("naa.", "3")
                        self.jbods[jbod].setdefault("disks", [])
                        self.jbods[jbod]["disks"].append({'wwid': wwid,
                                                         'path': disk_path
                                                          })
                        f.close()
                except FileNotFoundError:
                    pass

    def assign_jbod_role(self, primary="xxx.0000000000000000", secondary="xxx.0000000000000000"):
        # check if JBOD present
        self.primary = primary
        self.secondary = secondary
        for jbod in self.jbods:
            if jbod == self.primary:
                self.jbods[jbod]["role"] = "primary"
            elif jbod == self.secondary:
                self.jbods[jbod]["role"] = "secondary"
            else:
                self.jbods[jbod]["role"] = "unknown"


def main():
    argument_spec = dict(
        primary=dict(type='str'),
        secondary=dict(type='str')
    )

    module = AnsibleModule(
            argument_spec=argument_spec,
            supports_check_mode=True,
            required_together=[
                ['primary', 'secondary'],
            ]
    )

    sas_jbods = SAS_JBODS(module)
    sas_jbods.gather_controllers()
    sas_jbods.add_controller_ports()
    sas_jbods.gather_jbods()
    if module.params['primary'] and module.params['secondary']:
        sas_jbods.assign_jbod_role(primary = module.params['primary'],
                                   secondary = module.params['secondary']
                                  )
    else:
        sas_jbods.assign_jbod_role()
    sas_jbods.gather_disks_by_jbods()

    if len(sas_jbods.ctrls) == 0:
        results = dict(skipped=True,
                       msg="Failed to find any SAS controllers. \
                            This can be due to privileges or some other configuration issue."
                        )
    else:
        results = dict(ansible_facts=dict(sas_jbods=sas_jbods.jbods, sas_ctrls=sas_jbods.ctrls))
    module.exit_json(**results)


if __name__ == '__main__':
    main()
