import asynctest as unittest
import server_process
import os
import random
import shutil
import asyncio
import urllib.request
import string
import functools

class TestNewServerProcess(unittest.TestCase):
    SERVER_FILE = 'server.jar'
    def setUp(self):
        # Create directory with minecraft server and chdir there
        self.directory = 'new_server_process_test_' + ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        os.mkdir(self.directory)
        os.chdir(self.directory)

        # Download Minecraft server
        mc_url = 'https://launcher.mojang.com/mc/game/1.12.2/server/886945bfb2b978778c3a0288fd7fab09d315b25f/server.jar'
        urllib.request.urlretrieve(mc_url, filename=self.SERVER_FILE)

        # Agree to EULA
        with open('eula.txt', 'w') as f:
            f.write("eula=true")

    def tearDown(self):
        # Remove directory with minecraft server
        os.chdir('..')
        shutil.rmtree(self.directory)
    
    async def test_create_and_stop_new_server(self):
        # Run server
        server = await server_process.NewServerProcess.launch(server_file=self.SERVER_FILE)
        # Check status
        assert server.status == server_process.ServerProcess.RUNNING
        # Stop server
        await server.stop()
        # Check status
        assert server.status == server_process.ServerProcess.OFF

    async def test_deny_to_create_two_servers(self):
        ev_loop = asyncio.get_event_loop()

        # Run one server
        server = await server_process.NewServerProcess.launch(server_file=self.SERVER_FILE)
        # Try to run another server, it should raise an exception
        self.assertAsyncRaises(server_process.ServerAlreadyRunningError, 
            functools.partial(server_process.NewServerProcess.launch, server_file=self.SERVER_FILE))
        # Stop server
        await server.stop()
