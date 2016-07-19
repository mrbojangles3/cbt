#! /usr/bin/python

import os
import fnmatch
import sys
import itertools 
from collections import defaultdict

# Thanks stackoverflow!
def find(pattern, path):
    results = []
    for root, dirs, files in os.walk(path):
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                results.append(os.path.join(root, name))
    return results

def parse_rados_bench(group):
    parsed_io = defaultdict(list)
    print(group[0])
    for results_file in group:
        # get io type by using basename of file
        base_path = os.path.dirname(results_file).split('.')[0]
        iotype = base_path.split(os.sep)[-1]
        parsed_io[iotype]
        curr_MB = []
        curr_IOPS = []
        avg_lat = -1.0
        min_lat = -1.0
        max_lat = -1.0
        if os.stat(results_file).st_size <= 30:
            continue
        with open(results_file) as f:
            # advance the fp to the first data portion
            while True:
                line = f.readline()
                if "sec Cur ops" in line:
                    break
		if line == '':
		    print "End of file encountered, unexpectedly"
		    sys.exit(1)

            for line in f:
                # bypass the rados bench live terminal output
                if "sec Cur ops" in line  or "lat:" in line:
                    continue
                if "Total time run:" in line:
                    # we have parsed to the end
                    break
                line = line.split()
                try:
                    # other needed columns should be added here
                    curr_MB.append(float(line[7]))
		    curr_IOPS.append(int(line[4]) - int(line[5]))
                except ValueError:
                    # we hit a - in the file
                    # which means this runs needs another look
                    curr_MB.append(0.0)
                    cur_IOPS.append(0)
                    continue

            #parse the latency calculated by rados bench
            for line in f:
                line = line.split(':')
                if line[0].lower() == 'average latency':
                    avg_lat=float(line[1])

                if line[0].lower() == 'max latency':
                    max_lat=float(line[1])

                if line[0].lower() == 'min latency':
                    min_lat=float(line[1])

        parsed_io[iotype].append([sum(curr_MB)/len(curr_MB), min_lat, max_lat, avg_lat,sum(curr_IOPS)/len(curr_IOPS)]) 
    return parsed_io

def usage():
    print\
    '''
    3 arguments needed:
        1. File name pattern
        2. path to search
        3. number of clients generating io
    Example invocation:
    ./radosbench_results.py "output*" /home/username/perf-results/iomix_3_seq_read/ 6
    You need quote or escape your regex for the filename pattern.
    I am using python fnmatch under the covers, those regex rules apply
    '''

def sum_results(results,clients):
    ''' Taking in a dictionary with iotypes as keys, 2d array as values'''
    for key in results.iterkeys():
        bw = 0.0
        min_lat = 0.0
        max_lat = 0.0
        avg_lat = 0.0
	iops = 0
        if key == 'delete':
            print('delete IO stats are not captured')
            continue
        for data in results[key]:
            bw += data[0]
            min_lat += data[1]
            max_lat += data[2]
            avg_lat += data[3]
            iops += data[4]
        print(key)
        print(calc_per_node_bw(bw,clients), min_lat/len(results[key]),\
                max_lat/len(results[key]), avg_lat/len(results[key]), iops)

def calc_per_node_bw(bw, nodes):
    bits_per_MiB = 8.0 * 1024 * 1024
    bits_per_sec = (bw * bits_per_MiB)/nodes
    # Print in human friendly format - Thanks stackoverflow!
    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if(abs(bits_per_sec)) < 1000:
            return "%3.3f %sbps" % (bits_per_sec,unit)
        bits_per_sec /= 1000.0
    return "%.3f %sbps" % (bits_per_sec, 'Y')

def grouper(paths, clients):
    ''' A most excellent python recipie returns an iterator'''
    args = [iter(paths)] * clients
    return itertools.izip_longest(*args, fillvalue=None)


def main(argv):
    clients = int(argv[2])
    results_path = find(argv[0], argv[1])
    results_path.sort()
    for i in grouper(results_path,clients):
        parsed_results = parse_rados_bench(i)
        sum_results(parsed_results,clients)
        print '-='*40
    

if __name__ == '__main__':
    if(len(sys.argv) != 4):
        usage()
        sys.exit("Please rerun")
    main(sys.argv[1:])
