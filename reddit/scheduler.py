import threading


class SmartJob:
    def __init__(self, job_id, action, lock, logger):
        self.id = job_id
        self.action = action
        self.running = False
        self.misfired = False
        self.job_info_lock = lock
        self.logger = logger
        
    def execute_job(self):
        with self.job_info_lock:
            # Check if a job is already running
            if self.running:
                # Indicate misfire and die
                self.logger.debug(f"{self.id} Misfired")
                self.misfired = True
                return
            else:
                # Mark job as started
                self.running = True
                self.misfired = False

        # Run the job
        try:
            self.action()
        except Exception as error:
            self.logger.debug(f"{self.id} Exited with an exception - " + repr(error))
            self.logger.error(error)

        # Run misfire recovery on same thread in the event of a misfire
        while True:
            with self.job_info_lock:
                misfired = self.misfired
                # Clear misfire status and attempt recovery. This will get reset to true if another misfire occurs
                # while recovering
                if misfired:
                    self.misfired = False
            # Run the job, but outside of the lock
            if misfired:
                self.action()
            else:
                # If no misfire occurred, mark the job as not running and break the recovery loop
                with self.job_info_lock:
                    self.running = False
                    break


class SmartScheduler:
    def __init__(self, scheduler):
        self.scheduler = scheduler
        self.jobs = {}
        self.job_info_lock = threading.Lock()

    def start(self):
        self.scheduler.start()
        
    def register_job(self, job_id, interval, action, logger):
        self.jobs[job_id] = SmartJob(job_id, action, self.job_info_lock, logger=logger)
        self.scheduler.add_job(self.jobs[job_id].execute_job, 'interval', id=job_id, seconds=interval)
