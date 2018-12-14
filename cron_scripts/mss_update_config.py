#! /usr/bin/env python

import configparser
import json
import os
import subprocess
import urllib.request

dali_config_url = "http://www.macroseismicsensor.at/msn_config/dali_config.json"
dali_config_sig_url = dali_config_url + '.sig'
local_dali_config = 'dali_config.json'
local_dali_config_sig = local_dali_config + '.sig'
dali_ini_filename = 'dali.ini'


# Get the dali config file.
urllib.request.urlretrieve(dali_config_url, local_dali_config)
urllib.request.urlretrieve(dali_config_sig_url, local_dali_config_sig)

orig_lang = os.environ['LANGUAGE']
os.environ['LANGUAGE'] = 'en_US:en'

# Verify the signature.
try:
    verify_result = subprocess.check_output(['gpg', '--verify', local_dali_config_sig],
                                          stderr = subprocess.STDOUT)
    verify_result = verify_result.decode("utf-8")
    #print("verify_result:")
    #print(verify_result)
    # Although gpg --verify returned a success, check the output string for a
    # good signature and the expected key.
    if((verify_result.find('gpg: Good signature') != -1) and (verify_result.find('mss@mertl-research.at') != -1)):
        with open(local_dali_config) as fp:
            new_config = json.load(fp)
        # Update the dali config and restart the service.
        config = configparser.ConfigParser()
        config.read(dali_ini_filename)
        config_changed = False
        if config['dali']['host'] != str(new_config['dali_host']):
            config['dali']['host'] = str(new_config['dali_host'])
            config_changed = True
        if config['dali']['port'] != new_config['dali_port']:
            config['dali']['port'] = str(int(new_config['dali_port']))
            config_changed = True

        if config_changed:
            os.rename(dali_ini_filename, dali_ini_filename + '.old')
            with open(dali_ini_filename, 'w') as fp:
                config.write(fp)

            # TODO: Restart the dali service.

finally:
    os.remove(local_dali_config)
    os.remove(local_dali_config_sig)

os.environ['LANGUAGE'] = orig_lang
