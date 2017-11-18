#!/usr/bin/python
#
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}


DOCUMENTATION = """
---
module: asa_command
version_added: "2.2"
author: "Peter Sprygada (@privateip), Patrick Ogenstad (@ogenstad)"
short_description: Run arbitrary commands on Cisco ASA devices
description:
  - Sends arbitrary commands to an ASA node and returns the results
    read from the device. The C(asa_command) module includes an
    argument that will cause the module to wait for a specific condition
    before returning or timing out if the condition is not met.
extends_documentation_fragment: asa
options:
  commands:
    description:
      - List of commands to send to the remote device over the
        configured provider. The resulting output from the command
        is returned. If the I(wait_for) argument is provided, the
        module is not returned until the condition is satisfied or
        the number of retires as expired.
    required: true
  wait_for:
    description:
      - List of conditions to evaluate against the output of the
        command. The task will wait for each condition to be true
        before moving forward. If the conditional is not true
        within the configured number of retries, the task fails.
        See examples.
    required: false
    default: null
    aliases: ['waitfor']
  match:
    description:
      - The I(match) argument is used in conjunction with the
        I(wait_for) argument to specify the match policy.  Valid
        values are C(all) or C(any).  If the value is set to C(all)
        then all conditionals in the wait_for must be satisfied.  If
        the value is set to C(any) then only one of the values must be
        satisfied.
    required: false
    default: all
    choices: ['any', 'all']
  retries:
    description:
      - Specifies the number of retries a command should by tried
        before it is considered failed. The command is run on the
        target device every retry and evaluated against the
        I(wait_for) conditions.
    required: false
    default: 10
  interval:
    description:
      - Configures the interval in seconds to wait between retries
        of the command. If the command does not pass the specified
        conditions, the interval indicates how long to wait before
        trying the command again.
    required: false
    default: 1
"""

EXAMPLES = """
# Note: examples below use the following provider dict to handle
#       transport and authentication to the node.
---
vars:
  cli:
    host: "{{ inventory_hostname }}"
    username: cisco
    password: cisco
    authorize: yes
    auth_pass: cisco
    transport: cli

---
- asa_command:
    commands:
      - show version
    provider: "{{ cli }}"

- asa_command:
    commands:
      - show asp drop
      - show memory
    provider: "{{ cli }}"

- asa_command:
    commands:
      - show version
    provider: "{{ cli }}"
    context: system
"""

RETURN = """
stdout:
  description: the set of responses from the commands
  returned: always
  type: list
  sample: ['...', '...']

stdout_lines:
  description: The value of stdout split into a list
  returned: always
  type: list
  sample: [['...', '...'], ['...'], ['...']]

failed_conditions:
  description: the conditionals that failed
  returned: failed
  type: list
  sample: ['...', '...']
"""
import time

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.asa import asa_argument_spec, check_args
from ansible.module_utils.asa import run_commands
from ansible.module_utils.netcli import Conditional
from ansible.module_utils.six import string_types


def to_lines(stdout):
    for item in stdout:
        if isinstance(item, string_types):
            item = str(item).split('\n')
        yield item


def main():
    spec = dict(
        # { command: <str>, prompt: <str>, response: <str> }
        commands=dict(type='list', required=True),

        wait_for=dict(type='list', aliases=['waitfor']),
        match=dict(default='all', choices=['all', 'any']),

        retries=dict(default=10, type='int'),
        interval=dict(default=1, type='int')
    )

    spec.update(asa_argument_spec)

    module = AnsibleModule(argument_spec=spec, supports_check_mode=True)
    check_args(module)

    result = {'changed': False}

    wait_for = module.params['wait_for'] or list()
    conditionals = [Conditional(c) for c in wait_for]

    commands = module.params['commands']
    retries = module.params['retries']
    interval = module.params['interval']
    match = module.params['match']

    while retries > 0:
        responses = run_commands(module, commands)

        for item in list(conditionals):
            if item(responses):
                if match == 'any':
                    conditionals = list()
                    break
                conditionals.remove(item)

        if not conditionals:
            break

        time.sleep(interval)
        retries -= 1

    if conditionals:
        failed_conditions = [item.raw for item in conditionals]
        msg = 'One or more conditional statements have not be satisfied'
        module.fail_json(msg=msg, failed_conditions=failed_conditions)


    result.update({
        'changed': False,
        'stdout': responses,
        'stdout_lines': list(to_lines(responses))
    })

    module.exit_json(**result)


if __name__ == '__main__':
    main()
