#! /usr/bin/env python3

import configparser
import json
import os
import random
import subprocess
import time
import urllib.request

serial_filepath = '/home/mss/config/mss_serial'
update_path = '/home/mss/update'
update_config_url = "http://www.macroseismicsensor.at/msn_config/mssrecord_update.json"
update_config_sig_url = update_config_url + '.sig'
local_update_config = os.path.join(update_path, 'mssrecord_update.json')
local_update_config_sig = os.path.join(update_path, local_update_config + '.sig')

def get_serial():
    '''
    '''
    serial = ''
    with open(serial_filepath, 'r') as fid:
        serial = fid.readline().strip()

    return serial

def update_mssrecord(serial):
    if 'LANGUAGE' in os.environ:
        orig_lang = os.environ['LANGUAGE']
    else:
        orig_lang = None
    os.environ['LANGUAGE'] = 'en_US:en'

    try:
        # Verify the signature.
        verify_result = subprocess.check_output(['gpg', '--verify', local_update_config_sig],
                                                stderr = subprocess.STDOUT)
        verify_result = verify_result.decode("utf-8")
        #print("verify_result:")
        #print(verify_result)
        # Although gpg --verify returned a success, check the output string for a
        # good signature and the expected key.
        if((verify_result.find('gpg: Good signature') != -1) and (verify_result.find('mss@mertl-research.at') != -1)):
            with open(local_update_config) as fp:
                update_config = json.load(fp)

            update_software = False
            if isinstance(update_config['recorders'], str):
                if update_config['recorders'].lower() == 'all':
                    update_software = True
            elif serial in update_config['recorders']:
                update_software = True

            if update_software:
                for cur_filename in update_config['filename']:
                    print("Downloading the deb package %s." % cur_filename)
                    try:
                        deb_url = "http://www.macroseismicsensor.at/msn_config/" + cur_filename
                        deb_sig_url = "http://www.macroseismicsensor.at/msn_config/" + cur_filename + '.sig'
                        local_deb = os.path.join(update_path, cur_filename)
                        local_deb_sig = os.path.join(update_path, cur_filename + '.sig')
                        urllib.request.urlretrieve(deb_url, local_deb)
                        urllib.request.urlretrieve(deb_sig_url, local_deb_sig)
                        deb_file_downloaded = True

                    except urllib.error.URLError:
                        deb_file_downloaded = False


                    if deb_file_downloaded:
                        # Verify the signature.
                        verify_result = subprocess.check_output(['gpg', '--verify', local_deb_sig],
                                                                stderr = subprocess.STDOUT)
                        verify_result = verify_result.decode("utf-8")
                        if((verify_result.find('gpg: Good signature') != -1) and (verify_result.find('mss@mertl-research.at') != -1)):
                            # Install the software.
                            print("Updating the software.")
                            os.chdir(update_path)
                            subprocess.check_call(['sudo', 'apt', 'install', './' + cur_filename])
                            print("Installed the software.")
                            # Restart the dali service.
                            subprocess.check_call(['sudo', 'systemctl', 'restart', 'mss_record.service'])
                            print("Restarted the service.")


    finally:
        os.remove(local_update_config)
        os.remove(local_update_config_sig)

    if orig_lang:
        os.environ['LANGUAGE'] = orig_lang

if __name__ == '__main__':
    # Add some jitter to the start of the execution to avoid that all mss try
    # to access the update files at the same time.
    jitter = random.randint(0, 60)
    time.sleep(jitter)

    # Get the dali config file.
    try:
        urllib.request.urlretrieve(update_config_url, local_update_config)
        urllib.request.urlretrieve(update_config_sig_url, local_update_config_sig)
        dali_files_downloaded = True
    except urllib.error.URLError:
        dali_files_downloaded = False

    if dali_files_downloaded:
        serial = get_serial()
        update_mssrecord(serial)

