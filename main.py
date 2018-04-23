#!/usr/bin/env python
import sys

from reddit.reddit import Reddit


def main(config):
    # You can pass in a path to a custom config .ini file on the command line
    bot = Reddit()
    bot.run()


if __name__ == '__main__':
    main(config=sys.argv[1] if len(sys.argv) > 1 else None)
