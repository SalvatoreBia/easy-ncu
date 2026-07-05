import sys
import os
import configparser
import cli_views


debug = True
ncu_path = None


def load_configs():
    global ncu_path
    config = configparser.ConfigParser()
    if not os.path.exists('config.cfg'):
        print('[ERROR] config.cfg file not found.')
        return    
    try:
        config.read('config.cfg')
        ncu_path = config.get('DEFAULT', 'NcuPythonPath', fallback=None)
    except Exception as e:
        print('[ERROR] Error reading config.cfg')
        return
    
    if debug:
        print(f'[DEBUG] ncu_path set to: {ncu_path}')

    if ncu_path and os.path.exists(ncu_path):
        if ncu_path not in sys.path:
            sys.path.append(ncu_path)
        os.environ['LD_LIBRARY_PATH'] = ncu_path + ':' + os.environ.get('LD_LIBRARY_PATH', '')
        if debug:
            print('[DEBUG] Python environment and LD_LIBRARY_PATH updated')


load_configs()
if not ncu_path or not os.path.exists(ncu_path):
    print('[ERROR] ncu_path is incorrect. Add or correct the entry \'NcuPythonPath\' in config.cfg')
    sys.exit(1)

try:
    import ncu_report
except ImportError as e:
    print('[ERROR] Couldn\'t import ncu_report library. Check for \'NcuPythonPath\' correctness in config.cfg')
    sys.exit(1)


def empty_metric():
    return { 'value': None, 'unit': None }


def get_metric(action, readable_name, metric_name):
    if metric_name in action.metric_names():
        metric = action.metric_by_name(metric_name)
        return { 'name': readable_name, 'value': metric.value(), 'unit': metric.unit() }
    return empty_metric()

################################################
#
#       SPEED OF LIGHT
#
################################################

def get_SoL_kernel_duration(action):
    return get_metric(action, 'Duration', 'gpu__time_duration.sum')

def get_SoL_compute_sm(action):
    return get_metric(action, 'Compute (SM) throughput', 'sm__throughput.avg.pct_of_peak_sustained_elapsed')

def get_SoL_memory_throughput(action):
    return get_metric(action, 'Memory throughput', 'gpu__compute_memory_throughput.avg.pct_of_peak_sustained_elapsed')

def get_SoL_elapsed_cycles(action):
    return get_metric(action, 'Elapsed cycles', 'gpc__cycles_elapsed.max')

def get_SoL_L1_throughput(action):
    return get_metric(action, 'L1/TEX cache throughput', 'l1tex__throughput.avg.pct_of_peak_sustained_active')

def get_SoL_sm_active_cycles(action):
    return get_metric(action, 'SM active cycles', 'sm__cycles_active.avg')

def get_SoL_L2_throughput(action):
    return get_metric(action, 'L2 cache throughput', 'lts__throughput.avg.pct_of_peak_sustained_elapsed')

def get_SoL_sm_frequency(action):
    return get_metric(action, 'SM frequency', 'gpc__cycles_elapsed.avg.per_second')

def get_SoL_dram_throughput(action):
    return get_metric(action, 'DRAM throughput', 'gpu__dram_throughput.avg.pct_of_peak_sustained_elapsed')

def get_SoL_dram_frequency(action):
    return get_metric(action, 'DRAM frequency', 'dram__cycles_elapsed.avg.per_second')

def show_SpeedOfLight(action):
    sol_metrics = {
        'duration': get_SoL_kernel_duration(action),
        'sm_sol': get_SoL_compute_sm(action),
        'mem_sol': get_SoL_memory_throughput(action),
        'cycles': get_SoL_elapsed_cycles(action),
        'l1_sol': get_SoL_L1_throughput(action),
        'l2_sol': get_SoL_L2_throughput(action),
        'dram_sol': get_SoL_dram_throughput(action),
        'sm_freq': get_SoL_sm_frequency(action),
        'sm_active': get_SoL_sm_active_cycles(action),
        'dram_freq': get_SoL_dram_frequency(action)
    }
    cli_views.print_speed_of_light(action.name(), sol_metrics)

################################################
#
#       COMPUTE WORKLOAD ANALYSIS
#
################################################

def get_executed_ipc_elapsed(action):
    return get_metric(action, 'Executed Ipc elapsed', 'sm__inst_executed.avg.per_cycle_elapsed')

def get_executed_ipc_active(action):
    return get_metric(action, 'Executed Ipc active', 'sm__inst_executed.avg.per_cycle_active')

def get_issued_ipc_active(action):
    return get_metric(action, 'Issued Ipc active', 'sm__inst_issued.avg.per_cycle_active')

def get_sm_busy(action):
    return get_metric(action, 'SM busy', 'sm__instruction_throughput.avg.pct_of_peak_sustained_active')

def get_issue_slots_busy(action):
    return get_metric(action, 'Issue slots busy', 'sm__inst_issued.avg.pct_of_peak_sustained_active')

def show_compute_workload_analysis(action):
    compute_metrics = {
        'exec_ipc_elapsed': get_executed_ipc_elapsed(action),
        'exec_ipc_active': get_executed_ipc_active(action),
        'issued_ipc_active': get_issued_ipc_active(action),
        'sm_busy': get_sm_busy(action),
        'issue_slots_busy': get_issue_slots_busy(action)
    }
    cli_views.print_compute_workload(action.name(), compute_metrics)


################################################

def main():
    if len(sys.argv) != 2:
        print('[ERROR] Provide a valid .ncu-rep file')
        sys.exit(1)

    report = sys.argv[1]
    if not os.path.exists(report) or not report.endswith('.ncu-rep'):
        print(f'[ERROR] Report not found or invalid extension at: {report}')
        sys.exit(1)
    if debug:
        print(f'[DEBUG] Input report found at {report}')

    context = ncu_report.load_report(report)
    if debug:
        print('[DEBUG] ncu report loaded')

    irange = context.range_by_idx(0)
    action = irange.action_by_idx(0)
    show_SpeedOfLight(action)
    show_compute_workload_analysis(action)

if __name__ == '__main__':
    main()
