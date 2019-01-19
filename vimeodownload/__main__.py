import argparse

from .downloader import download


parser = argparse.ArgumentParser()
parser.add_argument("-u", "--url", action="store", help="master json url")
parser.add_argument("-o", "--output", action="store",
                    help="output video filename without extension (mp4)",
                    default=None)

args = parser.parse_args()
download(args.url, args.output or 'output.mp4')
