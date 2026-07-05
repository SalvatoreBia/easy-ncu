import cmd
import os

class EasyNcuShell(cmd.Cmd):
    intro = 'Welcome to easy-ncu interactive shell. Check for the commands with "help".\n'
    prompt = '(easy-ncu)> '
    flags_whitelist = ['aggregate.avg']

    def __init__(self, context):
        super().__init__()
        self.context = context

        import __main__ as main_module
        self.main_mod = main_module

        self.range_idx = 0
        self.irange = self.context.range_by_idx(self.range_idx)
        self.nrange = self.context.num_ranges()
        
        self.action_idx = 0
        self.action  = self.irange.action_by_idx(self.action_idx)
        self.naction = self.irange.num_actions()

        self.start = 0
        self.count = self.naction

        self.avg_on = False
        self.summary = None
        self.do_fetch(None)
        self._update_prompt()

    def do_fetch(self, arg):
        """Cool logo"""
        kernel_name = self.action.name() if self.naction > 0 else "N/A"
        if len(kernel_name) > 30:
            kernel_name = kernel_name[:27] + "..."

        sm_freq_m = self.main_mod.get_metric(self.action, '', 'gpc__cycles_elapsed.avg.per_second')
        clk_val = sm_freq_m.get('value', 0) or 0
        clk_str = f"{clk_val / 1e6:.1f} MHz" if clk_val > 0 else "Unknown"

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

        print()
        for i in range(len(logo)):
            l_side = logo[i] if i < len(logo) else " " * 86
            print(f"  \033[1;32m{l_side}\033[0m")
        print()

    def _update_prompt(self):
        if self.avg_on:
            end_idx = self.start + self.count - 1
            mode = f"Summary:{self.start}-{end_idx}"
        else:
            mode = f"Kernel {self.action_idx}"
        self.prompt = f'(easy-ncu)[range:{self.range_idx} | {mode}]> '

    def _update_summary_if_needed(self):
        if self.avg_on:
            self.summary = self.main_mod.get_range_metrics_summary(self.irange, start=self.start, count=self.count)
        else:
            self.summary = None

    def do_enable(self, arg):
        """
        Enables a configuration flags contained in the flags whitelist.
        Usage: enable <flag-name>
        """
        if not arg:
            print('Provide a valid flag to toggle.')
            return
        
        flag = str(arg).strip()
        if flag not in self.flags_whitelist:
            print('Flag provided does not exist.')
            return
            
        if not self.avg_on:
            self.avg_on = True
            self._update_summary_if_needed()
            self._update_prompt()
            print('Summary aggregation enabled.')

    def do_disable(self, arg):
        """
        Disables a configuration flags contained in the flags whitelist.
        Usage: enable <flag-name>
        """
        if not arg:
            print('Provide a valid flag to toggle.')
            return

        flag = str(arg).strip()
        if flag not in self.flags_whitelist:
            print('Flag provided does not exist.')
            return
            
        if self.avg_on:
            self.avg_on = False
            self.summary = None
            self._update_prompt()
            print('Summary aggregation disabled. Single kernel mode active.')

    def do_showflags(self, arg):
        """Shows all available flags."""
        print(' Available flags:')
        for f in self.flags_whitelist:
            print(f'    {f}')

    def do_setrange(self, arg):
        """
        Select a range from the current context.
        If you did not use multiple cudaProfilerStart() and cudaProfilerStop() calls, these values should always be 0.
        Usage: setrange <range-idx>
        """
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
            
            self._update_summary_if_needed()
            self._update_prompt()
            print(f'Switched to range {idx}.')
        except ValueError:
            print('Provide a valid range index.')

    def do_setkernel(self, arg):
        """
        Select a kernel from the current range.
        When aggregate flags are disabled, the shell will show metrics only for the specified kernel.
        Usage: setkernel <kernel-idx>
        """
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
            
            if self.avg_on:
                self.avg_on = False
                self.summary = None
                print('Auto-disabled summary aggregation to inspect the selected kernel.')
                
            self._update_prompt()
            print(f'Targeted kernel {idx}: {self.action.name()}')
        except ValueError:
            print('Provide a valid kernel index.')

    def do_setslice(self, arg):
        """
        Set a custom sub-slice of kernels for the summary calculation.
        Usage: setslice <start-idx> <count>
        """
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

            if not self.avg_on:
                self.avg_on = True
                print('Auto-enabled summary aggregation for the selected slice.')

            self._update_summary_if_needed()
            self._update_prompt()
            print(f'Summary slice updated: evaluating {self.count} kernels starting from index {self.start}.')
        except ValueError:
            print('Arguments must be valid integers.')
    
    def do_sol(self, arg):
        """Show Speed of Light section."""
        if self.avg_on:
            self.main_mod.show_SpeedOfLight_range(self.summary)
        else:
            self.main_mod.show_SpeedOfLight(self.action)

    def do_cwa(self, arg):
        """Show Compute Workload Analysis section."""
        if self.avg_on:
            self.main_mod.show_ComputeWorkloadAnalysis_range(self.summary)
        else:
            self.main_mod.show_ComputeWorkloadAnalysis(self.action)

    def do_wss(self, arg):
        """Show Warp State Statistics section."""
        if self.avg_on:
            self.main_mod.show_WarpStateStatistics_range(self.summary)
        else:
            self.main_mod.show_WarpStateStatistics(self.action)

    def do_occ(self, arg):
        """"Show Occupancy section."""
        if self.avg_on:
            self.main_mod.show_Occupancy_range(self.summary)
        else:
            self.main_mod.show_Occupancy(self.action)

    def do_clear(self, arg):
        os.system('cls' if os.name == 'nt' else 'clear')

    def do_exit(self, arg):
        print('Bye.')
        return True
    
    def do_EOF(self, arg):
        print()
        return True