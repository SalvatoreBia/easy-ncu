from rich.console import Console
from rich.table import Table
from rich.box import ROUNDED
from rich.markup import escape

console = Console()

def _fmt_val(metric, target_unit=None):
    val = metric.value()
    unit = metric.unit()
    name = metric.label()
    
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

def print_section(section_name, kernel_name, data):
    t_left = Table(box=None, show_header=False, expand=True)
    t_left.add_column('Metric',  justify='left', style='magenta')
    t_left.add_column('Value', justify='right', style='white')

    t_right = Table(box=None, show_header=False, expand=True)
    t_right.add_column('Metric', justify='left', style='magenta')
    t_right.add_column('Value', justify='right', style='white')
    
    metrics = data.get_entries()
    for i, m in enumerate(metrics):
        unit_str = '' if not m.unit() else f'[{m.unit()}]'
        if i % 2 == 0:
            t_left.add_row(escape(f'{m.label()} {unit_str}'), _fmt_val(m))
        else:
            t_right.add_row(escape(f'{m.label()} {unit_str}'), _fmt_val(m))
    
    outer_table = Table(
        title=f'\n[bold]SECTION: {section_name} [/bold] | [dim]Kernel: {kernel_name}[/dim]',
        box=ROUNDED, 
        show_header=False,
        title_justify='left'
    )
    
    outer_table.add_column(width=50)
    outer_table.add_column(width=50)
    outer_table.add_row(t_left, t_right)
    console.print(outer_table)

