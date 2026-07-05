from rich.console import Console
from rich.table import Table
from rich.box import ROUNDED
from rich.markup import escape

console = Console()

def _fmt_val(metric_dict, target_unit=None):
    val = metric_dict.get('value')
    unit = metric_dict.get('unit')
    name = metric_dict.get('name', '').lower()
    
    if val is None:
        return '[dim]N/A[/dim]'
    
    if target_unit == '[s]' and unit == 'ns':
        return f'{float(val) / 1_000_000_000:.2f}'
    
    if target_unit == '[Ghz]' and (unit == 'hz' or 'frequency' in name):
        return f'{float(val) / 1_000_000_000:.2f}'
        
    if isinstance(val, (int, float)):
        if target_unit == '[cycle]' or 'cycles' in name:
            return f'{int(val):,}'.replace(',', '.')
            
        formatted = f'{val:.2f}'
        if val > 1000:
            return f'{float(formatted):,}'.replace(',', '.')
        return formatted.replace('.', ',')
        
    return str(val)


def print_speed_of_light(kernel_name, data):
    t_left = Table(box=None, show_header=False, expand=True)
    t_left.add_column('Metric',  justify='left', style='magenta')
    t_left.add_column('Value', justify='right', style='white')
    
    t_left.add_row(f'{data['sm_sol']['name']} [%]', _fmt_val(data['sm_sol']))
    t_left.add_row(f'{data['mem_sol']['name']} [%]', _fmt_val(data['mem_sol']))
    t_left.add_row(f'{data['l1_sol']['name']} [%]', _fmt_val(data['l1_sol']))
    t_left.add_row(f'{data['l2_sol']['name']} [%]', _fmt_val(data['l2_sol']))
    t_left.add_row(f'{data['dram_sol']['name']} [%]', _fmt_val(data['dram_sol']))

    t_right = Table(box=None, show_header=False, expand=True)
    t_right.add_column('Metric', justify='left', style='magenta')
    t_right.add_column('Value', justify='right', style='white')
    
    t_right.add_row(escape(f'{data['duration']['name']} [s]'), _fmt_val(data['duration'], '[s]'))
    t_right.add_row(escape(f'{data['cycles']['name']} [cycle]'), _fmt_val(data['cycles'], '[cycle]'))
    t_right.add_row(escape(f'{data['sm_active']['name']} [cycle]'), _fmt_val(data['sm_active'], '[cycle]'))
    t_right.add_row(f'{data['sm_freq']['name']} [Ghz]', _fmt_val(data['sm_freq'], '[Ghz]'))
    t_right.add_row(f'{data['dram_freq']['name']} [Ghz]', _fmt_val(data['dram_freq'], '[Ghz]'))

    outer_table = Table(
        title=f'\n[bold]SECTION: Speed of Light (SoL)[/bold] | [dim]Kernel: {kernel_name}[/dim]',
        box=ROUNDED, 
        show_header=False,
        title_justify='left'
    )
    
    outer_table.add_column(width=50)
    outer_table.add_column(width=50)
    outer_table.add_row(t_left, t_right)
    console.print(outer_table)


def print_compute_workload(kernel_name, data):
    t_left = Table(box=None, show_header=False, expand=True)
    t_left.add_column('Metric', justify='left', style='magenta')
    t_left.add_column('Value', justify='right', style='white')
    t_left.add_row(f"{data['exec_ipc_elapsed']['name']}", _fmt_val(data['exec_ipc_elapsed']))
    t_left.add_row(f"{data['exec_ipc_active']['name']}", _fmt_val(data['exec_ipc_active']))
    t_left.add_row(f"{data['issued_ipc_active']['name']}", _fmt_val(data['issued_ipc_active']))

    t_right = Table(box=None, show_header=False, expand=True)
    t_right.add_column('Metric', justify='left', style='magenta')
    t_right.add_column('Value', justify='right', style='white')
    t_right.add_row(escape(f"{data['sm_busy']['name']} [%]"), f"{_fmt_val(data['sm_busy'])}")
    t_right.add_row(escape(f"{data['issue_slots_busy']['name']} [%]"), f"{_fmt_val(data['issue_slots_busy'])}")
    t_right.add_row('', '')

    outer_table = Table(
        title=f'\n[bold]SECTION: Compute Workload Analysis[/bold] | [dim]Kernel: {kernel_name}[/dim]',
        box=ROUNDED,
        show_header=False,
        title_justify='left'
    )
    outer_table.add_column(width=50)
    outer_table.add_column(width=50)
    outer_table.add_row(t_left, t_right)
    console.print(outer_table)

def print_warp_state(kernel_name, data):
    t_left = Table(box=None, show_header=False, expand=True)
    t_left.add_column('Metric', justify='left', style='magenta')
    t_left.add_column('Value', justify='right', style='white')
    t_left.add_row(escape(f"{data['cycles_x_issued']['name']} [cycle]"), f"{_fmt_val(data['cycles_x_issued'])}")
    t_left.add_row(escape(f"{data['cycles_x_exec']['name']} [cycle]"), f"{_fmt_val(data['cycles_x_exec'])}")

    t_right = Table(box=None, show_header=False, expand=True)
    t_right.add_column('Metric', justify='left', style='magenta')
    t_right.add_column('Value', justify='right', style='white')
    t_right.add_row(f"{data['active_threads']['name']}", f"{_fmt_val(data['active_threads'])}")
    t_right.add_row(f"{data['not_predicated']['name']}", f"{_fmt_val(data['not_predicated'])}")

    outer_table = Table(
        title=f'\n[bold]SECTION: Warp State Statistics[/bold] | [dim]Kernel: {kernel_name}[/dim]',
        box=ROUNDED,
        show_header=False,
        title_justify='left'
    )
    outer_table.add_column(width=55)
    outer_table.add_column(width=55)
    outer_table.add_row(t_left, t_right)
    console.print(outer_table)