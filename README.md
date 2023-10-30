# dm\_multipath

This roles installs and configures Linux `dm_multipath` driver to access 

## Role Variables

A description of the settable variables for this role should go here, including any variables that are in defaults/main.yml, vars/main.yml, and any variables that can/should be set via parameters to the role. Any variables that are read from other roles and/or the global scope (ie. hostvars, group vars, etc.) should be mentioned here as well.

## Example Playbook

Install dm-multipath and configure with defaults and ensure it's started:

```
...
    - hosts: all
      roles:
         - dm_multipath
```

## License

BSD-3-Clause

## Origin

This role is forked from [Cambridge Research Computing Services DM-Multipath Role](https://gitlab.developers.cam.ac.uk/rcs/platforms/infrastructure/ansible-roles/ansible-dm-multipath)
