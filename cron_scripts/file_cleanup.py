#! /usr/bin/env python

import os
import time

# The directories to process and the corresponding time span in seconds for which to keep
# the files in the directory.
data_dir = {
        '/home/mss/mseed': 120,
        }

now = time.time()

# Process the data_dir folders.
for cur_data_dir, cur_span in data_dir.iteritems():
    for cur_file in sorted([x for x in os.listdir(cur_data_dir) if os.path.isfile(os.path.join(cur_data_dir, x))]):
        if os.stat(os.path.join(cur_data_dir, cur_file)).st_mtime <= (now - cur_span):
            os.remove(os.path.join(cur_data_dir, cur_file))


