#!/usr/bin/env python
from reddit.reddit import Reddit


def main():
    # You can also pass in a path to a custom config .ini file
    bot = Reddit()
    bot.run()


if __name__ == '__main__':
    main()
