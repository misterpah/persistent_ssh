import paramiko
import time
import platform
import sys
import re
import io


class PersistentSSH_paramiko_screen:
    def __init__(self, persistentID, hostName,
                 username, password="", sshKeyFilePath=""):
        self.hostName = hostName
        if sshKeyFilePath != "":
            self.sshKey = sshKeyFilePath
        self.username = username
        self.password = password
        self.screenAvailable = False
        self.persistentID = persistentID
        self.logFile = self.persistentID + ".log"
        self.version = 1
        self.startIndex = ""
        self.endIndex = ""

        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        if self.sshKey != None:
            k = paramiko.RSAKey.from_private_key_file(self.sshKey)
            self.client.connect(
                hostname=self.hostName,
                username=self.username,
                pkey=k
            )
        else:
            self.client.connect(
                hostname=self.hostName,
                username=self.username,
                password=self.password
            )

    def startScreen(self):
        if self.screenAvailable == False:
            # create Logfile
            configFile = []
            configFile.append("logfile {}".format(self.logFile))
            configFile.append("logfile flush 1")
            configFile.append("log on")
            config_cmd = "echo '{}' > ~/screen.cfg && echo done".format(
                "\\n".join(configFile))
            result = self.runCommandParamiko(config_cmd)

            # check if there is already a screen with the same name
            grepScreen = self.runCommandParamiko(
                "screen -ls | grep {} ".format(self.persistentID))
            createNewScreen = False
            if len(grepScreen['stdout']) >= 1:
                print("screen {} exist. using it.".format(
                    self.persistentID))
            else:
                print("screen {} not exist. creating...".format(
                    self.persistentID))
                createNewScreen = True

            # create screen if flag is True
            if createNewScreen == True:
                result = self.runCommandParamiko(
                    "screen -L -c ~/screen.cfg -dmS {} ".format(
                        self.persistentID) +
                    "&& sleep 1 " +
                    "&& echo done"
                )
                self.runCommand("set prompt='screen$ '")
                self.clearLog()
            self.screenAvailable = True

    def destroySession(self):
        if self.screenAvailable != False:
            self.runCommand("exit")
            self.runCommandParamiko("rm ~/screen.cfg")
            self.runCommandParamiko("rm ~/{}".format(self.logFile))

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
                "echo PRMKSCR_START &&"+command+" && echo && echo PRMKSCR_STOP",
                "`/bin/echo -ne \\\\r`",
                doubleQuote)

        sh_cmd = "{} && echo done".format(screen_cmd)
        result = self.runCommandParamiko(sh_cmd)
        time.sleep(2)  # sleep 2sec because flush is 1sec
        return result

    def getLog(self):
        # get log file
        global log
        result = self.runCommandParamiko("cat {}".format(self.logFile))
        if self.version == 2:
            if self.startIndex != "" and self.endIndex != "":
                result['stdout'] = result['stdout'][self.startIndex:self.endIndex]
                self.startIndex = ""
                self.endIndex = ""
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
                # trying to get PRMKSCR_START and PRMKSCR_STOP
                if len(idleCheck['stdout']) > 0:
                    startIndex = None
                    endIndex = None
                    # search PRMKSCR_START
                    for x in range(0, len(idleCheck['stdout'])):
                        if idleCheck['stdout'][x].find("PRMKSCR_START") != -1:
                            # always ignore the first line
                            if x != 0:
                                startIndex = x
                                break
                    # search PRMKSCR_STOP
                    for y in range(0, len(idleCheck['stdout'])):
                        if idleCheck['stdout'][y].find("PRMKSCR_STOP") != -1:
                            # always ignore the first line
                            if y != 0:
                                endIndex = y
                                break
                    print(startIndex, endIndex)
                    # if both PRMKSCR not None
                    if ((startIndex != None) and (endIndex != None)):
                        # we don't want the PRMKSCR_START statement.
                        # skip by adding 1 to startIndex
                        self.startIndex = startIndex + 1
                        self.endIndex = endIndex
                        loop = False
                        print("Complete. {} sec".format(i))
                        ret = True
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
    cmd = "accounts {}".format(username)
    obj.runCommand(cmd)
    if obj.waitCommandComplete(10) == True:
        log = obj.getLog()
        print(log)
