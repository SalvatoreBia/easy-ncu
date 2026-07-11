import cmd
import os
import cli_views
import roofline
from aggregators import SumAggregator, AvgAggregator
from rule_parser import RuleParser


class EasyNcuShell(cmd.Cmd):
    intro = 'Welcome to easy-ncu interactive shell. Check for the commands with "help".\n'
    prompt = '(easy-ncu)> '
    flags_whitelist = ['aggregate.sum', 'aggregate.avg']

    def __init__(self, context):
        super().__init__()
        self.context = context

        import __main__ as main_module
        self.main_mod = main_module

        self.range_idx = 0
        self.irange = None
        self.nrange = 0
        self.action_idx = 0
        self.action = None
        self.naction = 0
        self.start = 0
        self.count = 0

        self.avg_on = False
        self.sum_on = False
        self.sum_agg = None
        self.avg_agg = None
        self.aggregated = None
        
        self.sections = None

        if self.context:
            self._context_init()

        self.do_fetch(None)

    def do_fetch(self, arg):
        """Cool logo"""
        logo = [
            r' _______   ________  ________       ___    ___      ________   ________  ___  ___',
            r'|\  ___ \ |\   __  \|\   ____\     |\  \  /  /|    |\   ___  \|\   ____\|\  \|\  \ ',
            r'\ \   __/|\ \  \|\  \ \  \___|_    \ \  \/  / /    \ \  \\ \  \ \  \___|\ \  \\\  \ ',
            r' \ \  \_|/_\ \   __  \ \_____  \    \ \    / /      \ \  \\ \  \ \  \    \ \  \\\  \ ',
            r'  \ \  \_|\ \ \  \ \  \|____|\  \    \/  /  /        \ \  \\ \  \ \  \____\ \  \\\  \ ',
            r'   \ \_______\ \__\ \__\____\_\  \ __/  / /           \ \__\\ \__\ \_______\ \_______\ ',
            r'    \|_______|\|__|\|__|\_________\\___/ /             \|__| \|__|\|_______|\|_______|',
            r'                       \|_________\|___|/'
        ]

        import random
        available_colors = ['31', '32', '33', '34', '35', '36']
        selected_color = random.choice(available_colors)

        print()
        for i in range(len(logo)):
            l_side = logo[i]
            print(f"  \033[1;{selected_color}m{l_side}\033[0m")
        print()

    def _update_prompt(self):
        if self.context:
            if self.avg_on:
                end_idx = self.start + self.count - 1
                mode = f"Agg:{self.start}-{end_idx}"
            else:
                mode = f"Kernel {self.action_idx}"
            self.prompt = f'(easy-ncu)[range:{self.range_idx} | {mode}]> '
        else:
            self.prompt = '(easy-ncu)> '

    def _context_init(self):
        self.range_idx = 0
        self.irange = self.context.range_by_idx(self.range_idx)
        self.nrange = self.context.num_ranges()

        self.action_idx = 0
        self.action  = self.irange.action_by_idx(self.action_idx)
        self.naction = self.irange.num_actions()

        self.start = 0
        self.count = self.naction

        self.avg_on = False
        self.sum_on = False

        self.sum_agg = SumAggregator(self.irange, self.start, self.count, should_load=False)
        self.avg_agg = AvgAggregator(self.irange, self.start, self.count, should_load=False)

        self.sections = self.main_mod.load_sections(self.action)
        self._update_prompt()

    def do_enable(self, arg):
        if not self.context:
            print('No report loaded. Use "report <path>" first.')
            return
        if not arg:
            print('Provide a valid flag to toggle.')
            return

        flag = str(arg).strip()
        if flag not in self.flags_whitelist:
            print('Flag provided does not exist.')
            return

        if flag == 'aggregate.avg':
            self.avg_on = True
            self.sum_on = False
            self.avg_agg.set_slice(self.start, self.count)
            self.avg_agg.load()
            self.aggregated = self.avg_agg.aggregate()
        elif flag == 'aggregate.sum':
            self.sum_on = True
            self.avg_on = False
            self.sum_agg.set_slice(self.start, self.count)
            self.sum_agg.load()
            self.aggregated = self.sum_agg.aggregate()

        self._update_prompt()
        print(f'Aggregation {flag} enabled for the current slice.')

    def do_disable(self, arg):
        """
        Disables configuration flags contained in the whitelist.

        Usage:
            disable <flag>
        """
        if not self.context:
            print('No report loaded.')
            return
        if not arg:
            print('Provide a valid flag to toggle.')
            return

        flag = str(arg).strip()
        if flag not in self.flags_whitelist:
            print('Flag provided does not exist.')
            return

        if flag == 'aggregate.avg':
            self.avg_on = False
        elif flag == 'aggregate.sum':
            self.sum_on = False

        if not self._any_aggregation():
            self.aggregated = None
            print('Aggregation disabled. Single kernel mode active.')
        self._update_prompt()

    def do_showflags(self, arg):
        """
        Shows all configuration flags available to toggle.

        Usage:
            showflags
        """
        print(' Available flags:')
        for f in self.flags_whitelist:
            print(f'    {f}')

    def do_report(self, arg):
        """
        Load a valid ncu-rep file into the execution context at runtime.

        Usage:
            report <path>

        Arguments:
            <path>              The filepath pointing to the .ncu-rep file.
        """
        if not arg:
            print('Provide a valid ncu-rep file.')
            return

        try:
            rep_path = str(arg).strip()
            if not os.path.exists(rep_path):
                print(f'Report file at {rep_path} does not exist.')
                return
            self.context = self.main_mod.load_report_wrapper(rep_path)
            self._context_init()
            print(f'Successfully loaded report: {rep_path}')
        except Exception as e:
            print(f'Failed to load report: {e}')
            return

    def do_setrange(self, arg):
        """
        Select an active profiling range from the current context.

        Usage:
            setrange <range-idx>

        Arguments:
            <range-idx>         The index of the range window to load.
        """
        if not self.context:
            print('No report loaded.')
            return
        if not arg:
            print('Provide a valid range index.')
            return
        
        try:
            idx = int(arg)
            if idx < 0 or idx >= self.nrange:
                print(f'Range index out of bounds. Valid indices are 0 to {self.nrange-1}')
                return
            
            self.range_idx = idx
            self.irange = self.context.range_by_idx(idx)
            self.naction = self.irange.num_actions()
            
            self.action_idx = 0
            self.action = self.irange.action_by_idx(self.action_idx)
            
            self.start = 0
            self.count = self.naction
            
            self._update_prompt()
            print(f'Switched to range {idx}.')
        except ValueError:
            print('Provide a valid range index.')

    def do_setkernel(self, arg):
        """
        Select a specific kernel execution target from the current range window.

        Usage:
            setkernel <kernel-idx>

        Arguments:
            <kernel-idx>        The index of the execution action to load.
        """
        if not self.context:
            print('No report loaded.')
            return
        if not arg:
            print('Provide a valid kernel index.')
            return
        try:
            idx = int(arg)
            if idx < 0 or idx >= self.naction:
                print(f'Kernel index out of bounds. Valid indices for this range are 0 to {self.naction-1}')
                return

            self.action_idx = idx
            self.action = self.irange.action_by_idx(idx)
            self.sections = self.main_mod.load_sections(self.action)
            if self.avg_on:
                self.avg_on = False
                print('Auto-disabled aggregation to inspect the selected kernel.')

            self._update_prompt()
            print(f'Targeted kernel {idx}: {self.action.name()}')
        except ValueError:
            print('Provide a valid kernel index.')

    def do_setslice(self, arg):
        if not self.context:
            print('No report loaded.')
            return
        if not arg:
            print('Provide valid start and count values.')
            return

        parts = arg.split()
        if len(parts) != 2:
            print('Invalid arguments. Usage: setslice <start-idx> <count>')
            return

        try:
            s_val = int(parts[0])
            c_val = int(parts[1])

            if s_val < 0 or s_val >= self.naction:
                print(f'Start index out of bounds. Valid indices are 0 to {self.naction-1}')
                return
            if c_val <= 0:
                print('Count must be greater than 0.')
                return
            if s_val + c_val > self.naction:
                print(f'Slice exceeds range window. Maximum remaining kernels from start: {self.naction - s_val}')
                return

            self.start = s_val
            self.count = c_val

            if not self.sum_on and not self.avg_on:
                self.avg_on = True
                print('Auto-enabled average aggregation for the selected slice.')

            if self.avg_on:
                self.avg_agg.set_slice(self.start, self.count)
                self.avg_agg.load()
                self.aggregated = self.avg_agg.aggregate()
            elif self.sum_on:
                self.sum_agg.set_slice(self.start, self.count)
                self.sum_agg.load()
                self.aggregated = self.sum_agg.aggregate()

            self._update_prompt()
            print(f'Evaluating {self.count} kernels starting from index {self.start}.')
        except ValueError:
            print('Arguments must be valid integers.')

    def _any_aggregation(self):
        return self.avg_on or self.sum_on

    def _show_section(self, section_name):
        if not self.context:
            print('No report loaded.')
            return
        sect = self.aggregated[section_name] if self._any_aggregation() else self.sections[section_name]
        cli_views.print_section(section_name, self.action.name(), sect)

    def do_sol(self, arg):
        """
        Show the Speed of Light section.
        """
        self._show_section('GPU Speed Of Light Throughput')

    def do_cwa(self, arg):
        """
        Show the Compute Workload Analysis section.
        """
        self._show_section('Compute Workload Analysis')

    def do_wss(self, arg):
        """
        Show the Warp State Statistics section.
        """
        self._show_section('Warp State Statistics')

    def do_occ(self, arg):
        """
        Show the Occupancy section.
        """
        self._show_section('Occupancy')

    def do_full(self, arg):
        """
        Show all sections.
        """
        self.do_sol(None)
        self.do_cwa(None)
        self.do_wss(None)
        self.do_occ(None)

    def do_roofline(self, arg):
        """
        Show or save the Roofline plot for the current kernel.

        Usage: 
            roofline <precision> [options]

        Arguments:
            <precision>         Target precision model. Currently only 'fp32' is supported.
                                Valid choices: fp32, fp64 (N/A)

        Options:
            --all               Show the full hierarchical roofline model. Currently not supported.
            --save <dir> <file> Save the generated plot as a PNG file insidede <dir> 
                                with the name <file> (do not include extension).

        Examples:
            roofline fp32
            roofline fp32 --all
            roofline fp32 --save ./plots my_kernel_roofline
        """
        if not self.context:
            print('No report loaded.')
            return
        if not arg:
            print('Usage: roofline <fp32 | fp64> [--full | --save <out_dir> <filename>]')
            return

        parts = arg.split()
        precision = parts[0].lower()
        if precision not in {'fp32', 'fp64'}:
            print(f'{parts[0]} is not a valid precision.')
            return
        
        show_full, save_plot, out_path = False, False, None
        i = 1
        while i < len(parts):
            flag = parts[i].lower()
            if flag == '--all':
                show_full = True
                i += 1
            elif flag == '--save':
                if i + 2 >= len(parts):
                    print('--save requires an <out_dir> and a <filename> without extension.')
                    return
                out_dir = parts[i + 1]
                filename = parts[i + 2]
                stripped_filename = os.path.splitext(filename)[0]
                out_path = os.path.join(out_dir, f'{stripped_filename}.png')
                save_plot = True
                i += 3
            else:
                print(f'Unknown argument: {parts[i]}')
                return

        if self.avg_on:
            print('Roofline plot is currently supported only for single kernel inspection.')
        else:
            if precision == 'fp32':
                data = self.main_mod.get_roofline_coords_fp32(self.action, show_full)

                dev_name = self.main_mod.get_metric(self.action, '', 'device__attribute_display_name')['value']
                sm_freq = self.main_mod.get_metric(self.action, '', 'sm__cycles_elapsed.avg.per_second')['value']
                derived_ffma = self.main_mod.get_metric(self.action, '', 'derived__sm__sass_thread_inst_executed_op_ffma_pred_on_x2')['value']
                dram_bytex_x_cycles = self.main_mod.get_metric(self.action, '', 'dram__bytes.sum.peak_sustained')['value']
                dram_freq = self.main_mod.get_metric(self.action, '', 'dram__cycles_elapsed.avg.per_second')['value']

                max_comp = derived_ffma * sm_freq
                max_dram = dram_bytex_x_cycles * dram_freq
                
                roofline_data = {
                    'dev_name': dev_name, 
                    'kernel_name': self.action.name(), 
                    'coords': data, 
                    'max_comp': max_comp, 
                    'max_dram': max_dram
                }
                roofline.gen_roofline_fp32(roofline_data, save_to_file=save_plot, save_path=out_path)
            elif precision == 'fp64':
                print('FP64 precision is currently not implemented.')

    def do_eval(self, arg):
        """
        Evaluate a rule file against the currently selected kernel.
        
        Usage: 
            eval <file_path>
            
        Example:
            eval example.rule
        """
        if not self.context:
            print('[ERROR] No report loaded. Use "report <path>" first.')
            return
        if not arg:
            print('[ERROR] Provide a valid rule file path. Usage: eval <file_path>')
            return

        rule_path = str(arg).strip()
        if self._any_aggregation():
            print('[WARNING] Rule evaluation is currently supported only for single kernel inspection.')
            print(f'          Evaluating against the currently targeted kernel {self.action_idx}.')

        print(f'Evaluating rule file: {rule_path} ...')
        try:
            rp = RuleParser()
            results = rp.evaluate(rule_path, self.action)
            if results is None:
                return

            print("\n" + "="*50)
            print(f" RULE EVALUATION RESULTS ({self.action.name()[:40]}...)")
            print("="*50)
            
            if not results:
                print(" No expressions were evaluated (check if [EXPRESSION] block is empty).")
            else:
                for expr_name, value in results.items():
                    if isinstance(value, float):
                        print(f"  {expr_name:<15} = {value:.4f}")
                    else:
                        print(f"  {expr_name:<15} = {value}")
            print("="*50 + "\n")
        except Exception as e:
            print(f"[ERROR] An unexpected error occurred during evaluation: {e}")

    def do_c(self, arg):
        """
        Clear the terminal screen window.
        """
        os.system('cls' if os.name == 'nt' else 'clear')

    def do_exit(self, arg):
        """
        Exit and close the interactive shell session.
        """
        print('Bye.')
        return True

    def do_EOF(self, arg):
        print()
        return True

