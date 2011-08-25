
import time
import threading

import helpers.kronos as kronos 


class Writer(threading.Thread):
    def __init__(self, periodic=False, interval=0):
        self.scheduler = kronos.ThreadedScheduler()
        if periodic == True:
            self.scheduler.add_interval_task(self.write,
                                 "periodic task",
                                 0,
                                 interval,
                                 kronos.method.threaded,
                                 [],
                                 None)
        else:
            self.scheduler.add_single_task(self.write,
                                           "single task",
                                           0,
                                           kronos.method.threaded,
                                           [],
                                           None)
        threading.Thread.__init__(self)

    def write(self):
        """Subclasses should implement."""
        pass

    def run(self):
        self.scheduler.start()


if __name__ == "__main__":
    class MyWriter(Writer):
        def write(self):
            print "know thyself"

    writer = MyWriter(periodic=True, interval=1)
    writer.start()

    writer = MyWriter(periodic=True, interval=4)
    writer.start()
    while True:
        pass
