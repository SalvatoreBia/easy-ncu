# easy-ncu - A smart CLI tool for NVIDIA Nsight Compute report analysis.
# Copyright (C) 2026  Salvatore Biamonte
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
import sys
import os
import configparser
import cli_views
import cli_repl
import pathlib
import section


CFG = 'config.cfg'
debug = True
ncu_path = None

def locate_ncu_pymodule(start='/'):
    if debug: print(f'[DEBUG] Searching for ncu_report module in {start} folder...')
    res = next(pathlib.Path(start).rglob('ncu_report.py'), None)
    if res:
        config = configparser.ConfigParser()
        config.optionxform = str
        if not os.path.exists(CFG):
            print(f'[ERROR] {CFG} file not found.')
            return None
        config.read(CFG)
        s = str(res.parent) + '/'
        config.defaults()['NcuPythonPath'] = s
        with open(CFG, 'w') as file:
            config.write(file)
        return s
    return None

def get_ncu_path():
    config = configparser.ConfigParser()
    config.optionxform = str
    if os.path.exists(CFG):
        config.read(CFG)
        cached_path = config.defaults().get('NcuPythonPath')
        if cached_path and os.path.exists(cached_path):
            if debug: print(f'[DEBUG] ncu_path found in {CFG}: {cached_path}')
            return cached_path
    return locate_ncu_pymodule(start='/usr/')

ncu_path = get_ncu_path()
if ncu_path:
    if ncu_path not in sys.path:
        sys.path.insert(0, ncu_path)
    if debug: print(f'[DEBUG] Python environment and LD_LIBRARY_PATH updated with: {ncu_path}')
    os.environ['LD_LIBRARY_PATH'] = os.environ.get('LD_LIBRARY_PATH', '') + ':' + ncu_path
else:
    print("[ERROR] Impossibile trovare il modulo ncu_report sul sistema.")
    sys.exit(1)

try:
    import ncu_report
    if debug: print("[DEBUG] ncu_report successfully loaded after environment setup!")
except ImportError:
    print(f"[ERROR] Unable to locate ncu_report.py in provided folder: {ncu_path}. Fallback to automatic resolving...") 
    ncu_path = locate_ncu_pymodule(start='/usr/')
    if not ncu_path:
        print('[ERROR] Unable to resolve path for ncu_report.py. Check if nsight-compute is installed in your machine')
        print('        If you think it\'s an error, please report it on github: https://github.com/SalvatoreBia/easy-ncu')
        sys.exit(1)

    if ncu_path not in sys.path:
        sys.path.insert(0, ncu_path)
    os.environ['LD_LIBRARY_PATH'] = os.environ.get('LD_LIBRARY_PATH', '') + ':' + ncu_path

    try:
        import ncu_report
        if debug: print("[DEBUG] ncu_report successfully loaded after automatic resolving!")
    except ImportError as e:
        print(f"[ERROR] Found path {ncu_path} but still unable to import ncu_report: {e}")
        sys.exit(1)

##############################################

#
# old stuff, may be useful...
#
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
def get_roofline_coords_fp32(action, full=False):
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
        'flop_s': flops_s_fp32,
        'ai': round(arithmetic_intensity_fp32, 2)
    }

################################################

def load_report_wrapper(report):
    return ncu_report.load_report(report)

def load_sections(action):
    sections = {}
    for s in action.sections():
        sect = section.Section(s.name())
        for m in s.header_metrics():
            sect.add_entry(m)
        sections[sect.name] = sect
    return sections

def main():
    if len(sys.argv) > 2:
        print('[ERROR] Only one report file can be selected.')
        sys.exit(1)

    context = None
    if len(sys.argv) == 2:
        try:
            report = sys.argv[1]
            if not os.path.exists(report) or not report.endswith('.ncu-rep'):
                print(f'[ERROR] Report not found or invalid extension at: {report}')
                sys.exit(1)
            if debug:
                print(f'[DEBUG] Input report found at {report}')
            context = ncu_report.load_report(report)
            if debug:
                print('[DEBUG] ncu report loaded')
        except Exception as e:
            print(f'[ERROR] Failed to load report: {e}')
            sys.exit(1)

    shell = cli_repl.EasyNcuShell(context)
    shell.cmdloop()

if __name__ == '__main__':
    main()
