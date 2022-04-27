import pathlib
import numpy as np
import zipfile
from matplotlib import pyplot as plt

program_dir = pathlib.Path(__file__).parent

NUM_VMS = 13
NUM_VCPUS = 4
BENCHMARK = 'timectxsw'

def reject_outliers(data, m=2):
    return data[abs(data - np.mean(data)) < m * np.std(data)]

def bicond(a, b):
    return (a and b) or (not a and not b)

means = np.zeros(NUM_VMS)
medians = np.zeros(NUM_VMS)

combinations = [
    (num_vms, virt_type, pinning, taskset, scheduler, mem_management, slop) 
    for num_vms in ('13VM',)
    for virt_type in ('pv',)
    for pinning in ('pinning-on',)
    for taskset in ('taskset-on',)
    for scheduler in ('credit2-1ms', 'credit2-10ms')
    for mem_management in ('pv-mmu',)
    for slop in ('default-slop',)
    if bicond(virt_type == 'pv', mem_management == 'pv-mmu')
]

legends = []

kernel_size = 1000


for num_vms, virt_type, pinning, taskset, scheduler, mem_management, slop in combinations:

    # for vm_count in range(1, NUM_VMS+1):
    for vm_count in range(13, 14):

        benchmark_name = f'({num_vms})({virt_type})({pinning})({taskset})({scheduler})(ht-off)({mem_management})(dom0-all-cpus)({slop})'
        with zipfile.ZipFile(program_dir.parent / benchmark_name / str(vm_count) / f'{BENCHMARK}.zip', mode='r', compression=zipfile.ZIP_DEFLATED) as zf:

            per_core_means = np.zeros(NUM_VCPUS)
            # per_core_medians = np.zeros(NUM_VCPUS)
            
            for i in range(NUM_VCPUS):
                with zf.open(f'{BENCHMARK}{i}.out') as f:
                    plot_name = f'{scheduler}'
                    print(plot_name)
                    legends.append(plot_name)
                    result_bytes = f.read()
                    time = np.frombuffer(result_bytes, dtype=np.int64, count=1)[0]
                    print(time)
                    result_array = np.frombuffer(result_bytes, dtype=np.uint32, offset=8)[::1]

                    print(len(result_array))

                    # print(len(result_array), result_array[0:100].reshape(20,5).tolist())


                    # result_array = reject_outliers(result_array)

                    # print(len(result_array), result_array[0:100].reshape(20,5).tolist())


                    # per_core_means[i] = np.mean(result_array)

                    kernel = np.ones(kernel_size) / kernel_size
                    data_convolved = np.convolve(result_array, kernel, mode='same')

                    plt.plot(np.linspace(0, time, len(data_convolved)), data_convolved, linewidth=0.5)

                    # per_core_medians[i] = np.median(result_array)
        means[vm_count-1] = np.mean(per_core_means)
        # medians[vm_count-1] = np.mean(per_core_medians)

    # plt.plot(range(1, NUM_VMS+1), means)
    # plt.plot(range(1, NUM_VMS+1), medians)

# plt.ylim(bottom=2700, top=3200)
plt.legend(legends)

# plt.show()

plt.savefig(program_dir / 'figs' / f'pvh-default-tsc-hap{BENCHMARK}.png', dpi=500)



'''
Okay, should only compare one variable at a time.
The whole idea is to reduce the number of benchmarks that I need to run.

hap vs shadow are two big ones
Could do hap vs shadow, then do all combinations of what remains










'''