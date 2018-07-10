import asyncio
import os
import re
import psutil

class ServerProcess:
    """Base class for all server process wrappers
    """
    OFF = 0
    STARTING = 1
    RUNNING = 2
    STOPPING = 3
    UNKNOWN = -1

    def __init__(self):
        self._status = ServerProcess.UNKNOWN
        self.pid = -1

    def _lockfile_create(self):
        """ Create lockfile with this process PID
        """
        with open("lock.pid", "w") as f:
            f.write(str(self.pid))

    @classmethod
    def _lockfile_delete(cls):
        """ Delete lockfile
        """
        os.remove("lock.pid")
    
    @classmethod
    def _check_lock(cls):
        """ Check if server is already running (using lockfile) and check if lockfille is correct (check if there is MC server running on this PID)
        """
        try:
            f = open("lock.pid", "r")
            pid_s = f.readline()
            pid = int(pid_s)

            # Check if process with PID exists and is Minecraft server; otherwise return None and delete PID-lock
            try:
                p = psutil.Process(pid)
                if p.name != "java":
                    ServerProcess._lockfile_delete()
                    return None
            except psutil.NoSuchProcess:
                ServerProcess._lockfile_delete()
                return None
            return int(pid_s)
        except FileNotFoundError:
            return None


class ServerRunningError(BaseException):
    """ Error raised when server has not run successfully 
    """
    def __init__(self, return_code:str, last_msg:int):
        self.return_code = return_code
        self.last_msg = last_msg


class ServerAlreadyRunningError(BaseException):
    """ Error raised when server is already running
    """
    pass


class NewServerProcess(ServerProcess):
    """Runs and wraps newly running server process
    """

    @classmethod
    async def launch(cls, server_file="server.jar", xms="1024M", xmx="1024M"):
        """Launches server and returns new ServerProcess

        server_file - name of Minecraft's server JAR
        xms - initial amount of RAM (Java's -Xms option)
        xmx - maximal amount of RAM (Java's -Xmx option)
        """
        self = cls()
        self._status = ServerProcess.OFF

        # Check if server is already running
        if ServerProcess._check_lock():
            raise ServerAlreadyRunningError

        # Prepare starting command and launch server's process
        server_cmd="java"
        server_params = ["-Xms{}".format(xms), "-Xmx{}".format(xmx), "-jar", server_file, "nogui"]
        process = await asyncio.create_subprocess_exec(
            server_cmd, 
            *server_params,
            stdin=asyncio.subprocess.PIPE, 
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        self.process = process
        self._status = ServerProcess.STARTING
        self.pid = process.pid

        # Create lockfile
        self._lockfile_create()

        # Set stdin and stdout pipes
        self.stdin = process.stdin
        self.stdout = process.stdout

        # Wait until server is started
        done_regex_pattern = r"Done \(.*\)!" # pattern for Done! info on stdout
        done_regex = re.compile(done_regex_pattern)
        done = False # True if server started successfully at the end of the loop
        line_b = b"nonempty"
        line = "" # last line on server's stdout
        while line_b:
            line_b = await process.stdout.readline()
            line = line_b.decode("utf-8").strip() or line
            if done_regex.search(line) is not None:
                done = True
                break
        
        if not done:
            # Server has not started sucessfully, throw exception
            raise ServerRunningError(process.pid, line)

        self._status = ServerProcess.RUNNING
        return self
    
    async def command(self, command:str):
        """Calls command on server

        command - command to be called
        """
        self.stdin.write("{}\n".format(command).encode("utf-8"))
    
    async def stop(self):
        """Gracefully stops this server (using stop command)
        """
        self._status = ServerProcess.STOPPING
        await self.command("stop")
        await self.process.wait()
        # Delete lockfile
        ServerProcess._lockfile_delete()
        self._status = ServerProcess.OFF
    
    @property
    def status(self):
        """Returns current server status
        """
        if self.process.returncode:
            self._status = ServerProcess.OFF
            return ServerProcess.OFF
        return self._status