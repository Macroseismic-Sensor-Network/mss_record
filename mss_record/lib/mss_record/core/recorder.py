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
import sys

class Recorder:
    ''' The recorder class.

    '''
    def __init__(self, network, station, location, channels):
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

        # The channels of the recorder.
        if len(channels) > 3:
            self.logger.error("No more than 3 channels are allowed.")
            sys.exit()
