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
import argparse
import os
import configparser
import pathlib
import section

import cli_repl
import cli_views


CFG = 'config.cfg'
debug = False
ncu_path = None

def locate_ncu_pymodule(start='/'):
    if debug: cli_views.print_debug_string(f'Searching for ncu_report module in {start} folder...')
    res = next(pathlib.Path(start).rglob('ncu_report.py'), None)
    if res:
        config = configparser.ConfigParser()
        config.optionxform = str
        if not os.path.exists(CFG):
            cli_views.print_error_string(f'{CFG} file not found.')
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
            if debug: cli_views.print_debug_string(f'ncu_path found in {CFG}: {cached_path}')
            return cached_path
    return locate_ncu_pymodule(start='/usr/')

ncu_path = get_ncu_path()
if ncu_path:
    if ncu_path not in sys.path:
        sys.path.insert(0, ncu_path)
    if debug: cli_views.print_debug_string(f'Python environment and LD_LIBRARY_PATH updated with: {ncu_path}')
    os.environ['LD_LIBRARY_PATH'] = os.environ.get('LD_LIBRARY_PATH', '') + ':' + ncu_path
else:
    print("[ERROR] Impossibile trovare il modulo ncu_report sul sistema.")
    sys.exit(1)

try:
    import ncu_report
    if debug: cli_views.print_debug_string("ncu_report successfully loaded after environment setup!")
except ImportError:
    print(f"[ERROR] Unable to locate ncu_report.py in provided folder: {ncu_path}. Fallback to automatic resolving...") 
    ncu_path = locate_ncu_pymodule(start='/usr/')
    if not ncu_path:
        cli_views.print_error_string('Unable to resolve path for ncu_report.py. Check if nsight-compute is installed in your machine')
        print('        If you think it\'s an error, please report it on github: https://github.com/SalvatoreBia/easy-ncu')
        sys.exit(1)

    if ncu_path not in sys.path:
        sys.path.insert(0, ncu_path)
    os.environ['LD_LIBRARY_PATH'] = os.environ.get('LD_LIBRARY_PATH', '') + ':' + ncu_path

    try:
        import ncu_report
        if debug: cli_views.print_debug_string("ncu_report successfully loaded after automatic resolving!")
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
    global debug
    parser = argparse.ArgumentParser(
        description="easy-ncu - A smart CLI tool for NVIDIA Nsight Compute report analysis."
    )
    parser.add_argument(
        '--debug', 
        action='store_true', 
        help='Enable debug mode'
    )
    parser.add_argument(
        'report', 
        nargs='?', 
        help='Path to a valid .ncu-rep file'
    )
    args = parser.parse_args()
    debug = args.debug
    context = None
    if args.report:
        report = args.report
        if not os.path.exists(report) or not report.endswith('.ncu-rep'):
            cli_views.print_error_string(f'Report not found or invalid extension at: {report}')
            sys.exit(1)
        if debug:
            cli_views.print_debug_string(f'Input report found at {report}')
        try:
            context = ncu_report.load_report(report)
            if debug:
                cli_views.print_debug_string('ncu report loaded')
        except Exception as e:
            cli_views.print_error_string(f'Failed to load report: {e}')
            sys.exit(1)

    shell = cli_repl.EasyNcuShell(context, debug)
    shell.cmdloop()

if __name__ == '__main__':
    main()
