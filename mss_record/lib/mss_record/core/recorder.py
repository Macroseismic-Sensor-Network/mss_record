#! /usr/bin/env python3

# -*- coding: utf-8 -*-
# LICENSE
#
# This file is part of mss_record.
#
# If you use mss_record in any program or publication, please inform and
# acknowledge its author Stefan Mertl (stefan@mertl-research.at).
#
# mss_record is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
import re
import subprocess
import time
import traceback

#import apscheduler.schedulers.background as background_scheduler
import obspy

import mss_record.core.channel

class Recorder:
    ''' The recorder class.

    '''
    def __init__(self, network, station, location):
        ''' Initialization of the instance.

        '''
        # The logger.
        logger_name = __name__ + "." + self.__class__.__name__
        self.logger = logging.getLogger(logger_name)

        # The recorder unique name consisting of network, station and location.
        # A 2 characters long string.
        self.network = network
        # A 5 characters long string.
        self.station = station
        # A 2 characters long string.
        self.location = location

        # The communication configuration of the ADCS.
        # The i2c addresses and the raspberry pins to which the RDY pins of the ADCs are connected.
        # The pin numbers are the numbers of the Broadcom SOC (GPIO.BCM mode). 
        self.adc_config = {'001': {'i2c_address': 0x4a, 'rdy_gpio': 22},
                           '002': {'i2c_address': 0x49, 'rdy_gpio': 27},
                           '003': {'i2c_address': 0x48, 'rdy_gpio': 17}}


        # Initialize the channels.
        self.channels = {}
        self.init_channels();


    def check_ntp(self):
        ''' Check for a valid NTP connection.
        '''
        self.logger.info('Checking the NTP.')
        proc = subprocess.Popen(['ntpq', '-np'], stdout=subprocess.PIPE)
        stdout_value = proc.communicate()[0].decode('utf-8')

        if stdout_value.lower().startswith("no association id's returned"):
            self.logger.error("NTP is not running. ntpd response: %s.", stdout_value)
            return []

        # Search for the header line.
        header_token = "===\n"
        header_end = stdout_value.find(header_token) + len(header_token)

        if not header_end:
            self.logger.error("NTP seems to be running, but no expected result was returned by ntpq: %s", stdout_value)
            return []

        self.logger.info("NTP is running.\n%s", stdout_value)

        payload = stdout_value[header_end:]
        working_server = []
        for cur_line in payload.splitlines():
            cur_data = re.split(' +', cur_line)
            if cur_line.startswith("*") or cur_line.startswith("+"):
                working_server.append(cur_data)

        if not working_server:
            self.logger.warning("No working servers found.")

        return working_server


    def init_channels(self):
        ''' Initialize the channels and check for existing ADCs.
        '''
        for cur_name in sorted(self.adc_config.keys()):
            cur_config = self.adc_config[cur_name]
            cur_addr = cur_config['i2c_address']
            cur_rdy_gpio = cur_config['rdy_gpio']
            self.logger.info("Checking channel %s with ADC address %s.", cur_name, hex(cur_addr))
            cur_channel = mss_record.core.channel.Channel(name = cur_name,
                                                          adc_address = cur_addr,
                                                          rdy_gpio = cur_rdy_gpio,
                                                          sps = 128,
                                                          gain = 4)

            if(cur_channel.check_adc()):
                self.logger.info("Found a working ADC.")
                self.logger.info("Configuring the ADC for continuous mode.")
                success = cur_channel.start_adc()
                if not success:
                    self.logger.error("ADC couldn't be configured. Ignoring channel %s.", cur_name)

                self.channels[cur_name] = cur_channel
                self.logger.info("Initialization of channel %s successfull.", cur_name)
            else:
                self.logger.warning("ADC not found. Ingnoring channel %s.", cur_name)



    def run(self):
        ''' Start the data collection.
        '''
        '''
        scheduler = background_scheduler.BackgroundScheduler()
        start_time = obspy.UTCDateTime()
        start_time += 2
        start_time.microsecond = 0
        self.logger.info('Job start time: %s.', start_time)
        scheduler.add_job(self.collect_data,
                          trigger = 'interval',
                          seconds = 1,
                          max_instances = 1,
                          next_run_time = start_time.datetime)
        scheduler.start()
        '''
        self.pps(self.collect_data)


    def collect_data(self):
        ''' Collect the data from the channels.
        '''
        timestamp = obspy.UTCDateTime()
        self.logger.info('Collecting data. timestamp: %s', timestamp)


    def pps(self, callback):
        now = obspy.UTCDateTime()
        delay_to_next_second = (1e6 - now.microsecond) / 1e6
        time.sleep(delay_to_next_second)
        while True:
            try:
                callback()
            except Exception:
                traceback.print_exc()
                # in production code you might want to have this instead of course:
                # logger.exception("Problem while executing repetitive task.")

            # skip tasks if we are behind schedule:
            #next_time += (time.time() - next_time) // delay * delay + delay
            now = obspy.UTCDateTime()
            delay_to_next_second = (1e6 - now.microsecond) / 1e6
            time.sleep(delay_to_next_second)





