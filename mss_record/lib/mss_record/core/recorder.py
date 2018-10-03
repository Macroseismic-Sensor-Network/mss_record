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
import multiprocessing
import os
import re
import signal
import subprocess
import sys
import threading
import time

#import apscheduler.schedulers.background as background_scheduler
import numpy as np
import obspy
import scipy as sp
import scipy.signal

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

        # The general sampling rate of the recorder.
        self.sps = 100.

        # The interval in full seconds to write the miniseed file.
        self.write_interval = 10

        # The obspy data stream.
        self.stream = obspy.core.Stream()

        # Mutex used for I2C communication.
        self.i2c_mutex = multiprocessing.Lock()

        # Thread synchronization.
        self.stop_event = multiprocessing.Event()

        # The communication configuration of the ADCS.
        # The i2c addresses and the raspberry pins to which the RDY pins of the ADCs are connected.
        # The pin numbers are the numbers of the Broadcom SOC (GPIO.BCM mode). 
        self.adc_config = {'001': {'i2c_address': 0x4a, 'rdy_gpio': 22},
                           '002': {'i2c_address': 0x49, 'rdy_gpio': 27},
                           '003': {'i2c_address': 0x48, 'rdy_gpio': 17}}



        # Initialize the channels.
        self.channels = {}
        self.channel_stats = {}
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
            data_queue = multiprocessing.Queue()
            cur_channel = mss_record.core.channel.Channel(name = cur_name,
                                                          adc_address = cur_addr,
                                                          rdy_gpio = cur_rdy_gpio,
                                                          i2c_mutex = self.i2c_mutex,
                                                          data_queue = data_queue,
                                                          sps = 128,
                                                          gain = 8)

            if(cur_channel.check_adc()):
                self.logger.info("Found a working ADC.")
                self.logger.info("Configuring the ADC for continuous mode.")
                success = cur_channel.start_adc()
                if not success:
                    self.logger.error("ADC couldn't be configured. Ignoring channel %s.", cur_name)

                self.channels[cur_name] = cur_channel

                # Create the obspy trace stats for the channel.
                cur_stats = obspy.core.Stats()
                cur_stats.network = self.network
                cur_stats.station = self.station
                cur_stats.location = self.location
                cur_stats.sampling_rate = self.sps
                cur_stats.channel = cur_channel.name
                self.channel_stats[cur_name] = cur_stats

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


        # Wait for the next full second, than start the channels.
        now = obspy.UTCDateTime()
        delay_to_next_second = (1e6 - now.microsecond) / 1e6
        time.sleep(delay_to_next_second)
        #orig_sigint_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
        self.logger.info("self.channels. %s.", self.channels)
        self.data_request_process = multiprocessing.Process(target = data_request,
                                                       args = (self.channels, self.stop_event),
                                                       name = "data_request")
        self.data_request_process.start()
        #signal.signal(signal.SIGINT, orig_sigint_handler)

        self.pps_thread = threading.Thread(name = 'pps',
                                      target = self.pps,
                                      args = (self.collect_data,))

        self.pps_thread.start()


    def stop(self):
        ''' Stop the data collection.
        '''
        self.logger.info("Stopping.")
        self.stop_event.set()
        self.data_request_process.join()
        self.pps_thread.join()
        self.logger.info("Stopped... %s", self.stop_event.is_set())


    def collect_data(self):
        ''' Collect the data from the channels.
        '''
        timestamp = obspy.UTCDateTime()
        self.logger.info('Collecting data. timestamp: %s', timestamp)

        request_start = timestamp - 1
        request_start.microsecond = 0
        request_end = request_start + 1

        #ms_delay = np.floor(timestamp.microsecond / 1000)
        #samples_to_interpolate = int(self.sps - int(np.floor(ms_delay / (1/self.sps * 1000))))
        #self.logger.info("samples_to_interpolate: %d", samples_to_interpolate)

        # Adjust the timestamp.
        #ms_start = ms_delay - (ms_delay % ((1/self.sps) * 1000))
        #timestamp.microsecond = int(ms_start * 1000)

        for cur_name in sorted(self.channels.keys()):
            cur_channel = self.channels[cur_name]
            cur_data = cur_channel.get_data(start_time = request_start,
                                            end_time = request_end)
            self.logger.info("get_data finished.")

            if cur_data:
                self.logger.info("Collected data from channel %s.", cur_channel.name)
                self.logger.info("Data length: %d.", len(cur_data))
                if (len(cur_data) > (cur_channel.sps - 10)) and (len(cur_data) < (cur_channel.sps + 10)):
                    # Grid the data to a regular sampling interval.
                    try:
                        cur_data = np.array(cur_data)
                        self.logger.info("orig_data: %s", cur_data[:,1])
                        cur_time = cur_data[:,0] - request_start
                        self.logger.info("cur_time: %s", cur_time)
                        cur_samp_time = np.arange(0, 1, 1/cur_channel.sps)
                        self.logger.info("cur_samp_time: %s", cur_samp_time)
                        cur_data = sp.interpolate.griddata(cur_time, cur_data[:,1], cur_samp_time,
                                                           method = 'nearest')
                        self.logger.info("cur_data: %s", cur_data)

                        # Resample the data to the recorder sampling rate.
                        cur_data = sp.signal.resample(cur_data, int(self.sps))

                        # Create a obspy trace using the resampled data.
                        cur_trace = obspy.core.Trace(data = cur_data)
                        cur_trace.stats.network = self.network
                        cur_trace.stats.station = self.station
                        cur_trace.stats.location = self.location
                        cur_trace.stats.channel = cur_channel.name
                        cur_trace.stats.sampling_rate = self.sps
                        cur_trace.stats.starttime = request_start
                        self.logger.info(cur_trace)

                        # Add the trace to the recorder stream.
                        self.stream.append(cur_trace)
                    except Exception as e:
                        self.logger.exception(e)
                else:
                    self.logger.error("The retrieved number of samples doesn't match the expected value.")

        self.write_counter += 1

        if self.write_counter >= self.write_interval:
            data_dir = '/home/mss/mseeds'
            self.stream.merge()
            self.logger.info('stream: %s.', self.stream)
            for cur_trace in self.stream:
                cur_filename = cur_trace.id.replace('.','_') + '_' + cur_trace.stats.starttime.isoformat().replace(':','') + '.msd'
                cur_filepath = os.path.join(data_dir, cur_filename)
                cur_trace.write(cur_filepath,
                                format = "MSEED",
                                reclen = 512,
                                encodeing = 'STEIM2',
                                flush = True)
            self.stream = obspy.core.Stream()
            self.logger.info('stream after write: %s.', self.stream)
            self.write_counter = 0


        # TODO: Remove old data files from the data_dir.

        self.logger.info('Finished collecting data.')




    def pps(self, callback):
        now = obspy.UTCDateTime()
        delay_to_next_second = (1e6 - now.microsecond) / 1e6
        time.sleep(delay_to_next_second)

        self.write_interval = int(self.write_interval)
        self.write_counter = 0

        while not self.stop_event.is_set():
            try:
                callback()
            except Exception as e:
                self.logger.exception(e)
                # in production code you might want to have this instead of course:
                # logger.exception("Problem while executing repetitive task.")

            # skip tasks if we are behind schedule:
            #next_time += (time.time() - next_time) // delay * delay + delay
            now = obspy.UTCDateTime()
            delay_to_next_second = (1e6 - now.microsecond) / 1e6
            time.sleep(delay_to_next_second)

        self.logger.info("Leaving the pps method.")




def data_request(channels, stop_event):
    ''' Request data from the ADCs and put it into the queue.
    '''
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    # The logger.
    logger_name = __name__
    logger = logging.getLogger(logger_name)

    logger.info("Starting the ADC data request for channels: %s.", channels)
    for cur_name in sorted(channels.keys()):
        cur_channel = channels[cur_name]
        logger.info("Starting channel %s.", cur_name)
        cur_channel.run()

    while not stop_event.is_set():
        logger.info("data_request waiting.... %s", stop_event.is_set())
        time.sleep(1)

    for cur_name in sorted(channels.keys()):
        cur_channel = channels[cur_name]
        logger.info("Stopping channel %s.", cur_name)
        cur_channel.stop()
    logger.info("Leaving the data_request process.")
    sys.exit(0)
