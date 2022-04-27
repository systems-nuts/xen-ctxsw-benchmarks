import pathlib
import zipfile
import argparse
import pandas as pd
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.ticker import AutoMinorLocator

program_dir = pathlib.Path(__file__).parent

parser = argparse.ArgumentParser(description='Generate graphs from test data.')

# Positional args
parser.add_argument(
    'benchmark_data', metavar='benchmark-data', type=pathlib.Path,
    help='path to benchmark data')
parser.add_argument(
    'benchmark_name', metavar='benchmark-name', 
    help='name of benchmark to analyse (timesyscall, timectxsw etc.)')

args = parser.parse_args()

benchmarks_with_iterations = {
    'timesyscall' : 10_000_000, 
    'timectxsw'   :    500_000, 
    'timetctxsw'  :    500_000, 
    'timetctxsw2' :    500_000
}

def get_subdirs(path):
    assert path.is_dir() == True
    return [x for x in path.iterdir() if x.is_dir()]

def generate_graph(path, benchmark_name):
    number_of_vms = len(tuple(path.iterdir()))
    number_of_data_points = benchmarks_with_iterations[benchmark_name]

    rdtsc_readings = np.ndarray(shape=(number_of_data_points, number_of_vms), dtype=np.int32)
    combined_exec_times = np.zeros(number_of_vms, dtype=np.int64)

    print('VM: ', end=' ')
    for benchmark_pass in range(number_of_vms):
        print(benchmark_pass+1, end=' ')
        zip_path = path/f'{benchmark_pass+1}/{benchmark_name}.zip'
        with zipfile.ZipFile(zip_path, mode='r', compression=zipfile.ZIP_DEFLATED) as zf:
            num_benchmark_processes = len(zf.namelist())
            for process_num in range(num_benchmark_processes):
                with zf.open(f'{benchmark_name}{process_num}.out') as b:
                    raw_bytes = b.read()
                # Read the clock_gettime execution time, [0] because singleton array
                combined_exec_times[benchmark_pass] += (np.frombuffer(raw_bytes, dtype=np.int64, count=1)[0] // num_benchmark_processes)
                # Read all rdtsc readings, offset is 8 to avoid reading 64-bit clock_gettime at beginning of file
                rdtsc_readings[:,benchmark_pass] += np.frombuffer(raw_bytes, dtype=np.int32, offset=8)
        rdtsc_readings[:,benchmark_pass] //= num_benchmark_processes
        
    
    print('Plotting and saving...')

    column_labels =[f'{i+1}VM' for i in range(number_of_vms)]
    df = pd.DataFrame(rdtsc_readings, columns=column_labels)
    df = pd.DataFrame({'mean' : df.mean(), 'median' : df.median()})
    ax = df.plot.bar()
    ax.yaxis.set_minor_locator(AutoMinorLocator())
    plt.savefig(program_dir/f'figs/{benchmark_name}/rdtsc-{path.stem}.png', dpi=300)
    plt.close()
    
    df = pd.DataFrame(combined_exec_times, index=column_labels)
    ax = df.plot.bar()
    ax.yaxis.set_minor_locator(AutoMinorLocator())
    plt.savefig(program_dir/f'figs/{benchmark_name}/clock_gettime-{path.stem}.png', dpi=300)
    plt.close()

for benchmark_suite in get_subdirs(args.benchmark_data):
    if (program_dir/f'figs/{args.benchmark_name}/clock_gettime-{benchmark_suite.stem}.png').exists():
        print(f'Skipping {benchmark_suite.stem}')
        continue
    if (program_dir/f'figs/{args.benchmark_name}/rdtsc-{benchmark_suite.stem}.png').exists():
        print(f'Skipping {benchmark_suite.stem}')
        continue
    if benchmark_suite.stem[0] != '(':
        print(f'Skipping {benchmark_suite.stem}')
        continue
    generate_graph(benchmark_suite, args.benchmark_name)


        



