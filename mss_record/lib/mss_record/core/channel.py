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
import threading

import RPi.GPIO as gpio

import mss_record.adc.ads111x


class Channel:
    ''' A MSS channel.

    '''

    def __init__(self, name, adc_address, rdy_gpio, sps = 128, gain = 1):
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

        # The samples collected from the ADC.
        self.data = []

        # The mutex lock for the data.
        self.data_mutex = threading.Lock()



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


    def drdy_callback(self, channel):
        ''' Handle the ADC drdy interrupt.
        '''
        cur_sample = self.adc.get_last_result()
        # TODO: Acquire a mutex from the recorder for the I2C communication
        # bus to avoid multiple i2c requests on the bus from the individual
        # channels.
        self.data_mutex.acquire()
        self.data.append(cur_sample)
        self.data_mutex.release()


    def get_data(self):
        ''' Return the data and clear the data array.
        '''
        self.data_mutex.acquire()
        cur_data = self.data.copy()
        self.data = []
        self.data_mutex.release()
        return cur_data




