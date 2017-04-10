#!/usr/bin/env python
# encoding: utf-8


import getopt
import os
import sys
import yaml
import zeppelincmd
from usage import Usage


help_message ="""
Usage: zdari [--config $CONFIG_PATH] COMMAND_TYPE
$CONFIG_PATH default is '~/.zdari.yml'

COMMAND TYPE LIST
%s

""" % '\n'.join(["  " + v for v in zeppelincmd.invoker.list_command_types()])


def init(config_path):
    """
    Config example:
      zeppelin_url: http://xxxx.xxxx
      #Options
      zeppelin_auth: true
      zeppelin_user: xxxxx
      zeppelin_password: xxxxx
    """
    config = yaml.load(open(config_path, "r"))
    return config


def main(argv=None):

    if argv is None:
        argv = sys.argv

    # option processing
    config_path = os.environ['HOME'] + "/.zdari.yml"
    try:
        opts, args = getopt.getopt(argv[1:], "h", ["help", "config="])
        raise_usage = len(argv) < 2
        next_argv_index = 1 if len(argv) >= 2 else 0
        for option, value in opts:
            if option in ("-h", "--help"):
                raise_usage = True
            if option in ("--config"):
                config_path = value
                remove_index = [i for (i,v) in enumerate(argv) if v == '--config']
                next_argv_index = 3 if len(argv) > 3 else 0
        config = init(config_path)
        command_type = argv[next_argv_index]

        if raise_usage or command_type not in zeppelincmd.invoker.list_command_types():
            raise Usage(help_message)

        argv = argv[next_argv_index+1:]
        command_name = argv[0] if len(argv) > 0 else ""
        if command_name not in zeppelincmd.invoker.list_commands(command_type):
            raise Usage("""Command type: %s\nSupport Commands\n%s
             """ % (command_type,
                    '\n'.join(["  " + v for v in zeppelincmd.invoker.list_commands(command_type)])))

        argv = argv[1:]
        zeppelincmd.invoker.execute(command_type, command_name, config, argv)

    except Usage, err:
        print >> sys.stderr, str(err.msg)
        return 2


if __name__ == "__main__":
    sys.exit(main())