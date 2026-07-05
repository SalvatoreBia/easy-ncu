import cmd
import os

class EasyNcuShell(cmd.Cmd):
    intro = 'Welcome to easy-ncu interactive shell. Check for the commands with "help".\n'
    prompt = '(easy-ncu)> '

    def __init__(self, irange, summary_data):
        super().__init__()
        self.irange = irange
        self.summary = summary_data

        import __main__ as main_module
        self.main_mod = main_module

    def do_sol(self, arg):
        self.main_mod.show_ComputeWorkloadAnalysis_range(self.summary)

    def do_clear(self, arg):
        os.system('clear')

    def do_exit(self, arg):
        print('Bye.')
        return True
    
    def do_EOF(self, arg):
        print()
        return True