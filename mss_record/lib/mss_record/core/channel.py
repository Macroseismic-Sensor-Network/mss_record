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

import mss_record.adc


class Channel:
    ''' A MSS channel.

    '''

    def __init__(self, adc_address, name):
        ''' Initialization of the instance.

        '''
        # The name of the channel.
        self.name = name

        # The I2C address of the related ADC.
        self.adc_address = adc_address

        # The ADC device.
        self.adc = mss_record.adc.ADS1114(address = self.adc_address)


    def check_adc(self):
        ''' Check, if the ADC is available.
        '''
        



