# easy-ncu

![alt text](resources/image.png)

`easy-ncu` is an interactive shell which aims to simplify the extraction of kernel metrics collected through nsight-compute. In addition to that, it allows to aggregate values (==actually, a big refactoring is in the process, so aggregations are not functioning at the moment) of specified metrics on different kernel launches, roofline exports and much more.

It's still in development, so right now the shell it's not complete.

The code allows for collecting the following sections:
- Speed of Light
- Compute Workload Analysis
- Warp State Statistics
- Occupancy
- Arithmetic Intensity
- FLOP/s

An example `.ncu-rep` file is provided in the resources folder.

---

**NOTE**: The metrics name are taken from the Ampere architecture, so if you have GPUs with different architecture it may not find the metrics. If so, you can change yourself the metrics name and the code should work. Support for different architectures may be added later.
