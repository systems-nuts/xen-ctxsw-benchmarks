#!/usr/bin/env -S python3 -u

import socket
import subprocess
import re
import os
import multiprocessing
import zipfile
from pathlib import Path
from google.cloud import storage

HOST_NAME = 'xone'
SOCKET_PORT = 44544

my_hostname  = socket.gethostname()
my_address   = ('0.0.0.0', SOCKET_PORT)
host_address = (socket.gethostbyname(HOST_NAME), SOCKET_PORT)

prog_dir = Path(__file__).parent
benchmark_dir = prog_dir / 'benchmarks'
results_dir = prog_dir / 'results'

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(prog_dir / 'cred.json')
STORAGE_BUCKET_NAME = 'dissertation-benchmark-bucket'

is_vm1 = my_hostname.endswith('-1')
default_benchmarks = ('timesyscall', 'timectxsw', 'timetctxsw', 'timetctxsw2')

num_vcpus = multiprocessing.cpu_count()

def wait_on_command(regex_string):
    while True:
        message, _ = guest_socket.recvfrom(1024)
        print(message)
        if (match := re.fullmatch(regex_string, message.decode('utf-8'))):
            return match.groupdict()

def upload_file(filename, bucket_destination):
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(STORAGE_BUCKET_NAME)
    blob = bucket.blob(bucket_destination)
    blob.upload_from_filename(str(filename))

####  Main program  ################################################################################

# Create and bind guest socket
guest_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
guest_socket.bind(my_address)

print('Waiting on messages!')

while True:
    print('Either just started or got RESET, sending READY')
    # Send ready message to script on host
    guest_socket.sendto(bytes('READY', 'utf-8'), host_address)

    print('Waiting on START')
    # Block here until the 'START' message is received
    args = wait_on_command(
        r'START (?P<bench>.+) (?P<num_vms_open>\d+) (?P<params>.+) (?P<bench_string>\[.+\])')

    print('Got START! Starting benchmarks.')

    # Create as many processes as there are vcpus
    running_benchmarks = []
    for i in range(num_vcpus):
        parameters = [str(benchmark_dir/args['bench'])]
        # If vm1, pass name of destination file to benchmark program
        if is_vm1:
            parameters += [str(results_dir/(args['bench']+str(i)+'.out'))]
        benchmark = subprocess.Popen(parameters)
        running_benchmarks.append(benchmark)

    print('Setting affinity')

    # Set affinity of each process if required
    if (args['bench'] in default_benchmarks) and (args['params'] == 'taskset-on'):
        for benchmark in running_benchmarks:
            os.sched_setaffinity(benchmark.pid, range(num_vcpus))

    print('Waiting on benchmarks to finish')
    # Wait for benchmarks to complete
    for benchmark in running_benchmarks:
        benchmark.wait()

    print('Sending finished!')

    # Send finished message to host
    guest_socket.sendto(bytes('FINISHED', 'utf-8'), host_address)
    
    # Prevents UPLOADED from getting mixed in with FINISH if VM1 finishes quickly
    wait_on_command('CONTINUE')

    # If I'm VM 1, I need to upload file 
    if is_vm1:
        zip_path = results_dir/(args['bench']+'.zip')
        print('Compressing files')
        with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=5) as zf:
            for i in range(num_vcpus):
                results_path = results_dir/(args['bench']+str(i)+'.out')
                zf.write(results_path, results_path.name)
        cloud_bench_string = args["bench_string"].replace('[', '(') \
                                                 .replace(']', ')')
        cloud_path = f'{cloud_bench_string}/{args["num_vms_open"]}/{zip_path.name}'
        print('Uploading files')
        upload_file(zip_path, cloud_path)
        guest_socket.sendto(bytes('UPLOADED', 'utf-8'), host_address)
        print('Sent UPLOADED')

    print('Waiting on RESET')
    wait_on_command('RESET')

