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
from rich.console import Console
from rich.table import Table
from rich.box import ROUNDED
from rich.markup import escape
import random

REPOSITORY = 'https://github.com/SalvatoreBia/easy-ncu'

console = Console()

def _fmt_val(metric, target_unit=None):
    val = metric.value()
    unit = metric.unit()
    name = metric.label()
    
    if val is None:
        return '[dim]N/A[/dim]'
    
    if isinstance(val, (int, float)):
        formatted = f'{val:.2f}'
        if val > 1000:
            return f'{float(formatted):,}'.replace(',', '.')
        return formatted.replace('.', ',')
        
    return str(val)

def fetch(logo, is_in_debug_mode):
    rich_colors = ['red', 'green', 'yellow', 'blue', 'magenta', 'cyan']
    logo_color = random.choice(rich_colors)
    logo_str = "\n".join([f"[{logo_color}]{line}[/{logo_color}]" for line in logo])

    info_lines = [
        f"[bold {logo_color}]easy-ncu[/bold {logo_color}]@[bold white]shell[/bold white]",
        "[dim]---------------------------------------[/dim]",
        f"[bold {logo_color}]Debug Mode :[/bold {logo_color}] {'Enabled' if is_in_debug_mode else 'Disabled'}",
        f"[bold {logo_color}]GitHub     :[/bold {logo_color}] [underline]{REPOSITORY}[/underline]",
        f"[bold {logo_color}]License    :[/bold {logo_color}] GNU GPLv3",
        "",
        " ".join([f"[background color={c}]   [/background color]" for c in ['red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white']])
    ]
    info_str = "\n".join(info_lines)

    fetch_table = Table(box=None, show_header=False, pad_edge=False)
    fetch_table.add_column("Logo", justify="left", vertical="middle")
    fetch_table.add_column("Info", justify="left", vertical="middle")

    fetch_table.add_row(logo_str, info_str)

    console.print()
    console.print(fetch_table)
    console.print()

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
    
    outer_table.add_column(width=70)
    outer_table.add_column(width=70)
    outer_table.add_row(t_left, t_right)
    console.print(outer_table)

def print_eval_results(rule_path, kernel_name, result):
    t_res = Table(box=None, show_header=False, title_justify='left')
    t_res.add_column('Output', justify='left')

    aftereqlen = 10
    maxlen = len(max(result.keys(), key=len))
    for outname, val in result.items():
        tgtlen = maxlen - len(outname) + 3
        out_str = f'<{outname}>{" " * tgtlen}'
        val = val if not isinstance(val, float) else f"{val:.4f}"
        t_res.add_row(f"[cyan]{out_str}[/cyan]={" " * aftereqlen}{val}")

    title = f'[bold]Evaluated expressions for kernel[/bold] [dim]{escape(kernel_name)}[/dim]\n[bold]From rule file :[/bold] [dim]{escape(rule_path)}[dim]'
    console.print(title, highlight=False)
    console.print(t_res)
    console.print()

def print_info_string(s):
    console.print(f'[cyan i]{escape(s)}[/i cyan]', highlight=False)

def print_warning_string(s):
    console.print(f'[yellow i]{escape(s)}[/i yellow]', highlight=False)

def print_error_string(s):
    console.print(f"[red i]{escape(s)}[/i red]", highlight=False)

def print_debug_string(s):
    console.print(f'[dim]{escape("[DEBUG]")} {escape(s)}[/dim]', highlight=False)

def print_available_elements(what, l):
    console.print(f'[bold]AVAILABLE {what.upper()}[/bold]')
    for key in l:
        console.print(f'   [i dim]{key}[/dim i]')

