# easy-ncu

`easy-ncu` is an interactive shell which aims to simplify the extraction of kernel metrics collected through nsight-compute. In addition to that, it allows to aggregate metrics (i.e., just averages right now) of specified metrics on different kernel launches, roofline exports and much more.

It's still in development, so right now the shell it's not complete.

The code allows for collecting the following sections:
- Speed of Light
- Compute Workload Analysis
- Warp State Statistics
- Occupancy
- Arithmetic Intensity
- FLOP/s
