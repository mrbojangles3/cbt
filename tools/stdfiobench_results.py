#! /usr/bin/python

import os
import fnmatch
import sys
import itertools 
import simplejson
from collections import defaultdict

# Thanks stackoverflow!
def find(pattern, path):
    results = []
    for root, dirs, files in os.walk(path):
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                results.append(os.path.join(root, name))
    return results

def parse_stdfiobench(file_group):
    parsed_io = defaultdict(list)
    for results_file in file_group:
        # get io type by using basename of file
	# getting the iomix of this run, e.g rwmixread-80
        iotype = results_file.split(os.sep)[-3]
        parsed_io[iotype]
	# skip small files
        if os.stat(results_file).st_size <= 30:
	    print('Bad News,%s is empty, skipping' % results_file)
            continue
        with open(results_file) as data_file:
		data = simplejson.load(data_file)
		#populate return array,this will create an array of arrays with results
		parsed_io[iotype].append([data['jobs'][0]['read']['bw'],
		data['jobs'][0]['read']['lat']['min'],
		data['jobs'][0]['read']['lat']['max'],
		data['jobs'][0]['read']['lat']['mean'],
		data['jobs'][0]['read']['lat']['stddev'],
		data['jobs'][0]['read']['iops'],
		data['jobs'][0]['write']['bw'],
		data['jobs'][0]['write']['lat']['min'],
		data['jobs'][0]['write']['lat']['max'],
		data['jobs'][0]['write']['lat']['mean'],
		data['jobs'][0]['write']['lat']['stddev'],
		data['jobs'][0]['write']['iops']])
    print results_file
    return parsed_io

def usage():
    print\
    '''
    4 arguments needed:
        1. File name pattern
        2. path to search
        3. number of clients generating IO
        4. number of data nodes
    Example invocation:
    ./radosbench_results.py "output*" /home/username/perf-results/iomix_3_seq_read/ 4 6
    You need quote or escape your regex for the filename pattern.
    I am using python fnmatch under the covers, those regex rules apply
    '''

def sum_results(results,data_nodes):
    ''' Taking in a dictionary with iotypes as keys, 2d array as values'''
    for key in results.iterkeys():
        read_bw = 0.0
        read_min_lat = 0.0
        read_max_lat = 0.0
        read_avg_lat = 0.0
	read_stddev_lat = 0.0
	read_iops = 0.0
        write_bw = 0.0
        write_min_lat = 0.0
        write_max_lat = 0.0
        write_avg_lat = 0.0
	write_stddev_lat = 0.0
	write_iops = 0.0
        for data in results[key]:
            read_bw += data[0]
            read_min_lat += data[1]
            read_max_lat += data[2]
            read_avg_lat += data[3]
            read_stddev_lat += data[4]
            read_iops += data[5]
            write_bw += data[6]
            write_min_lat += data[7]
            write_max_lat += data[8]
            write_avg_lat += data[9]
            write_stddev_lat += data[10]
            write_iops += data[11]
        print(key)
	print "Avg client read bandwidth MiB/s: " + str((read_bw / len(results[key]))/1024)
	print "Avg client read min latency msec: " + str(read_min_lat / len(results[key]))
	print "Avg client read max latency msec: " + str(read_max_lat / len(results[key]))
	print "Avg client read avg latency msec: " + str(read_avg_lat / len(results[key]))
	print "Avg client read stddev latency msec: " + str(read_stddev_lat / len(results[key]))
	print "Avg client read iops:" + str(read_iops / len(results[key]))
	print
	print "Avg client write bandwidth MiB/s: " + str((write_bw / len(results[key]))/1024)
	print "Avg client write min latency msec: " + str(write_min_lat / len(results[key]))
	print "Avg client write max latency msec: " + str(write_max_lat / len(results[key]))
	print "Avg client write avg latency msec: " + str(write_avg_lat / len(results[key]))
	print "Avg client write stddev latency msec: " + str(write_stddev_lat / len(results[key]))
	print "Avg client write iops: " + str(write_iops / len(results[key]))

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
    for i in grouper(results_path,clients):
        parsed_results = parse_stdfiobench(i)
        sum_results(parsed_results,data_nodes)
        print '-='*40
    

if __name__ == '__main__':
    if(len(sys.argv) != 5):
        usage()
        sys.exit("Please rerun")
    main(sys.argv[1:])
