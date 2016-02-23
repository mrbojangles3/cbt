import subprocess
import common
import settings
import monitoring
import os
import time
import threading
import logging

from cluster.ceph import Ceph
from benchmark import Benchmark

logger = logging.getLogger("cbt")

class Iomixbench(Benchmark):

    def __init__(self, cluster, config):
        super(Iomixbench, self).__init__(cluster, config)

        # config.get comes from the benchmark settings
        # settings.get comes from the cluster section
        # My changes require adding the fucntion of each host in the cluster
        # section, not the benchmark section
        self.tmp_conf = self.cluster.tmp_conf
        self.time =  str(config.get('time', '300'))
        self.concurrent_procs = config.get('concurrent_procs', 1)
        self.concurrent_ops = config.get('concurrent_ops', 16)
        self.pool_per_proc = config.get('pool_per_proc', False)  # default behavior used to be True
        self.write_only = config.get('write_only', False) #FIXME should be eliminated
        self.op_size = config.get('op_size', 4194304)
        self.pool_profile = config.get('pool_profile', 'default')
        self.write_clients = settings.getnodes('write_clients', None )
        self.rand_read_clients = settings.getnodes('rand_read_clients', None)
        self.seq_read_clients = settings.getnodes('seq_read_clients', None)
        self.delete_clients = settings.getnodes('delete_clients',None)

        self.run_dir = '%s/osd_ra-%08d/op_size-%08d/concurrent_ops-%08d/pool_profile-%s' % (self.run_dir, int(self.osd_ra), int(self.op_size), int(self.concurrent_ops), self.pool_profile)
        self.out_dir = '%s/osd_ra-%08d/op_size-%08d/concurrent_ops-%08d/pool_profile-%s' % (self.archive_dir, int(self.osd_ra), int(self.op_size), int(self.concurrent_ops), self.pool_profile)
        self.cmd_path = config.get('cmd_path', '/usr/bin/rados')

    def exists(self):
        if os.path.exists(self.out_dir):
            logger.info('Skipping existing test in %s.', self.out_dir)
            return True
        return False

    # Initialize may only be called once depending on rebuild_every_test setting
    def initialize(self):
        super(Iomixbench, self).initialize()

        logger.info('Running scrub monitoring.')
        monitoring.start("%s/scrub_monitoring" % self.run_dir)
        self.cluster.check_scrub()
        monitoring.stop()

        logger.info('Pausing for 60s for idle monitoring.')
        monitoring.start("%s/idle_monitoring" % self.run_dir)
        time.sleep(60)
        monitoring.stop()

        common.sync_files('%s/*' % self.run_dir, self.out_dir)

        return True

    def run(self):
        super(Iomixbench, self).run()
        # Remake the pools
        self.mkpools()

        if(self.delete_clients):
            del_client_arr = self.delete_clients.split(',')
        else:
            del_client_arr = []
        if(self.rand_read_clients):
            rr_client_arr = self.rand_read_clients.split(',')
        else:
            rr_client_arr = []
        if(self.seq_read_clients):
            sr_client_arr = self.seq_read_clients.split(',')
        else:
            sr_client_arr = []

        if(self.write_clients):
            wr_client_arr = self.write_clients.split(',')
        else:
            wr_client_arr = []

        if(del_client_arr or rr_client_arr or sr_client_arr ):
            logger.info("Pre-Populating cluster")
            self._pre_populate(del_client_arr, rr_client_arr, sr_client_arr)

        logger.info("Starting Rados Bench ")
        self._run(wr_client_arr, del_client_arr, rr_client_arr, sr_client_arr)

    def _pre_populate(self,del_client_arr, rr_client_arr, sr_client_arr):

        pool_name = 'rados-bench-cbt'
        op_size_str = '-b %s' % self.op_size
        mode = 'write'
        run_time = str(int(int(self.time)*1.50))
        ps = []
        concurrent_ops_str = '--concurrent-ios %s' % self.concurrent_ops
        logger.info('Pre-Population IO is run for 1.5x as long as the benchmark, to ensure sufficient data is available')

        logger.info('Launching pre-population for Delete IO')
        for i in xrange(len(del_client_arr)):
            objecter_log = '%s/objecter.%s.log' % (self.run_dir, i)
            run_name = "--run-name delete_me-%s" % (str(i))
            cmd_str = '%s -c %s -p %s bench %s %s %s %s %s --no-cleanup --show-time 2> %s' %\
                    (self.cmd_path_full, self.tmp_conf, pool_name, run_time, mode, op_size_str, concurrent_ops_str, run_name, objecter_log)

            p = common.pdsh(del_client_arr[i], cmd_str)
            ps.append(p)

        logger.info('Launching pre-population for Rand Read IO')
        for i in xrange(len(rr_client_arr)):
            objecter_log = '%s/objecter.%s.log' % (self.run_dir, i)
            run_name = "--run-name randread_me-%s" % (str(i))
            cmd_str = '%s -c %s -p %s bench %s %s %s %s %s --no-cleanup --show-time 2> %s' %\
                    (self.cmd_path_full, self.tmp_conf, pool_name, run_time, mode, op_size_str, concurrent_ops_str, run_name, objecter_log)

            p = common.pdsh(rr_client_arr[i], cmd_str)
            ps.append(p)

        logger.info('Launching pre-population for Seq Read IO')
        for i in xrange(len(sr_client_arr)):
            objecter_log = '%s/objecter.%s.log' % (self.run_dir, i)
            run_name = "--run-name seqread_me-%s" % (str(i))
            cmd_str = '%s -c %s -p %s bench %s %s %s %s %s --no-cleanup --show-time 2> %s' %\
                    (self.cmd_path_full, self.tmp_conf, pool_name, run_time, mode, op_size_str, concurrent_ops_str, run_name, objecter_log)

            p = common.pdsh(sr_client_arr[i], cmd_str)
            ps.append(p)

        # wait for all the commands to finish
        for p in ps:
            p.communicate()
        logger.info('Pre-population IO Complete')

    def _run(self, wr_client_arr, del_client_arr, rr_client_arr, sr_client_arr):
        # Can just call rados -p pool_name cleanup --run_name

        # We'll always drop caches for rados bench
        self.dropcaches()

        if self.concurrent_ops:
            concurrent_ops_str = '--concurrent-ios %s' % self.concurrent_ops
        op_size_str = '-b %s' % self.op_size

        # Make the remote directories on the clients for data collection
        for i in ['rand','seq','write','delete']:
            common.pdsh(settings.getnodes('clients'), 'mkdir -p -m0755 -- %s/%s' % (self.run_dir, i )).communicate()

        # dump the cluster config
        self.cluster.dump_config(self.run_dir)

        # Run the backfill testing thread if requested
        if 'recovery_test' in self.cluster.config:
            recovery_callback = self.recovery_callback
            self.cluster.create_recovery_test(self.run_dir, recovery_callback)

        # Run rados bench
        self.cluster.collect_ceph_configs(self.run_dir, "ceph_settings_before")
        monitoring.start(self.run_dir)
        logger.info('Running radosbench tests.')
        ps = []
        pool_name = 'rados-bench-cbt'

        ## MAYBE WE SHOULD MAKE A BUNCH OF STRINGS THEN LAUNCH BY ITERATING Through the array of commands
        ## should perf test to see how fast IO starts
        ## HERE IT GOES!!!!!
        mode = 'delete'
        for i in xrange(len(del_client_arr)):
            run_name = "--run-name delete_me-%s" % (str(i))
            out_file = '%s/%s/output.%s' % (self.run_dir,mode, i)
            objecter_log = '%s/%s/objecter.%s.log' % (self.run_dir,mode, i)
            cmd_str = '%s -c %s -p %s cleanup  %s 2> %s > %s' %\
                    (self.cmd_path_full, self.tmp_conf, pool_name, run_name, objecter_log, out_file)

            logger.info(cmd_str)
            p = common.pdsh(del_client_arr[i], cmd_str)
            ps.append(p)


        mode = 'rand'
        for i in xrange(len(rr_client_arr)):
            run_name = "--run-name randread_me-%s" % (str(i))
            out_file = '%s/%s/output.%s' % (self.run_dir,mode, i)
            objecter_log = '%s/%s/objecter.%s.log' % (self.run_dir,mode, i)
            cmd_str = '%s -c %s -p %s bench %s %s %s %s %s --no-cleanup --show-time 2> %s > %s' %\
                    (self.cmd_path_full, self.tmp_conf, pool_name, self.time, mode, op_size_str, concurrent_ops_str, run_name, objecter_log, out_file)

            logger.info(cmd_str)
            p = common.pdsh(rr_client_arr[i], cmd_str)
            ps.append(p)

        mode = 'seq'
        for i in xrange(len(sr_client_arr)):
            out_file = '%s/%s/output.%s' % (self.run_dir,mode, i)
            objecter_log = '%s/%s/objecter.%s.log' % (self.run_dir,mode, i)
            run_name = "--run-name seqread_me-%s" % (str(i))
            cmd_str = '%s -c %s -p %s bench %s %s %s %s %s --no-cleanup --show-time 2> %s > %s' %\
                    (self.cmd_path_full, self.tmp_conf, pool_name, self.time, mode, op_size_str, concurrent_ops_str, run_name, objecter_log, out_file)

            logger.info(cmd_str)
            p = common.pdsh(sr_client_arr[i], cmd_str)
            ps.append(p)

        mode = 'write'
        for i in xrange(len(wr_client_arr)):
            out_file = '%s/%s/output.%s' % (self.run_dir,mode, i)
            objecter_log = '%s/%s/objecter.%s.log' % (self.run_dir,mode, i)
            run_name = "--run-name seqread_me-%s" % (str(i))
            cmd_str = '%s -c %s -p %s bench %s %s %s %s %s --no-cleanup --show-time 2> %s > %s' %\
                    (self.cmd_path_full, self.tmp_conf, pool_name, self.time, mode, op_size_str, concurrent_ops_str, run_name, objecter_log, out_file)

            logger.info(cmd_str)
            p = common.pdsh(wr_client_arr[i], cmd_str)
            ps.append(p)
        # wait for all the commands to finish
        for p in ps:
            p.communicate()

        ## THERE IT WENT
#        for i in xrange(self.concurrent_procs):
#            out_file = '%s/output.%s' % (run_dir, i)
#            objecter_log = '%s/objecter.%s.log' % (run_dir, i)
#            # default behavior is to use a single storage pool 
#            pool_name = 'rados-bench-cbt'
#            run_name = '--run-name `hostname -s`-%s'%i
#            if self.pool_per_proc: # support previous behavior of 1 storage pool per rados process
#                pool_name = 'rados-bench-`hostname -s`-%s'%i
#                run_name = ''
#            rados_bench_cmd = '%s -c %s -p %s bench %s %s %s %s %s --no-cleanup --show-time 2> %s > %s' % \
#                 (self.cmd_path_full, self.tmp_conf, pool_name, self.time, mode, op_size_str, concurrent_ops_str, run_name, objecter_log, out_file)
#            p = common.pdsh(settings.getnodes('clients'), rados_bench_cmd)
#            ps.append(p)
#        for p in ps:
#            p.wait()
        monitoring.stop(self.run_dir)
        self.cluster.collect_ceph_configs(self.run_dir, "ceph_settings_after")

        # If we were doing recovery, wait until it's done.
        if 'recovery_test' in self.cluster.config:
            self.cluster.wait_recovery_done()

        # Finally, get the historic ops
        self.cluster.dump_historic_ops(self.run_dir)
        common.sync_files('%s/*' % self.run_dir,self.out_dir)

    def mkpools(self):
        monitoring.start("%s/pool_monitoring" % self.run_dir)
        if self.pool_per_proc: # allow use of a separate storage pool per process
            for i in xrange(self.concurrent_procs):
                for node in settings.getnodes('clients').split(','):
                    node = node.rpartition("@")[2]
                    self.cluster.rmpool('rados-bench-%s-%s' % (node, i), self.pool_profile)
                    self.cluster.mkpool('rados-bench-%s-%s' % (node, i), self.pool_profile)
        else: # the default behavior is to use a single Ceph storage pool for all rados bench processes
            self.cluster.rmpool('rados-bench-cbt', self.pool_profile)
            self.cluster.mkpool('rados-bench-cbt', self.pool_profile)
        monitoring.stop()

    def recovery_callback(self): 
        common.pdsh(settings.getnodes('clients'), 'sudo killall -9 rados').communicate()

# Make sure you have launched the IO from a system other than the clients or the results will be deleted!
# Also must use /tmp/cbt for tmp dir
    def cleanup(self):
        common.pdsh(settings.getnodes('clients','mons','osds','rgws','mds'),'rm -rf /tmp/cbt')

    def __str__(self):
        return "%s\n%s\n%s" % (self.run_dir, self.out_dir, super(Iomixbench, self).__str__())
