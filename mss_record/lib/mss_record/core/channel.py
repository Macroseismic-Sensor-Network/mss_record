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
import time

import numpy as np
import obspy
import RPi.GPIO as gpio

import mss_record.adc.ads111x


class Channel:
    ''' A MSS channel.

    '''

    def __init__(self, name, adc_address, rdy_gpio, i2c_mutex, data_queue, sps = 128, gain = '1'):
        ''' Initialization of the instance.

        '''
        # The logger.
        logger_name = __name__ + "." + self.__class__.__name__
        self.logger = logging.getLogger(logger_name)

        # The name of the channel.
        self.name = name

        # The I2C address of the related ADC.
        self.adc_address = adc_address

        # The pin of the Raspberry to which the ADC RDY pin is connected to.
        # The pin number is in BCM mode.
        self.rdy_gpio = rdy_gpio

        # The sampling rate of the channel.
        self.sps = sps

        # The gain of the channel.
        self.gain = gain

        # The ADC device.
        self.adc = mss_record.adc.ads111x.ADS1114(address = self.adc_address)

        # The multiprocessing queue used to get the ADC data from a subprocess.
        self.data_queue = data_queue

        # The samples collected from the ADC.
        self.data = []

        # Mutex used for I2C communication.
        self.i2c_mutex = i2c_mutex

        # The mutex lock for the data.
        self.data_mutex = multiprocessing.Lock()

        self.drdy = False


    def check_adc(self):
        ''' Check, if the ADC is available.
        '''
        default_config = 0x8583
        try:
            self.adc.stop_adc()
            adc_config = self.adc.read_config()
        except IOError:
            self.logger.warning("No response from ADC at address %s.", hex(self.adc_address))
            return False

        if adc_config == default_config:
            self.logger.info("Got valid response from ADC at address %s.", hex(self.adc_address))
            return True
        else:
            self.logger.warning("Got an invalid response from ADC at address %s: %s", hex(self.adc_address), hex(adc_config))
            return False


    def start_adc(self):
        ''' Start the ADC in continuous mode.
        '''
        self.adc.configure(gain = self.gain,
                           data_rate = self.sps,
                           mode = 'continuous')
        # Check if the configuration has been written successfully.
        adc_config = self.adc.read_config()
        self.logger.debug("adc_config %s.", hex(adc_config))

        # Extract the data_rate information.
        adc_dr = adc_config & 0xE0
        self.logger.debug("adc_dr: %s.", hex(adc_dr))
        if (adc_dr != mss_record.adc.ads111x.ADS111x_CONFIG_DR[self.sps]):
            self.logger.error("The samplingrate has not been set.")
            return False

        # Extract the pga information.
        adc_pga = adc_config & 0xE00
        self.logger.debug("adc_pga: %s.", hex(adc_pga))
        if (adc_pga != mss_record.adc.ads111x.ADS111x_CONFIG_GAIN[self.gain]):
            self.logger.error("The pga gain has not been set.")
            return False


        # Enable the conversion ready pin.
        self.logger.debug("Enabling the conversion ready pin.")
        success = self.adc.enable_conversion_ready_pin()
        adc_config = self.adc.read_config()
        self.logger.debug("adc_config %s.", hex(adc_config))
        if not success:
            self.logger.error("Couldn't enable the conversion ready pin.")

        return True


    def run(self):
        ''' Start the data collection of the channel.
        '''
        # Configure the GPIO.
        gpio.setmode(gpio.BCM)
        gpio.setup(self.rdy_gpio, gpio.IN)
        gpio.add_event_detect(self.rdy_gpio, gpio.RISING, callback = self.drdy_callback)
        self.logger.info("Added the DRDY event handler for channel %s.", self.name)


    def stop(self):
        ''' Stop the data collection of the channel.
        '''
        gpio.remove_event_detect(self.rdy_gpio)
        gpio.cleanup(self.rdy_gpio)


    def drdy_callback(self, channel):
        ''' Handle the ADC drdy interrupt.
        '''
        cur_timestamp = obspy.UTCDateTime()
        #start = time.time()

        # TODO: Add a check against filling up the self.data list in case, that
        # the get_data method is not called for some time.
        self.i2c_mutex.acquire()
        cur_sample = self.adc.get_last_result()
        self.i2c_mutex.release()

        self.data_queue.put((cur_timestamp, cur_sample))

        #end = time.time()
        #self.logger.info('drdy dt: %f', end - start)
        #self.logger.info("cur_timestamp: %s", cur_timestamp)


    def get_data(self, start_time, end_time):
        ''' Return the data and clear the data array.
        '''
        start = time.time()
        queue_len = self.data_queue.qsize()
        cur_data = [self.data_queue.get() for x in range(queue_len)]
        end = time.time()
        dt_1 = end - start
        self.logger.debug('get_data dt_1: %f', dt_1)

        if cur_data:
            # Include some samples prior to the requested start time. This
            # gives better results when using griddata in the recorder.
            start_time = start_time - 2 * 1/self.sps
            self.logger.debug("start: %s; end: %s", start_time, end_time)
            start = time.time()
            with self.data_mutex:
                self.data.extend(cur_data)
                ret_data = [x for x in self.data if x[0] >= start_time and x[0] < end_time]
                # Keep the last sample for better nearest neighbour
                # interpolation.
                del_ind = len(ret_data) - 1
                self.data = self.data[del_ind:]
            end = time.time()
            dt_2 = end - start
            self.logger.debug('get_data dt_2: %f', dt_2)

        return ret_data




