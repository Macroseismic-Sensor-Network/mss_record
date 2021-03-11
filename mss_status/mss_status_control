#! /usr/bin/env python3

import logging
import logging.handlers
import os
import re
import subprocess
import threading
import time

import obspy
import RPi.GPIO as gpio

led1_green = 10
led1_red = 24
led2_green = 11
led2_red = 9
led3_green = 7
led3_red = 8
led4_green = 6
led4_red = 5


def get_logger_handler(filename):
    ''' Create a logging format handler.
    '''
    handler = logging.handlers.RotatingFileHandler(filename,
                                                   maxBytes = 1000000,
                                                   backupCount = 10)
    formatter = logging.Formatter("#LOG# - %(asctime)s - %(process)d - %(threadName)s - %(levelname)s - %(name)s: %(message)s")
    handler.setFormatter(formatter)

    return handler


def check_ntp():
    ''' Check for a valid NTP connection.
    '''
    logger.info('Checking the NTP.')
    proc = subprocess.Popen(['ntpq', '-np'], stdout=subprocess.PIPE)
    stdout_value = proc.communicate()[0].decode('utf-8')
    working_server = []
    ntp_is_working = False

    if stdout_value.lower().startswith("no association id's returned"):
        logger.error("NTP is not running. ntpd response: %s.", stdout_value)
    else:
        # Search for the header line.
        header_token = "===\n"
        header_end = stdout_value.find(header_token) + len(header_token)

        if not header_end:
            logger.error("NTP seems to be running, but no expected result was returned by ntpq: %s", stdout_value)
            return []

        logger.info("NTP is running.\n%s", stdout_value)

        payload = stdout_value[header_end:]
        for cur_line in payload.splitlines():
            cur_data = re.split(' +', cur_line)
            if cur_line.startswith("*") or cur_line.startswith("+"):
                if (int(cur_data[4]) <= (int(cur_data[5]) * 3)) and (int(cur_data[6]) > 0):
                    working_server.append(cur_data)

    if not working_server:
        logger.warning("No working servers found.")
    else:
        ntp_is_working = True

    return ntp_is_working


def task_timer(callback, stop_event, interval = 10):
    ''' A timer executing a task at regular intervals.
    '''
    logger.info('Starting the timer.')
    interval = int(interval)
    now = obspy.UTCDateTime()
    delay_to_next_interval = interval - (now.timestamp % interval)
    logger.info('Sleeping for %f seconds.', delay_to_next_interval)
    time.sleep(delay_to_next_interval)

    while not stop_event.is_set():
        try:
            logger.info('task_timer: Executing callback.')
            callback()
        except Exception as e:
            logger.exception(e)

        now = obspy.UTCDateTime()
        delay_to_next_interval = interval - (now.timestamp % interval)
        logger.info('task_timer: Sleeping for %f seconds.',
                    delay_to_next_interval)
        time.sleep(delay_to_next_interval)

    logger.info("Leaving the task_timer method.")


def check_status():
    ''' Check the status of the MSS.
    '''
    gpio.output(led1_green, gpio.LOW)
    gpio.output(led1_red, gpio.LOW)
    gpio.output(led2_green, gpio.LOW)
    gpio.output(led2_red, gpio.LOW)
    gpio.output(led4_green, gpio.LOW)
    gpio.output(led4_red, gpio.LOW)

    time.sleep(0.5)

    # Check the NTP connection.
    if check_ntp():
        gpio.output(led1_green, gpio.HIGH)
        gpio.output(led1_red, gpio.LOW)
    else:
        gpio.output(led1_green, gpio.LOW)
        gpio.output(led1_red, gpio.HIGH)

    # Check the datalink connection.


    # Check the miniseed data files.


if __name__ == '__main__':
    # Setup the status LED.
    gpio.setmode(gpio.BCM)
    gpio.setup(led1_green, gpio.OUT)
    gpio.setup(led1_red, gpio.OUT)
    gpio.setup(led2_green, gpio.OUT)
    gpio.setup(led2_red, gpio.OUT)
    gpio.setup(led4_green, gpio.OUT)
    gpio.setup(led4_red, gpio.OUT)
    gpio.output(led1_green, gpio.LOW)
    gpio.output(led1_red, gpio.LOW)
    gpio.output(led2_green, gpio.LOW)
    gpio.output(led2_red, gpio.LOW)
    gpio.output(led4_green, gpio.LOW)
    gpio.output(led4_red, gpio.LOW)

    # Setup the threading events.
    stop_event = threading.Event()

    # Configure the logger
    log_dir = '/home/mss/log'
    log_filename = os.path.join('mss_status_control.log')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    logger = logging.getLogger('mss_status_control')
    logger.setLevel('INFO')
    logger.addHandler(get_logger_handler(log_filename))

    logger.info('Starting status control.')
    status_thread = threading.Thread(name = 'process_timer',
                                     target = task_timer,
                                     args = (check_status, stop_event))
    status_thread.start()
    status_thread.join()
