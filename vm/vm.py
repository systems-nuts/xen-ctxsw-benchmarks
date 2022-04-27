# VM Script

def match(xs, ys):
    matches = [x==y for x, y in zip(xs, ys)]
    return all(matches) or not any(matches)

virt_method_l     = ['pv', 'hvm', 'pvh']
vcpu_pinning_l    = ['pinning-on', 'pinning-off', 'null-pinning']
taskset_l         = ['taskset-on', 'taskset-off']
scheduler_l       = ['credit2-1ms', 'credit2-3ms', 'credit2-10ms', 'null']
mem_management_l  = ['hap', 'shadow', 'pv-mmu']
dom0_cpus_l       = ['dom0-all-cpus', 'dom0-less-cpus', 'dom0-less-cpus-pinned', 'dom0-null-pinning']
slop_l            = ['default-slop', 'low-slop']
hyperthreading_l  = ['ht-on', 'ht-off']
num_vms_l         = ['13VM', '4VM']

all_benchmarks = [
    f"| |    [{num_vms}][{virt_method}][{vcpu_pinning}][{taskset}][{scheduler}][{hyperthreading}][{mem_management}][{dom0_cpus}][{slop}]\n" 
    for slop in slop_l
    for dom0_cpus in dom0_cpus_l
    for mem_management in mem_management_l
    for hyperthreading in hyperthreading_l
    for scheduler in scheduler_l
    for taskset in taskset_l
    for vcpu_pinning in vcpu_pinning_l
    for virt_method in virt_method_l
    for num_vms in num_vms_l
    if match([scheduler, vcpu_pinning, dom0_cpus], ['null', 'null-pinning', 'dom0-null-pinning'])
    if match([virt_method, mem_management], ['pv', 'pv-mmu'])
]
    

with open('test-benchmarks', 'w') as f:
    f.writelines(all_benchmarks)




