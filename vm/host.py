#!/usr/bin/env -S python3 -u

import argparse
import sys
import re
import subprocess
import socket
import math
import time
from pathlib import Path

GUEST_NAME_PREFIX = 'xen-benchmark-vm-'
GUEST_BASE_CFG = 'memory = 8192\n'
BENCHMARKS = ('timesyscall', 'timectxsw', 'timetctxsw', 'timetctxsw2')
SOCKET_PORT = 44544
REGEX_STR = (
    r'\|( |X)\|    '
    r'\[(?P<num_vms>4VM|13VM)\]'
    r'\[(?P<virt_method>pv|hvm|pvh)\]'
    r'\[(?P<vcpu_pinning>(pinning\-(on|off))|null\-pinning)\]'
    r'\[(?P<taskset>taskset\-(on|off))\]'
    r'\[(?P<scheduler>(credit2\-(1ms|3ms|10ms))|null)\]'
    r'\[(?P<hyperthreading>ht\-(on|off))\]'
    r'\[(?P<mem_management>hap|shadow|pv\-mmu)\]'
    r'\[(?P<dom0_cpus>dom0\-(all\-cpus|less\-cpus|less\-cpus\-pinned|null\-pinning))\]'
    r'\[(?P<slop>(default|low)\-slop)\]'
)

host_cpus = 52

# Directory that this script resides in
prog_dir = Path(__file__).parent

guest_cfg_dir = prog_dir / 'guest-cfgs'

# List of MACs from file
mac_list = (prog_dir / 'macs.txt').read_text().splitlines()

def bicond(a, b):
    return (a and b) or (not a and not b)

def get_online_guests(guest_statuses):
    return {name:status for name, status in guest_statuses.items() if status != 'X'}

def wait_on_guest_messages(expected_message, guest_statuses):
    print_guest_status(guest_statuses)
    while not all(status==expected_message for status in get_online_guests(guest_statuses).values()):
        # print('Guest statuses: ', guest_statuses)
        message, (ip_addr, _) = host_socket.recvfrom(1024)

        # print(f'wait_on_message got -> {message} ({message.decode("utf-8")})')
        # print(f'expected message was {expected_message}')
        # print(f'ip address is {ip_addr}')

        if message.decode('utf-8') == expected_message:
            # print(f'ip address is {ip_addr}!')
            # This will catch any READYs that come from a domain as they're being shut down
            try:
                guest_hostname, _, _ = socket.gethostbyaddr(ip_addr)
            except socket.herror:
                continue
            # print(guest_hostname)
            guest_hostname = guest_hostname.split('.')[0]
            if guest_hostname in guest_statuses:
                guest_statuses[guest_hostname] = expected_message
                print_guest_status(guest_statuses)

def send_message_to_guests(message, guest_statuses):
    for guest in get_online_guests(guest_statuses).keys():
        guest_hostname = socket.gethostbyname(guest)
        host_socket.sendto(bytes(message, 'utf-8'), (guest_hostname, SOCKET_PORT))

def wait_on_message(expected_message):
    matches = False
    while not matches:
        message, _ = host_socket.recvfrom(1024)
        # print(f'wait_on_message got -> {message} ({message.decode("utf-8")})')
        # print(f'expected message was {expected_message}')
        matches = (message.decode('utf-8') == expected_message)
        
def print_guest_status(guest_statuses):
    # Since Python 3.7, dict order is guaranteed to be insertion order
    status_string = ' '.join([s[0].capitalize() for s in guest_statuses.values()])
    print(f'Guest status: [{status_string}]', end='\r')

def attempt_shutdown(name, ensure=False):
    try:
        subprocess.run(['xl', 'shutdown', '--wait', name], timeout=120)
    except subprocess.TimeoutExpired:
        print(f'Failed to shutdown domain "{name}". Destroying...')
        subprocess.run(['xl', 'destroy', name])
    if ensure:
        time.sleep(30)

####  Main program  ################################################################################
#--------------------------------------------------------------------------------------------------#

parser = argparse.ArgumentParser()

# Positional args
parser.add_argument(
    'image_directory', metavar='image-directory', type=Path, 
    help='path to directories for all guest images')
parser.add_argument(
    'benchmark_list', metavar='benchmark-list', type=Path,
    help='file containing list of remaining benchmarks')

# Optional args
parser.add_argument(
    '--low-slop', action='store_true', 
    help='TIMER_SLOP has been decreased')
parser.add_argument(
    '--overcommit', action='store_true', 
    help='run twice as many vcpus as pcpus')
parser.add_argument(
    '--ht', action='store_true', 
    help='hyperthreading is enabled')
parser.add_argument(
    '--no-hvm', action='store_true',
    help='do not start HVM domains')
parser.add_argument(
    '--config-only', action='store_true', 
    help='don\'t run benchmark, just create config files')

# Mutually exclusive args
mut_group = parser.add_mutually_exclusive_group()
mut_group.add_argument(
    '--null', action='store_true', 
    help='null scheduler is active')
mut_group.add_argument(
    '--less-dom0-cpus', choices=['pinning-on', 'pinning-off'], 
    help='dom0 cpus have been restricted')

args = parser.parse_args()

#--------------------------------------------------------------------------------------------------#

# Check paths are valid
if not args.image_directory.is_dir():
    sys.exit('Invalid image path specified')
if not args.benchmark_list.is_file():
    sys.exit('Invalid benchmark list specified')

# Read list of benchmarks from file
benchmark_list = args.benchmark_list.read_text().splitlines()

#--------------------------------------------------------------------------------------------------#

# Create and bind socket for communication with guests
host_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
host_socket.bind(('0.0.0.0', SOCKET_PORT))

#--------------------------------------------------------------------------------------------------#

# Run benchmark for each benchmark in the list
for lineno, benchmark in enumerate(benchmark_list):

    # Ignore any blank lines
    if benchmark in ('', '\n'):
        continue

    # Check benchmark string is well formed
    re_match = re.fullmatch(REGEX_STR, benchmark)
    if re_match is None:
        sys.exit('Invalid benchmark string')

    # Extract regex groups into dictionary
    m = re_match.groupdict()

    # Ignore benchmarks that have already been run
    if benchmark.startswith('|X|'):
        continue

    if args.no_hvm and m['virt_method'] == 'hvm':
        continue

    # Ignore benchmarks that cannot be run because of current hypervisor configuration
    # For example, do not run null-scheduler benchmarks when credit2-scheduler is active
    if not bicond(args.null, m['scheduler'] == 'null'):
        continue
    if not bicond(args.low_slop, m['slop'] == 'low-slop'):
        continue
    if not bicond(args.less_dom0_cpus == 'pinning-on', m['dom0_cpus'] == 'dom0-less-cpus-pinned'):
        continue
    if not bicond(args.less_dom0_cpus == 'pinning-off', m['dom0_cpus'] == 'dom0-less-cpus'):
        continue
    if not bicond(args.ht, m['hyperthreading'] == 'ht-on'):
        continue

    #----------------------------------------------------------------------------------------------#

    # Delete old guest configs
    for vm_cfg in guest_cfg_dir.glob(GUEST_NAME_PREFIX + '*.cfg'):
        vm_cfg.unlink()

    # Number of vCPUs to assign to each guest
    if m['num_vms'] == '4VM':
        guest_vcpus = 13
    elif m['num_vms'] == '13VM':
        guest_vcpus = 4

    if m['dom0_cpus'] in ('dom0-less-cpus-pinned', 'dom0-null-pinning'):
        num_vms = (host_cpus - 8) // guest_vcpus
        first_guest_vcpu = math.ceil(8 / guest_vcpus) * guest_vcpus
    else:
        num_vms = host_cpus // guest_vcpus
        first_guest_vcpu = 0

    # Double these values if SMT is enabled
    if m['hyperthreading'] == 'ht-on':
        guest_vcpus *= 2
        host_cpus *= 2

    for vm_number, lowest_vcpu in enumerate(range(first_guest_vcpu, host_cpus, guest_vcpus)):
        vm_name = GUEST_NAME_PREFIX + str(vm_number+1)
        image = 'hvm-disk.raw,hda1' if m['virt_method'] == 'hvm' else 'disk.img,xvda2'
        mac_offset = 13 if m['virt_method'] == 'hvm' else 0

        # Configuration that all VMs need
        common_cfg = (
            f'\n#{benchmark.removeprefix("| |    ")}\n'
            f'name = \'{vm_name}\'\n'
            f'type = \'{m["virt_method"]}\'\n'
            f'vcpus = {guest_vcpus}\n'
            f'vif = [\'mac={ mac_list[vm_number+mac_offset] }\']\n'
            f'disk = [\'file:{args.image_directory/vm_name}/{image},w\']\n'
        )

        # Additional config depending on choice of PV, HVM, PVH
        type_specific_cfg = ''
        if m['virt_method'] == 'hvm':
            type_specific_cfg += 'firmware = \'bios\'\n'
            type_specific_cfg += 'serial = [\'pty\']\n'
        if m['virt_method'] in ('pv', 'pvh'):
            type_specific_cfg += 'bootloader = \'pygrub\'\n'
        if m['virt_method'] == ('hvm', 'pvh'):
            type_specific_cfg += f'hap = {int(m["mem_management"] == "hap")}\n'

        # Pin CPUs if pinning is enabled (cpu string is range inclusive)
        if m['vcpu_pinning'] == 'pinning-on':
            type_specific_cfg += f'cpus = \'{lowest_vcpu}-{lowest_vcpu+guest_vcpus-1}\'\n'

        # Write new config to file 
        new_guest_cfg = GUEST_BASE_CFG + common_cfg + type_specific_cfg
        (guest_cfg_dir / (vm_name+'.cfg')).write_text(new_guest_cfg)

    #----------------------------------------------------------------------------------------------#

    # Stop here if --config-only flag is provided
    if args.config_only:
        print('Wrote guest configs. Exiting...')
        sys.exit(0)

    vm_1_name = GUEST_NAME_PREFIX+'1'
    print(vm_1_name + ' is defined by the following xl config:')
    print((guest_cfg_dir/(vm_1_name+'.cfg')).read_text())

    # Determine host ratelimit
    if m['scheduler'] == 'credit2-1ms':
        ratelimit = 1000
    elif m['scheduler'] == 'credit2-3ms':
        ratelimit = 3000
    elif m['scheduler'] == 'credit2-10ms':
        ratelimit = 10000

    remaining = '\n'.join(benchmark_list).count('| |')
    print(f'Beginning new benchmark ({remaining} remaining)...')

    print('Setting ratelimit...')
    # Set ratelimit
    subprocess.run(['xl', 'sched-credit2', '--schedparam', f'--ratelimit_us={ratelimit}'])

    print('Starting guests...')
    # Start all new guests
    for vm_cfg in [guest_cfg_dir/f'{GUEST_NAME_PREFIX}{i}.cfg' for i in range(1, num_vms+1)]:
        subprocess.run(['xl', 'create', str(vm_cfg)])
        
    #----------------------------------------------------------------------------------------------#
    
    guest_statuses = {f'{GUEST_NAME_PREFIX}{i}' : '?' for i in range(1,num_vms+1)}
    
    for num_open_vms in range(num_vms, 0, -1):
        for executable in BENCHMARKS:
            wait_on_guest_messages('READY', guest_statuses)

            print('\nAll guests ready! Starting benchmarks...')

            start_command = f'START {executable} {num_open_vms} {m["taskset"]} {benchmark}'
            send_message_to_guests(start_command, guest_statuses)

            wait_on_guest_messages('FINISHED', guest_statuses)
            print('\nAll guests finished! Uploading files...')

            # Prevents UPLOADED from getting mixed in with FINISH if VM1 finishes quickly
            send_message_to_guests('CONTINUE', guest_statuses)

            wait_on_message('UPLOADED')
            print('Upload finished!')

            send_message_to_guests('RESET', guest_statuses)
            
        if num_open_vms > 1:
            name = f'{GUEST_NAME_PREFIX}{num_open_vms}'
            attempt_shutdown(name)
            guest_statuses[name] = 'X'
        
    print('Benchmark suite complete!')
    attempt_shutdown(GUEST_NAME_PREFIX + '1', ensure=True)

    print('Updating benchmark list...')
    benchmark_list[lineno] = benchmark_list[lineno].replace('| |', '|X|')
    with open(args.benchmark_list, 'w') as f:
        f.writelines('\n'.join(benchmark_list))

host_socket.close()
