# persistent_ssh
paramiko + screen = persistent ssh


## How To use

```

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


```



