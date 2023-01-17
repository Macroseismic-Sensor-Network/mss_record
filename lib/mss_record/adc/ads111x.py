# Copyright (c) 2016 Adafruit Industries
# Author: Tony DiCola
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

# 2014 - 2017
# author: Schools & Quakes Team
# homepage: (https://www.sparklingscience.at/en/projects/show.html?--typo3_neos_nodetypes-page[id]=857)
# The original file ADS1x15.py from the Adafruit Library has been modified to
# include the ADS1114 support. This modification has been done by the
# MacroSeismic Development team within the Sparkling Science project "Schools &
# Quakes".

# 2018
# author: Stefan Mertl
# homepage: www.mertl-research.at
# Restructuring of the file for a better separation between the ADS1115 and
# ADS1114 (www.mertl-research.at).


import time

import adafruit_bus_device.i2c_device as ada_busdev


# Register and other configuration values:
ADS111x_DEFAULT_ADDRESS        = 0x48
ADS111x_POINTER_CONVERSION     = 0x00
ADS111x_POINTER_CONFIG         = 0x01
ADS111x_POINTER_LOW_THRESHOLD  = 0x02
ADS111x_POINTER_HIGH_THRESHOLD = 0x03
ADS111x_CONFIG_OS_SINGLE       = 0x8000
ADS111x_CONFIG_MUX_OFFSET      = 12
ADS111x_CONFIG_DEFAULT         = 0x0583
# Choose a gain of 1 for reading voltages from 0 to 4.09V.
# Or pick a different gain to change the range of voltages that are read:
#  - 2/3 = +/-6.144V
#  -   1 = +/-4.096V
#  -   2 = +/-2.048V
#  -   4 = +/-1.024V
#  -   8 = +/-0.512V
#  -  16 = +/-0.256V
# See table 3 in the ADS1015/ADS1115 datasheet for more info on gain.
# Maping of gain values to config register values.
ADS111x_CONFIG_GAIN = {
    '2/3': 0x0000,
      '1': 0x0200,
      '2': 0x0400,
      '4': 0x0600,
      '8': 0x0800,
     '16': 0x0A00
}
ADS111x_CONFIG_MODE_CONTINUOUS  = 0x0000
ADS111x_CONFIG_MODE_SINGLE      = 0x0100
# Mapping of data/sample rate to config register values for ADS1115 (slower).
ADS111x_CONFIG_DR = {
    8:    0x0000,
    16:   0x0020,
    32:   0x0040,
    64:   0x0060,
    128:  0x0080,
    250:  0x00A0,
    475:  0x00C0,
    860:  0x00E0
}
ADS111x_CONFIG_COMP_WINDOW      = 0x0010
ADS111x_CONFIG_COMP_ACTIVE_HIGH = 0x0008
ADS111x_CONFIG_COMP_LATCHING    = 0x0004
ADS111x_CONFIG_COMP_QUE = {
    1: 0x0000,
    2: 0x0001,
    4: 0x0002
}
ADS111x_CONFIG_COMP_QUE_DISABLE = 0x0003


class ADS111x(object):
    """Base functionality for ADS1x15.py analog to digital converters."""

    def __init__(self, i2c_bus, address=ADS111x_DEFAULT_ADDRESS, **kwargs):

        # The ADC device on the I2C bus.
        self._device = ada_busdev.I2CDevice(i2c_bus,
                                            address)

        # The i2c write buffer.
        self._writebuf = bytearray(3)

        # The i2c read buffer.
        self._readbuf = bytearray(2)

        # The ADC default configuration.
        self._config = ADS111x_CONFIG_DEFAULT


    def _data_rate_config(self, data_rate):
        """Subclasses should override this function and return a 16-bit value
        that can be OR'ed with the config register to set the specified
        data rate.  If a value of None is specified then a default SAMPLE_RATE
        setting should be returned.  If an invalid or unsupported SAMPLE_RATE is
        provided then an exception should be thrown.
        """
        raise NotImplementedError('Subclass must implement _data_rate_config function!')

    def _conversion_value(self, low, high):
        """Subclasses should override this function that takes the low and high
        byte of a conversion result and returns a signed integer value.
        """
        raise NotImplementedError('Subclass must implement _conversion_value function!')


    def _read(self, mux, gain, data_rate, mode):
        """Perform an ADC read with the provided mux, gain, SAMPLE_RATE, and mode
        values.  Returns the signed integer result of the read.
        """
        config = ADS111x_CONFIG_OS_SINGLE  # Go out of power-down mode for conversion.
        # Specify mux value.
        config |= (mux & 0x07) << ADS111x_CONFIG_MUX_OFFSET
        # Validate the passed in gain and then set it in the config.
        if gain not in ADS111x_CONFIG_GAIN:
            raise ValueError('Gain must be one of: 2/3, 1, 2, 4, 8, 16')
        config |= ADS111x_CONFIG_GAIN[gain]
        # Set the mode (continuous or single shot).
        config |= mode
        # Get the default data rate if none is specified
        if data_rate is None:
            data_rate = self._data_rate_default()
        # Set the data rate (this is controlled by the subclass)
        config |= self._data_rate_config(data_rate)
        config |= ADS111x_CONFIG_COMP_QUE_DISABLE  # Disble comparator mode.
        # Send the config value to start the ADC conversion.
        # Explicitly break the 16-bit value down to a big endian pair of bytes.
        self._writebuf = bytearray([ADS111x_POINTER_CONFIG,
                                    (config >> 8) & 0xFF,
                                    config & 0xFF])
        self._device.write(self._writebuf)
        # Wait for the ADC sample to finish based on the sample rate plus a
        # small offset to be sure (0.1 millisecond).
        time.sleep(1.0/data_rate+0.0001)
        # Retrieve the result.
        self._device.write_then_readinto(bytearray([ADS111x_POINTER_CONVERSION]),
                                         self._readbuf,
                                         in_end = 2)
        return self._conversion_value(self.read_buf[1],
                                      self.read_buf[0])


    def configure(self, mux, gain, data_rate, mode):
        """ Configure the ADC.
        """
        cur_config = 0x00
        # Specify mux value.
        cur_config |= (mux & 0x07) << ADS111x_CONFIG_MUX_OFFSET
        # Validate the passed in gain and then set it in the config.
        if gain not in ADS111x_CONFIG_GAIN:
            raise ValueError('Gain must be one of: 2/3, 1, 2, 4, 8, 16')
        cur_config |= ADS111x_CONFIG_GAIN[gain]
        # Set the mode (continuous or single shot).
        cur_config |= mode
        # Set the data rate (this is controlled by the subclass)
        cur_config |= self._data_rate_config(data_rate)
        cur_config |= ADS111x_CONFIG_COMP_QUE_DISABLE  # Disble comparator mode.
        # Send the config value to start the ADC conversion.
        # Explicitly break the 16-bit value down to a big endian pair of bytes.
        self._writebuf = bytearray([ADS111x_POINTER_CONFIG,
                                    (cur_config >> 8) & 0xFF,
                                    cur_config & 0xFF])
        self._device.write(self._writebuf)

        self._config = self.read_config()
        # Clear the OS bit.
        self._config &= ~(0x1 << 16)
        if self._config == cur_config:
            return True
        else:
            return False



    def enable_conversion_ready_pin(self):
        """ Set the configuration activate the RDY pin.
        """
        # Set the MSB in the high and low threshold.
        high_threshold = 0x8000
        low_threshold = 0x0
        self._writebuf = bytearray([ADS111x_POINTER_HIGH_THRESHOLD,
                                    (high_threshold >> 8) & 0xFF,
                                    high_threshold & 0xFF])
        self._device.write(self._writebuf)
        self._writebuf = bytearray([ADS111x_POINTER_LOW_THRESHOLD,
                                    (low_threshold >> 8) & 0xFF,
                                    low_threshold & 0xFF])
        self._device.write(self._writebuf)

        # Set the comp_que in the config register to 00.
        cur_config = self._config
        cur_config &= ~(0x1)
        cur_config &= ~(0x1 << 1)
        self._writebuf = bytearray([ADS111x_POINTER_CONFIG,
                                    (cur_config >> 8) & 0xFF,
                                    cur_config & 0xFF])
        self._device.write(self._writebuf)
        self._config = self.read_config()
        self._config &= ~(0x1 << 16)
        if (self._config & 0x7FFF) == (cur_config & 0x7FFF):
            return True
        else:
            return False


    def stop_adc(self):
        """Stop all continuous ADC conversions (either normal or difference mode).
        """
        config = ADS111x_CONFIG_DEFAULT
        self._writebuf = bytearray([ADS111x_POINTER_CONFIG,
                                    (config >> 8) & 0xFF,
                                    config & 0xFF])
        self._device.write(self._writebuf)


    def get_last_result(self):
        """Read the last conversion result when in continuous conversion mode.
        Will return a signed integer value.
        """
        # Retrieve the conversion register value, convert to a signed int, and
        # return it.
        self._device.write_then_readinto(bytearray([ADS111x_POINTER_CONVERSION]),
                                         self._readbuf,
                                         in_end = 2)
        return self._conversion_value(self.read_buf[1],
                                      self.read_buf[0])


    def read_config(self):
        """ Read the configuration register.
        """
        self._device.write_then_readinto(bytearray([ADS111x_POINTER_CONFIG]),
                                         self._readbuf,
                                         in_end = 2)
        result = ((self._readbuf[0] & 0xFF) << 8) | (self._readbuf[1] & 0xFF)
        return result




class ADS1114(ADS111x):
    """ADS1115 16-bit analog to digital converter instance."""

    def __init__(self, *args, **kwargs):
        super(ADS1114, self).__init__(*args, **kwargs)

    def _data_rate_config(self, data_rate):
        if data_rate not in ADS111x_CONFIG_DR:
            raise ValueError('Data rate must be one of: 8, 16, 32, 64, 128, 250, 475, 860')
        return ADS111x_CONFIG_DR[data_rate]

    def _conversion_value(self, low, high):
        # Convert to 16-bit signed value.
        value = ((high & 0xFF) << 8) | (low & 0xFF)
        # Check for sign bit and turn into a negative value if set.
        if value & 0x8000 != 0:
            value -= 1 << 16
        return value

    def configure(self, gain = 1, data_rate = 128, mode = 'singleshot'):
        ''' Start the ADC in continuous differential mode.

        The ADS1114 is a single channel ADC, therefore, the differential option is fixed to 0.
        '''
        if mode == 'singleshot':
            adc_mode = ADS111x_CONFIG_MODE_SINGLE
        elif mode == 'continuous':
            adc_mode = ADS111x_CONFIG_MODE_CONTINUOUS
        else:
            raise ValueError("Mode has to be singleshot or continuous.")
        super(ADS1114, self).configure(mux = 0, gain = gain, data_rate = data_rate, mode = adc_mode)
