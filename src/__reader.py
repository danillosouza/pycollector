# -*- coding:utf-8 -*-

"""
    File: __reader.py
    Description: This module implements the logic of a Reader.

    A Reader is responsible to collect data from some source and
    store it as a message in the internal queue of the collector.

    In order to implement your Reader, you must extend this class
    and write 2 methods, like this:

    ==========
    from __reader import Reader

    class MyReader(Reader):
        def setup(self):
            ... # Provide here whatever initializations are necessary.
            ... # Properties defined in a conf.yaml will be available
            ... # here as instance variables (e.g., self.foo)

            ... # You may define a list of required confs, e.g.:
            ... self.required_confs = ['foo', 'bar']

            ... # and call check_required_confs to check if it was loaded properly
            ... self.check_required_confs()
            ... # If they are not found in your conf, an exception is raised

        def read(self):
            ... # Your code goes here.
            ... # You must call the store() method to put your message
            ... # in the queue.
    ==========

    There are basically 2 flavors of Readers: asynchronous and synchronous.

    Synchronous Readers are defined with a 'period' in conf.yaml
    Asynchronous Readers are defined WITHOUT a 'period' in conf.yaml.

    For synchronous Readers, after each 'period', the read() method is called,
    For asynchronous Readers, read() is called just once.
"""

import time
import Queue
import pickle
import logging
import traceback
import threading

import helpers.kronos as kronos

from __exceptions import ConfigurationError


class Reader(threading.Thread):
    def __init__(self,
                 queue,                   # queue to store read messages
                 conf={},                 # additional configurations
                 period=None,             # period of readings
                 blockable=True,          # retry if a message was not stored
                 retry_timeout=None,      # if timeout is reached, discard message
                 checkpoint_enabled=False,# default is to not deal with checkpoint
                 checkpoint_period=60,    # period between checkpoints
                 health_check_period=300, # period to log status
                 thread_name='Reader',    # thread name to easily recognize in log
                 last_checkpoint=''       # may have a writer checkpoint
                 ):

        self.log = logging.getLogger('pycollector')
        self.conf = conf
        self.processed = 0
        self.discarded = 0
        self.busy = False
        self.queue = queue
        self.blocked = False
        self.period = period
        self.blockable = blockable
        self.thread_name = thread_name
        self.retry_timeout = retry_timeout
        self.checkpoint_enabled = checkpoint_enabled
        self.health_check_period = health_check_period
        self.checkpoint_period = checkpoint_period
        self.last_checkpoint = last_checkpoint
        self.set_conf(conf)

        if not self.blockable:
            self.retry_timeout = 0

        self.schedule_tasks()
        self.setup()
        threading.Thread.__init__(self, name=self.thread_name)

    def schedule_checkpoint_writing(self):
        self.scheduler.add_interval_task(self._write_checkpoint,
                                         "",
                                         0,
                                         self.checkpoint_period,
                                         kronos.method.threaded,
                                         [],
                                         None)

    def schedule_periodic_task(self):
        self.scheduler.add_interval_task(self._read,
                                         "",
                                         0,
                                         self.period,
                                         kronos.method.threaded,
                                         [],
                                         None)

    def schedule_single_task(self):
        self.scheduler.add_single_task(self._read,
                                       "",
                                       0,
                                       kronos.method.threaded,
                                       [],
                                       None)
    def check_required_confs(self):
        """Validate if required confs are present.
           required_confs are supposed to be set in setup() method."""
        for item in self.required_confs:
            if not hasattr(self, item):
                raise(ConfigurationError("%s not defined in your conf.yaml" % item))

    def set_conf(self, conf):
        """Turns configuration properties
           into instance properties."""
        try:
            for item in conf:
                if isinstance(conf[item], str):
                    exec("self.%s = \"\"\"%s\"\"\"" % (item, conf[item]))
                else:
                    exec("self.%s = %s" % (item, conf[item]))
            self.log.info("Configuration settings added with success into reader.")
        except Exception, e:
            self.log.error("Stack trace: %s" % traceback.format_exc())
            raise(ConfigurationError("Invalid configuration item: %s" % item))

    def _write_checkpoint(self):
        """Write checkpoint in disk."""
        try:
            lc = self.last_checkpoint
            f = open(self.checkpoint_path, 'w')
            pickle.dump(lc, f)
            f.close()
            self.log.debug('Checkpoint written: %s' % lc)
        except Exception, e:
            self.log.error('Error writing checkpoint in %s' % self.checkpoint_path)

    def _set_checkpoint(self, checkpoint):
        """Updates last_checkpoint.
           Shouldn't be called by subclasses."""
        self.last_checkpoint = checkpoint
        self.log.debug("Last checkpoint: %s" % checkpoint)

    def schedule_tasks(self):
        """Schedule periodic or single tasks"""
        self.scheduler = kronos.ThreadedScheduler()
        if self.period:
            self.schedule_periodic_task()
        else:
            self.schedule_single_task()
        if self.checkpoint_enabled:
            self.schedule_checkpoint_writing()
        self.log.debug("Tasks scheduled with success")

    def _store(self, msg):
        """Internal method to store read messages.
           Shouldn't be called by subclasses."""
        success = False
        try:
            self.queue.put(msg, block=self.blockable, timeout=self.retry_timeout)
            self.processed += 1
            success = True
            self.log.debug("Message read: %s" % msg)
        except Queue.Full:
            self.discarded += 1
            self.log.info("Discarded message: %s, due to full queue" % msg)
        except Exception, e:
            self.discarded += 1
            self.log.error("Can't store in queue message: %s" % msg)
            self.log.error(traceback.format_exc())

        if success and self.checkpoint_enabled:
            self._set_checkpoint(msg.checkpoint)
        return success

    def _read(self):
        """Method called internally to read a message.
           It is called in the end of each period
           in the case of a periodic task.
           Shouldn't be called by subclasses."""
        try:
            if self.busy:
                self.log.debug("Reader is busy with other reading. Skipping this scheduling.")
                return

            self.busy = True
            self.read()
            self.busy = False
        except Exception, e:
            self.log.error("Error running read() method.")
            self.log.error(traceback.format_exc())

    def store(self, msg):
        """Stores a read message.
           This should be called by subclasses."""
        return self._store(msg)

    def run(self):
        """Starts the reader"""
        self.scheduler.start()
        while True:
            self.log.debug("running")
            time.sleep(self.health_check_period)

    def __str__(self):
        return str(self.__dict__)

    def setup(self):
        """Subclasses should implement."""

    def read(self):
        """Subclasses should implement."""


