# persistent_ssh
paramiko + screen = persistent ssh

## Reason of writing this library
want to run sudo command from SSH.


## How To use

```

if __name__ == "__main__":
    import getpass
    ipaddress = "1.2.3.4"
    username = "username"
    password = getpass.getpass("password: ")

    obj = PersistentSSH_paramiko_screen(
        "screen_name", ipaddress, username, password)

    # see version flag explanation
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

```


## version flag

* version 1 : (default)
  * execute command without any padding.
  * suitable for writing response to application (eg: sudo password)
  * getLog will return result as is. no manipulation at all.

* version 2 :
  * execute command with padding for getLog detection.
  * NOT suitable for writing response to application.
  * getLog detects and return the actual result of the command executed.

