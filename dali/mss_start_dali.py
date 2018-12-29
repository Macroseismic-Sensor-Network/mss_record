#!/usr/bin/env python3

import argparse
import configparser
import subprocess

def load_configuration(filename):
    ''' Load the configuration from a file.
    '''
    parser = configparser.ConfigParser()
    parser.read(filename)

    config = {}
    config['host'] = parser.get('dali', 'host').strip()
    config['port'] = parser.getint('dali', 'port')
    config['mseed_dir'] = parser.get('dali', 'mseed_dir').strip()

    return config


if __name__ == '__main__':
    # Specify the configuration file using argpars.
    parser = argparse.ArgumentParser(description = 'mss_record')

    parser.add_argument('config_file', help = 'The path to the configuration file.',
                        type = str)
    args = parser.parse_args()

    # Read the INI formatted configuration file using configparser.
    config = load_configuration(args.config_file)

    # Start mseedscan2dali using the loaded configuration.
    subprocess.call(['/usr/bin/mseedscan2dali', '-s', '5', '-d', config['mseed_dir'], config['host'] + ':' + str(config['port'])])
