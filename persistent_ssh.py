import paramiko
import time
import platform
import sys
import re
import io
import re


class PersistentSSH_paramiko_screen:
    def __init__(self, persistentID, hostName,
                 username, password="", sshKeyFilePath="", newScreen=True):
        self.screenAvailable = False
        self.persistentID = persistentID
        self.logFile = self.persistentID + ".log"
        self.configFile = self.persistentID + ".cfg"
        self.version = 1
        self.waitCommandCompleteFlag = False

        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        if sshKeyFilePath != "":
            k = paramiko.RSAKey.from_private_key_file(sshKeyFilePath)
            self.client.connect(
                hostname=hostName,
                username=username,
                pkey=k
            )
        else:
            self.client.connect(
                hostname=hostName,
                username=username,
                password=password
            )
        self.screenAvailable = self.checkScreen()
        if newScreen == True:
            self.destroySession()

    def checkScreen(self):
        ret = False
        # check if there is already a screen with the same name
        grepScreen = self.runCommandParamiko(
            "screen -ls | grep {} ".format(self.persistentID))
        if len(grepScreen['stdout']) >= 1:
            ret = True
            print("screen available: {}".format(self.persistentID))
        return ret

    def startScreen(self):
        if self.screenAvailable == False:
            print("screen not available")
            createConfigFile = False
            # find config file
            grepScreen = self.runCommandParamiko(
                "ls {} ".format(self.persistentID))
            if grepScreen['stderr'] is not []:
                # config file not available
                createConfigFile = True
            # create configFile
            if createConfigFile is True:
                print("creating config file")
                configStr = []
                configStr.append("logfile {}".format(self.logFile))
                configStr.append("logfile flush 1")
                configStr.append("log on")
                configStr = "\n".join(configStr)
                if sys.version_info[0] == 2:
                    configStr = configStr.decode("utf-8")
                sftp = self.client.open_sftp()
                sftp.putfo(io.StringIO(configStr), self.configFile)
                sftp.close()
            print("create screen")
            self.runCommandParamiko(
                "screen -L -c ~/{} -dmS {} ".format(
                    self.configFile, self.persistentID) +
                "&& echo done"
            )
            self.screenAvailable = True

            print("get simple screen number")
            result = self.runCommandParamiko(
                "screen -ls | grep {}".format(self.persistentID))
            self.persistentID = result['stdout'][0].split(".")[0].strip()
            print("simple screen number = {}".format(self.persistentID))

            self.runCommand("set prompt='screen$ '")
            self.clearLog()
            print("screen created.")

    def destroySession(self):
        if self.screenAvailable != False:
            self.runCommand("exit")
            self.runCommandParamiko("rm ~/{}".format(self.configFile))
            self.runCommandParamiko("rm ~/{}".format(self.logFile))
            self.screenAvailable = False

    def saveStringAsBashFile(self, bash_string):
        if sys.version_info[0] == 2:
            bash_string = bash_string.decode("utf-8")
        sftp = self.client.open_sftp()
        filename = "{}.sh".format(self.persistentID)
        sftp.putfo(io.StringIO(bash_string), filename)
        self.runCommandParamiko("chmod +x ~/{}".format(filename))
        return "./{}".format(filename)

    def runCommandParamiko(self, cmdline):
        stdin, stdout, stderr = self.client.exec_command(cmdline)

        result = {}
        result['stdout'] = []
        result['stderr'] = []
        for line in stdout:
            result['stdout'].append(line.strip())
        try:
            for line in stderr:
                result['stderr'].append(line.strip())
        except:
            pass
        return result

    def runCommand(self, command):
        self.startScreen()
        singleQuote = "\x27"
        doubleQuote = "\x22"
        # reference https://stackoverflow.com/a/42341860

        screen_cmd = "screen -S {} -p 0 -X stuff {}{}{}{}".format(
            self.persistentID,
            doubleQuote,
            command,
            "`/bin/echo -ne \\\\r`",
            doubleQuote)

        if self.version == 2:
            screen_cmd = "screen -S {} -p 0 -X stuff {}{}{}{}".format(
                self.persistentID,
                doubleQuote,
                "echo PRMKSCR_START ;"+command+" ; echo ; echo PRMKSCR_STOP",
                "`/bin/echo -ne \\\\r`",
                doubleQuote)

        sh_cmd = "{} && echo done".format(screen_cmd)
        result = self.runCommandParamiko(sh_cmd)
        time.sleep(2)  # sleep 2sec because flush is 1sec
        return result

    def getLog(self):
        # get log file
        result = self.runCommandParamiko("cat {}".format(self.logFile))
        if self.version == 2:
            if self.waitCommandCompleteFlag == True:
                regex = r"PRMKSCR_START([\s\S]*?)PRMKSCR_STOP"
                stdout = re.findall(regex, "\n".join(result['stdout']))[-1]
                result['stdout'] = stdout
        return result

    def clearLog(self):
        # delete log File
        result = self.runCommandParamiko("rm {}".format(self.logFile))
        time.sleep(1)
        return result

    def waitCommandComplete(self, max_iteration=10):
        # Check output every 1 second.
        # stop waiting & return false after max_iteration iteration.
        ret = False
        loop = True
        i = 0
        time.sleep(1)
        while loop:
            idleCheck = self.getLog()
            if self.version == 1:
                if len(idleCheck['stdout']) > 0:
                    if idleCheck['stdout'][-1].startswith("screen$") == True:
                        loop = False
                        print("Complete. {} sec".format(i))
                        ret = True
                        break
            if self.version == 2:
                # trying to get PRMKSCR_START and PRMKSCR_STOP using regex
                regex = r"PRMKSCR_START([\s\S]*?)PRMKSCR_STOP"
                result = re.findall(regex, "\n".join(idleCheck['stdout']))
                print(idleCheck)
                print(result)
                if len(result) == 0:
                    pass
                else:
                    if result[-1].find("; echo") != -1:
                        pass
                    else:
                        print("command completed")
                        ret = True
                        self.waitCommandCompleteFlag = True
                        break
            if i > max_iteration:
                loop = False
                print("not Complete after {} sec".format(max_iteration))
                break
            if i % 2 == 0:
                print("still waiting. {} sec".format(i))
            i += 1
            time.sleep(1)  # sleep 1 sec each iteration
        return ret

    def run_ssh_command(self, cmd_arr, max_iteration=60):
        self.clearLog()
        for cmd in cmd_arr:
            self.runCommand(cmd)
            time.sleep(1)

        result = {}
        if self.waitCommandComplete(max_iteration):
            result['stdout'] = self.getLog()['stdout']
            result['stderr'] = self.getLog()['stderr']
        else:
            print("time too short?")

        if result['stdout']:
            result['stdout'].pop(0)
            temp = []
            for el in result['stdout']:
                temp.append(self.remove_ansi(el))

            result['stdout'] = temp

        if result['stderr']:
            result['stderr'].pop(0)

        return result

    def remove_ansi(self, str):
        ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')
        result = ansi_escape.sub('', str)
        return result


if __name__ == "__main__":
    import getpass
    ipaddress = "1.2.3.4"
    username = "username"
    password = getpass.getpass("password: ")

    obj = PersistentSSH_paramiko_screen(
        "screen_name", ipaddress, username, password)
    # using version 2
    obj.version = 2
    # clear log to remove old output
    obj.clearLog()

    # run command
    cmd = "uptime"
    obj.runCommand(cmd)
    if obj.waitCommandComplete(5) == True:
        log = obj.getLog()
        print(log)

    obj.destroySession()
