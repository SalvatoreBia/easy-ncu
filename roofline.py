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
import matplotlib.pyplot as plt
import numpy as np


def gen_roofline_fp32(data, save_to_file=False, save_path=''):
    # TODO: dynamic calculation of the divisor? nsight seems
    #       to do it whenever performance changes order of magnitude
    divisor = 1e12
    
    app_perf = data['coords']['flop_s'] / divisor
    op_ins   = data['coords']['ai']
    
    maxperf  = data['max_comp'] / divisor
    maxband  = data['max_dram'] / divisor

    application = data['kernel_name']
    sysdef = data['dev_name']
    max_perf_label = "Peak performance"

    plt.style.use('default')
    fig, ax = plt.subplots(figsize=(12, 7), dpi=100)
    
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')

    x_min, x_max = 0.01, 10000.0
    y_min = 10 ** np.floor(np.log10(app_perf) - 1)
    y_max = 10 ** np.ceil(np.log10(maxperf) + 1)
    
    if y_min > 0.0001: y_min = 0.0001
    if y_max < 100.0:  y_max = 100.0

    x_vals = np.logspace(np.log10(x_min), np.log10(x_max), 1000)
    y_vals = np.minimum(x_vals * maxband, maxperf)

    ax.plot(x_vals, y_vals, color='#000000', linewidth=2.5, zorder=3)
    ax.scatter([op_ins], [app_perf], color='#000000', s=100, zorder=5)

    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)

    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: '{:g}'.format(y)))
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: '{:g}'.format(y)))

    ax.minorticks_on()
    ax.grid(True, which="major", color='#cccccc', linestyle='--', linewidth=0.6, zorder=1)
    ax.grid(False, which="minor")

    for spine in ax.spines.values():
        spine.set_color('#333333')
    ax.tick_params(colors='#333333', which='both')

    ax.set_xlabel('Arithmetic Intensity [FLOP/byte]', fontsize=11, color='black', labelpad=10)
    ax.set_ylabel(f'Performance [FLOP/s]\n(1 = {divisor:,})'.replace(',', '.'), fontsize=11, color='black', labelpad=10)
    ax.set_title(f"FP32 Roofline ({sysdef})", fontsize=13, color='black', pad=15, weight='bold')

    ax.text(15, maxperf * 1.25, f"{max_perf_label} ({maxperf:.2f})", 
            color='#0090df', fontsize=10, verticalalignment='bottom', weight='semibold')

    kernel_text = f"{application}\n(AI: {op_ins:.2f}, Perf: {app_perf:.5f})"
    ax.text(op_ins, app_perf * 2.5, kernel_text, 
            color='#00b0b0', fontsize=9, horizontalalignment='center', verticalalignment='bottom', weight='semibold')

    plt.tight_layout()

    if save_to_file:
        filepath = save_path if save_path else 'roofline.png'
        plt.savefig(filepath, facecolor='white', edgecolor='none', bbox_inches='tight')
        print(f"[DEBUG] Roofline saved in: {filepath}")
    else:
        plt.show()
    plt.close(fig)

def gen_roofline_hierarchical(data, save_to_file=False, save_path=''):
    pass
