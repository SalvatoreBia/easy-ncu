import sys
import os
import configparser
import cli_views
import cli_repl


debug = False
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


def empty_metric(readable_name):
    return { 'name': readable_name, 'value': None, 'unit': None }

def get_metric(action, readable_name, metric_name):
    if metric_name in action.metric_names():
        metric = action.metric_by_name(metric_name)
        return { 'name': readable_name, 'value': metric.value(), 'unit': metric.unit() }
    return empty_metric(readable_name)

def get_metric_fallback(action, readable_name, metric_names):
    for name in metric_names:
        if name in action.metric_names():
            metric = action.metric_by_name(name)
            return { 'name': readable_name, 'value': metric.value(), 'unit': metric.unit() }
    return empty_metric(readable_name)

def get_metric_avg(irange, readable_name, metric_name, start, count):
    total_val = 0.0
    valid_count = 0
    unit = None

    for i in range(start, start + count):
        if i >= irange.num_actions():
            break
        action = irange.action_by_idx(i)
        metric = get_metric(action, readable_name, metric_name)
        if metric['value'] is not None and isinstance(metric['value'], (int, float)):
            total_val += metric['value']
            valid_count += 1
            if not unit:
                unit = metric['unit']

    avg_val = total_val / valid_count if valid_count > 0 else 0.0
    return { 'name': f"Avg. {readable_name}", 'value': round(avg_val, 2), 'unit': unit }

def get_metric_fallback_avg(irange, readable_name, metric_names, start, count):
    target_name = None
    if irange.num_actions() > start:
        action = irange.action_by_idx(start)
        for name in metric_names:
            if name in action.metric_names():
                target_name = name
                break

    if not target_name:
        return empty_metric(readable_name)
    return get_metric_avg(irange, readable_name, target_name, start, count)

def get_range_metrics_summary(irange, start, count):
    metric_map = {
        'duration': 'gpu__time_duration.sum',
        'sm_sol': 'sm__throughput.avg.pct_of_peak_sustained_elapsed',
        'mem_sol': 'gpu__compute_memory_throughput.avg.pct_of_peak_sustained_elapsed',
        'cycles': 'gpc__cycles_elapsed.max',
        'l1_sol': 'l1tex__throughput.avg.pct_of_peak_sustained_active',
        'sm_active': 'sm__cycles_active.avg',
        'l2_sol': 'lts__throughput.avg.pct_of_peak_sustained_elapsed',
        'sm_freq': 'gpc__cycles_elapsed.avg.per_second',
        'dram_sol': 'gpu__dram_throughput.avg.pct_of_peak_sustained_elapsed',
        'dram_freq': 'dram__cycles_elapsed.avg.per_second',
        'exec_ipc_elapsed': 'sm__inst_executed.avg.per_cycle_elapsed',
        'exec_ipc_active': 'sm__inst_executed.avg.per_cycle_active',
        'issued_ipc_active': 'sm__inst_issued.avg.per_cycle_active',
        'sm_busy': 'sm__instruction_throughput.avg.pct_of_peak_sustained_active',
        'issue_slots_busy': 'sm__inst_issued.avg.pct_of_peak_sustained_active',
        'cycles_x_issued': 'smsp__average_warp_latency_per_inst_issued.ratio',
        'cycles_x_exec': 'smsp__average_warps_active_per_inst_executed.ratio',
        'th_occ': 'sm__maximum_warps_per_active_cycle_pct',
        'th_warps': 'sm__maximum_warps_avg_per_active_cycle',
        'ach_occ': 'sm__warps_active.avg.pct_of_peak_sustained_active',
        'ach_warps': 'sm__warps_active.avg.per_cycle_active',
        'block_regs': 'launch__occupancy_limit_registers',
        'block_shared': 'launch__occupancy_limit_shared_mem',
        'block_warps': 'launch__occupancy_limit_warps',
        'block_sm': 'launch__occupancy_limit_blocks',
        'dram_bw': 'dram__bytes.sum.per_second',
        'l2_sectors': 'lts__t_sectors.sum',
        'l1_sectors_ld': 'l1tex__t_sectors_pipe_lsu_mem_global_op_ld.sum',
        'l1_sectors_st': 'l1tex__t_sectors_pipe_lsu_mem_global_op_st.sum'
    }
    
    fallback_maps = {
        'active_threads': ['smsp__thread_inst_executed_per_inst_executed.ratio', 'smsp__average_thread_inst_executed_per_inst_executed'],
        'not_predicated': ['smsp__thread_inst_executed_pred_on_per_inst_executed.ratio', 'smsp__average_thread_inst_executed_pred_on_per_inst_executed']
    }

    sums = {k: 0.0 for k in metric_map.keys()}
    sums.update({k: 0.0 for k in fallback_maps.keys()})
    roofline_sums = {'dram_flops': 0.0, 'dram_ai': 0.0, 'l2_flops': 0.0, 'l2_ai': 0.0, 'l1_flops': 0.0, 'l1_ai': 0.0}
    
    valid_count = 0
    units = {}
    kernel_name = ''
    for i in range(start, start + count):
        if i >= irange.num_actions():
            break
        action = irange.action_by_idx(i)
        valid_count += 1
        if i == start:
            kernel_name = action.name()

        current_vals = {}
        for key, m_name in metric_map.items():
            m = get_metric(action, '', m_name)
            val = m['value'] if (m['value'] is not None and isinstance(m['value'], (int, float))) else 0.0
            sums[key] += val
            current_vals[key] = val
            if key not in units and m['unit']:
                units[key] = m['unit']

        for key, f_names in fallback_maps.items():
            m = get_metric_fallback(action, '', f_names)
            val = m['value'] if (m['value'] is not None and isinstance(m['value'], (int, float))) else 0.0
            sums[key] += val
            if key not in units and m['unit']:
                units[key] = m['unit']

        fadd_pc = get_metric(action, '', 'smsp__sass_thread_inst_executed_op_fadd_pred_on.sum.per_cycle_elapsed').get('value', 0) or 0
        fmul_pc = get_metric(action, '', 'smsp__sass_thread_inst_executed_op_fmul_pred_on.sum.per_cycle_elapsed').get('value', 0) or 0
        ffma_pc = get_metric(action, '', 'smsp__sass_thread_inst_executed_op_ffma_pred_on.sum.per_cycle_elapsed').get('value', 0) or 0
        sm_freq_hz = current_vals['sm_freq']

        flops_s = (fadd_pc + fmul_pc + 2 * ffma_pc) * sm_freq_hz
        roofline_sums['dram_flops'] += flops_s

        dram_bw_bytes = current_vals['dram_bw'] * (1e9 if units.get('dram_bw') == 'Gbyte/s' else 1.0)
        roofline_sums['dram_ai'] += (flops_s / dram_bw_bytes if dram_bw_bytes > 0 else 0.0)
    if valid_count == 0:
        return None

    averages = {k: round(v / valid_count, 2) for k, v in sums.items()}
    roof_avgs = {k: round(v / valid_count, 2) for k, v in roofline_sums.items()}

    def fmt(readable, key):
        return {'name': f"Avg. {readable}", 'value': averages[key], 'unit': units.get(key)}

    return {
        'kernel_name': kernel_name,
        'sol': {
            'duration': fmt('Duration', 'duration'), 'sm_sol': fmt('Compute (SM) throughput', 'sm_sol'),
            'mem_sol': fmt('Memory throughput', 'mem_sol'), 'cycles': fmt('Elapsed cycles', 'cycles'),
            'l1_sol': fmt('L1/TEX cache throughput', 'l1_sol'), 'l2_sol': fmt('L2 cache throughput', 'l2_sol'),
            'dram_sol': fmt('DRAM throughput', 'dram_sol'), 'sm_freq': fmt('SM frequency', 'sm_freq'),
            'sm_active': fmt('SM active cycles', 'sm_active'), 'dram_freq': fmt('DRAM frequency', 'dram_freq')
        },
        'compute': {
            'exec_ipc_elapsed': fmt('Executed Ipc elapsed', 'exec_ipc_elapsed'), 'exec_ipc_active': fmt('Executed Ipc active', 'exec_ipc_active'),
            'issued_ipc_active': fmt('Issued Ipc active', 'issued_ipc_active'), 'sm_busy': fmt('SM busy', 'sm_busy'),
            'issue_slots_busy': fmt('Issue slots busy', 'issue_slots_busy')
        },
        'warp': {
            'cycles_x_issued': fmt('Warp cycles per issued instruction', 'cycles_x_issued'),
            'cycles_x_exec': fmt('Warp cycles per executed instruction', 'cycles_x_exec'),
            'active_threads': fmt('Avg. active threads per warp', 'active_threads'),
            'not_predicated': fmt('Avg. not predicated off threads per warp', 'not_predicated')
        },
        'occupancy': {
            'th_occ': fmt('Theoretical Occupancy', 'th_occ'), 'th_warps': fmt('Theoretical active warps per SM', 'th_warps'),
            'ach_occ': fmt('Achieved occupancy', 'ach_occ'), 'ach_warps': fmt('Achieved active warps per SM', 'ach_warps'),
            'block_regs': fmt('Block limit registers', 'block_regs'), 'block_shared': fmt('Block limit shared shared mem', 'block_shared'),
            'block_warps': fmt('Block limit warps', 'block_warps'), 'block_sm': fmt('Block limit SM', 'block_sm')
        },
        'roofline': {
            'flop_s': roof_avgs['dram_flops'],
            'ai_dram': roof_avgs['dram_ai'],
        }
    }

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

def show_SpeedOfLight_range(summary_data):
    cli_views.print_speed_of_light(summary_data['kernel_name'], summary_data['sol'])

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

def show_ComputeWorkloadAnalysis(action):
    compute_metrics = {
        'exec_ipc_elapsed': get_executed_ipc_elapsed(action),
        'exec_ipc_active': get_executed_ipc_active(action),
        'issued_ipc_active': get_issued_ipc_active(action),
        'sm_busy': get_sm_busy(action),
        'issue_slots_busy': get_issue_slots_busy(action)
    }
    cli_views.print_compute_workload(action.name(), compute_metrics)

def show_ComputeWorkloadAnalysis_range(summary_data):
    cli_views.print_compute_workload(summary_data['kernel_name'], summary_data['compute'])

################################################
#
#       WARP STATE STATISTICS
#
################################################

def get_warp_cycles_x_issued_inst(action):
    return get_metric(action, 'Warp cycles per issued instruction', 'smsp__average_warp_latency_per_inst_issued.ratio')

def get_warp_cycles_x_exec_inst(action):
    return get_metric(action, 'Warp cycles per executed instruction', 'smsp__average_warps_active_per_inst_executed.ratio')

def get_active_threads_x_warp(action):
    return get_metric_fallback(action, 'Avg. active threads per warp', [
        'smsp__thread_inst_executed_per_inst_executed.ratio',
        'smsp__average_thread_inst_executed_per_inst_executed'
    ])

def get_not_predicated_off_threads_x_warp(action):
    return get_metric_fallback(action, 'Avg. not predicated off threads per warp', [ 
        'smsp__thread_inst_executed_pred_on_per_inst_executed.ratio',
        'smsp__average_thread_inst_executed_pred_on_per_inst_executed'
    ])

def show_WarpStateStatistics(action):
    warpstate_metrics = {
        'cycles_x_issued': get_warp_cycles_x_issued_inst(action),
        'cycles_x_exec': get_warp_cycles_x_exec_inst(action),
        'active_threads': get_active_threads_x_warp(action),
        'not_predicated': get_not_predicated_off_threads_x_warp(action)
    }
    cli_views.print_warp_state(action.name(), warpstate_metrics)

def show_WarpStateStatistics_range(summary_data):
    cli_views.print_warp_state(summary_data['kernel_name'], summary_data['warp'])

################################################
#
#       OCCUPANCY
#
################################################

def get_th_occupancy(action):
    return get_metric(action, 'Theoretical Occupancy', 'sm__maximum_warps_per_active_cycle_pct')

def get_th_active_warps_x_sm(action):
    return get_metric(action, 'Theoretical active warps per SM', 'sm__maximum_warps_avg_per_active_cycle')

def get_achieved_occupancy(action):
    return get_metric(action, 'Achieved occupancy', 'sm__warps_active.avg.pct_of_peak_sustained_active')

def get_achieved_warps_x_sm(action):
    return get_metric(action, 'Achieved active warps per SM', 'sm__warps_active.avg.per_cycle_active')

def get_block_limit_regs(action):
    return get_metric(action, 'Block limit registers', 'launch__occupancy_limit_registers')

def get_block_limit_shared_mem(action):
    return get_metric(action, 'Block limit shared shared mem', 'launch__occupancy_limit_shared_mem')

def get_block_limit_warps(action):
    return get_metric(action, 'Block limit warps', 'launch__occupancy_limit_warps')

def get_block_limit_sm(action):
    return get_metric(action, 'Block limit SM', 'launch__occupancy_limit_blocks')

def show_Occupancy(action):
    occupancy_metrics = {
        'th_occ': get_th_occupancy(action),
        'th_warps': get_th_active_warps_x_sm(action),
        'ach_occ': get_achieved_occupancy(action),
        'ach_warps': get_achieved_warps_x_sm(action),
        'block_regs': get_block_limit_regs(action),
        'block_shared': get_block_limit_shared_mem(action),
        'block_warps': get_block_limit_warps(action),
        'block_sm': get_block_limit_sm(action)
    }
    cli_views.print_occupancy(action.name(), occupancy_metrics)

def show_Occupancy_range(summary_data):
    cli_views.print_occupancy(summary_data['kernel_name'], summary_data['occupancy'])

################################################
#
#       ROOFLINE METRICS
#
################################################

#
# this calculates Arithmetic Intensity and FLOPs
# in order to plot the roofline.
# The data needed for calculations is taken
# from the SpeedOfLight_RooflineChart.section file inside
# the ncu folder
#
def get_roofline_dram_coords_fp32(action):
    fadd_pc = get_metric(action, '', 'smsp__sass_thread_inst_executed_op_fadd_pred_on.sum.per_cycle_elapsed').get('value', 0) or 0
    fmul_pc = get_metric(action, '', 'smsp__sass_thread_inst_executed_op_fmul_pred_on.sum.per_cycle_elapsed').get('value', 0) or 0
    ffma_pc = get_metric(action, '', 'smsp__sass_thread_inst_executed_op_ffma_pred_on.sum.per_cycle_elapsed').get('value', 0) or 0

    sm_freq_metric = get_metric(action, '', 'smsp__cycles_elapsed.avg.per_second')
    sm_freq_hz = float(sm_freq_metric.get('value', 0) or 0)

    flops_s_fp32 = (fadd_pc + fmul_pc + 2 * ffma_pc) * sm_freq_hz

    dram_bw_metric = get_metric(action, '', 'dram__bytes.sum.per_second')
    dram_bw_bytes_s = float(dram_bw_metric.get('value', 0) or 0)
    if dram_bw_metric.get('unit') == 'Gbyte/s':
        dram_bw_bytes_s *= 1_000_000_000.0

    arithmetic_intensity_fp32 = flops_s_fp32 / dram_bw_bytes_s if dram_bw_bytes_s > 0 else 0

    return {
        'flop_s': round(flops_s_fp32, 2),
        'ai': round(arithmetic_intensity_fp32, 2)
    }

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

    shell = cli_repl.EasyNcuShell(context)
    shell.cmdloop()


if __name__ == '__main__':
    main()
