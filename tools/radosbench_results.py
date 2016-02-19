#! /usr/bin/python

import os
import fnmatch
import sys

# Thanks stackoverflow!
def find(pattern, path):
    results = []
    for root,dirs,files in os.walk(path):
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                results.append(os.path.join(root,name))
    return results

def parse_rados_bench(fname):
    curr_MB = []
    avg_lat = -1.0
    min_lat = -1.0
    max_lat = -1.0

    with open(fname) as f:
        # advance the fp to the first data portion
        while True:
            line = f.readline()
            if "sec Cur ops" in line:
                break

        for line in f:
            # bypass the rados bench live terminal output
            if "sec Cur ops" in line  or "lat:" in line:
                continue
            if "Total time run:" in line:
                # we have parsed to the end
                break
            line = line.split()
            # other needed columns should be added here
            curr_MB.append(float(line[7]))

        #parse the latency calculated by rados bench
        for line in f:
            line = line.split(':')
            if line[0].lower() == 'average latency':
                avg_lat=float(line[1])

            if line[0].lower() == 'max latency':
                max_lat=float(line[1])

            if line[0].lower() == 'min latency':
                min_lat=float(line[1])

    return sum(curr_MB)/len(curr_MB),(min_lat,max_lat,avg_lat) 

# function to group the results by top-level dir name
#   inside of that group by pool type
#       inside of that group by block size
# function to parse the rados bench results

def usage():
    print
    '''
    2 arguments needed:
        1. File name pattern
        2. path to search
    Example invocation:
    ./radosbench_results.py "output*" /home/username/perf-results/iomix_3_seq_read/
    You need quote or escape your regex for the filename pattern.
    I am using python fnmatch under the covers, those regex rules apply
    '''
# plan is to call this on a per-run basis
# group the output by pool type and object size
def main(argv):
    results_path = find(argv[0], argv[1])
    results_path.sort()
    for i in results_path:
        print(i)
        print(parse_rados_bench(i))
    


if __name__ == '__main__':
    if len(sys.argv) != 3:
        usage()
    main(sys.argv[1:])
