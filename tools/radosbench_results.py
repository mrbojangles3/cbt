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

def simple_percentile(arr, num):
    '''
    num should be a string value from 0.0 to 1.0
    '''
    arr.sort()
    key  = int(len(arr)  * float(num)) # int() rounds down
    return arr[key]

def parse_rados_bench(group):
    '''
    Parses a group  of rados bench output files, essentially the cli output that
    has been piped to a file
    the files are grouped by the IO type.
    the IO type is they key for a hash map
    '''
    parsed_io = defaultdict(list)
    print(group[0])
    for results_file in group:
        # get io type by using basename of file
        base_path = os.path.dirname(results_file).split('.')[0]
        iotype = base_path.split(os.sep)[-1]
        parsed_io[iotype]
        curr_MB = []
        curr_IOPS = []
        curr_LAT = []
        avg_lat = -1.0
        min_lat = -1.0
        max_lat = -1.0
        # Avoid Empty files, should make some noise here
        if os.stat(results_file).st_size <= 30:
            print(results_file + " is EMPTY!!!!")
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
                    curr_LAT.append(float(line[8]))
                    curr_IOPS.append(int(line[4]) - int(line[5]))
                except ValueError:
                    # we hit a - in the file
                    # which means this runs needs another look
                    curr_MB.append(0.0)
                    curr_IOPS.append(0)
                    continue

            #parse the latency calculated by rados bench
            for line in f:
                line = line.split(':')
                if 'average latency' in line[0].lower():
                    avg_lat=float(line[1])

                if 'max latency' in line[0].lower():
                    max_lat=float(line[1])

                if 'min latency' in line[0].lower():
                    min_lat=float(line[1])

	percentile = simple_percentile(curr_LAT,'0.85') # 85th percentile of latency, a chosen upperbound
        parsed_io[iotype].append([sum(curr_MB)/len(curr_MB), min_lat, max_lat, avg_lat,sum(curr_IOPS)/len(curr_IOPS),percentile]) 
    return parsed_io

def usage():
    print\
    '''
    3 arguments needed:
        1. File name pattern
        2. path to search
        3. number of rados bench instances generating IO
        4. number of data nodes
    Example invocation:
    ./radosbench_results.py "output.0.*" /home/username/perf-results/iomix_3_seq_read/ 4 6
    You need quote or escape your regex for the filename pattern.
    Be mindful of the hostname that is actually acting as a client, it doesn't ALWAYS have client in it
    I am using python fnmatch under the covers, those regex rules apply
    '''

def sum_results(results,data_nodes):
    ''' Taking in a dictionary with iotypes as keys, 2d array as values'''
    for key in results.iterkeys():
        bw = 0.0
        min_lat = 0.0
        max_lat = 0.0
        avg_lat = 0.0
        iops = 0
        percentile = 0.0
        if key == 'delete':
            print('delete IO stats are not captured')
            continue
        for data in results[key]:
            bw += data[0]
            min_lat += data[1]
            max_lat += data[2]
            avg_lat += data[3]
            iops += data[4]
            percentile += data[5]
        print(key)
        # convert rados bench seconds to millisecondsrint(key)
        try:
            print(calc_per_node_bw(bw,data_nodes),\
            '{0:.3f}ms'.format(min_lat/len(results[key])*1000),\
            '{0:.3f}ms'.format(max_lat/len(results[key])*1000),\
            '{0:.3f}ms'.format(avg_lat/len(results[key])*1000),\
            (iops),\
            '{0:.3f}ms'.format(percentile/len(results[key])*1000))
        except ZeroDivisionError:
            print("Hit a divide by zero, there are issues")

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
    data_nodes = int(argv[3])
    results_path = find(argv[0], argv[1])
    results_path.sort()
    # Parses all files that match the user input pattern for a given IO type
    # e.g. output.0.client-1 and output.1.client-1 are parsed if they are
    # in the same directory and match the given input pattern
    for i in grouper(results_path,clients):
        parsed_results = parse_rados_bench(i)
        sum_results(parsed_results,data_nodes)
        print '-='*40


if __name__ == '__main__':
    if(len(sys.argv) != 5):
        usage()
        sys.exit("Please rerun")
    main(sys.argv[1:])
