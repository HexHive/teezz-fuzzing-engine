#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import re


def main():
    if len(sys.argv) != 2:
        print('Usage: ' + sys.argv[0] + ' <crashes_directory_path>')
        exit(1)

    processed_crashes = set()

    # First argument is a path to a directory where the crash logs are
    crashes_directory_path = sys.argv[1]

    # Filtered crashes will be saved at <crashes_directory_path>/filtered/
    filter_crashes_path = os.path.join(crashes_directory_path, 'filtered')


    def process_file(path, shouldSave=True):
        if os.path.isdir(path) and len(path.split('_')) == 3:
            # Process this crash sequence directory
            for f in sorted(os.listdir(path), reverse=True):
                path2 = os.path.join(path, f)
                if os.path.isfile(path2) and path2.endswith('hisi_teelog'):
                    print(path2)
                    process_file(path2, shouldSave)
                    break
        if os.path.isfile(path) and path.endswith('hisi_teelog'):
            # Process this file
            with open(path) as f:
                content = f.read().replace('\x00', '')
                m = re.search(r'=+\s*The PC which result in abort is .*=+\s*Task Crash\s*=+', content, re.MULTILINE | re.DOTALL)
                if m:
                    data = m.group(0)
                    if data not in processed_crashes:
                        seed_path = path.replace('hisi_teelog', 'seed_ctx.pickle')
                        mutation_path = path.replace('hisi_teelog', 'mutation_ctx.pickle')
                        processed_crashes.add(data)
                        # Copy the file to `filtered` directory if `shouldSave==True`
                        if shouldSave:
                            with open(os.path.join(filter_crashes_path, os.path.basename(path)), 'w') as f2:
                                f2.write(content)
                            if os.path.exists(seed_path):
                                with open(seed_path) as sf:
                                    with open(os.path.join(filter_crashes_path, os.path.basename(seed_path)), 'w') as sf2:
                                        sf2.write(sf.read())
                            if os.path.exists(mutation_path):
                                with open(mutation_path) as mf:
                                    with open(os.path.join(filter_crashes_path, os.path.basename(mutation_path)), 'w') as mf2:
                                        mf2.write(mf.read())


    if not os.path.exists(filter_crashes_path):
        os.mkdir(filter_crashes_path)
    else:
        # Load existing crashes
        for f in sorted(os.listdir(filter_crashes_path), reverse=True):
            process_file(os.path.join(filter_crashes_path, f), False)

    # Process files in <crashes_directory_path>
    for f in sorted(os.listdir(crashes_directory_path), reverse=True):
        process_file(os.path.join(crashes_directory_path, f))


if __name__ == "__main__":
    main()
