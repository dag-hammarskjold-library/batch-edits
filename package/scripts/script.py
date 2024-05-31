
import sys
from argparse import ArgumentParser
from package.module import Class # rename package, module and class

def get_args():
    parser = ArgumentParser()
    parser.add_argument('--arg', help='')

    return parser.parse_args()

def run():
    args = get_args()
    c = Class()
    c.hello_world()

    return