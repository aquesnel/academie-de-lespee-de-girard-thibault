#!python3
# encoding: utf-8

import collections
import csv
import dataclasses
import os
import re
import sys
import urllib.request

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

DEBUG = False
KU_LEUVEN_THIBAULT_BASE_IMAGE_INDEX = 6805149
KU_LEUVEN_THIBAULT_IMAGE_WIDTH_DEFAULT = 7236
KU_LEUVEN_THIBAULT_IMAGE_WIDTH_OVERRIDE_BY_IMAGE_INDEX = {
    1:    6773,
    32:   9917,
    67:  10037,
    76:  10182,
    89:  10182,
    104: 10238,
    113: 10254,
    128: 10238,
    137: 10238,
    152: 10288,
    159: 10306,
    168: 10306,
    175: 10306,
    184: 10306,
    193: 10306,
    202: 10306,
    211: 10306,
    222: 10306,
    231: 10306,
    240: 10306,
    249: 10306,
    258: 10306,
    267: 10306,
    274: 10306,
    281: 10306,
    288: 10306,
    295: 10306,
    302: 10306,
    311: 10306,
    318: 10306,
    325: 10306,
    334: 10306,
    343: 10306,
    352: 10321,
    355: 10306,
    360: 10306,
    367: 10306,
    376: 10306,
    385: 10306,
    394: 10306,
    401: 10306,
    410: 10306,
    417: 10306,
    426: 10306,
    433: 10306,
    442: 10306,
    447:  6893,
    448:  5935,
    449:  1184,
    450:  5745,
    451:  1184,
}


@dataclasses.dataclass
class CsvDownloadConfig:
    image_index: int
    row_index: int

    def __post_init__(self):
        if not isinstance(self.image_index, int):
            self.image_index = int(self.image_index)

def download_files(csv_file_path, output_prefix, verbose = False, dry_run = False):
    downloads = []

    # read CSV file
    with open(csv_file_path) as csvfile:
        reader = csv.DictReader(csvfile) # supplying the fieldnames argument means that the first row is not used as the header
        i = 0
        for row in reader:
            csv_download_config = CsvDownloadConfig(row_index=i, **row)
            if csv_download_config.image_index == '':
                if verbose:
                    print(f'Skipping empty row (line {i}): {row}')
                continue

            downloads.append(csv_download_config)
            i+=1
    
    failed_downloads = []
    make_dir(output_prefix, verbose = verbose, dry_run = dry_run)
    for csv_download_config in downloads:
        
        final_image_index = KU_LEUVEN_THIBAULT_BASE_IMAGE_INDEX + csv_download_config.image_index
        image_width = get_image_width(csv_download_config.image_index)
        url = f'https://lib.is/iiif/2/FL{final_image_index}/full/{image_width},/0/default.jpg'
        
        file_path = os.path.abspath(f'{output_prefix}{csv_download_config.image_index:04}.jpg')
        try:
            download_file(url, file_path, verbose = verbose, dry_run = dry_run)
        except Exception as e:
            failed_downloads.append( (csv_download_config, url, file_path, str(e)) )
    
    if len(failed_downloads) > 0:
        raise ValueError(f'Some downloads failed. {failed_downloads}')

def get_image_width(image_index):
    if image_index in KU_LEUVEN_THIBAULT_IMAGE_WIDTH_OVERRIDE_BY_IMAGE_INDEX:
        return KU_LEUVEN_THIBAULT_IMAGE_WIDTH_OVERRIDE_BY_IMAGE_INDEX[image_index]
    else:
        return KU_LEUVEN_THIBAULT_IMAGE_WIDTH_DEFAULT

def make_dir(output_prefix, verbose = False, dry_run = False):
    
    if os.path.dirname(output_prefix) == '':
        abs_dir = os.path.abspath('.')
    elif os.path.basename(output_prefix) == '':
        abs_dir = os.path.abspath(output_prefix)
    else:
        abs_dir = os.path.dirname(os.path.abspath(output_prefix))
            
    if verbose:
        if dry_run:
            dry_run_str = '[Dry-run] ' 
        else:
            dry_run_str = ''
        print(f'{dry_run_str}Creating directory: `{abs_dir}`')
    if not dry_run:        
        os.makedirs(abs_dir, exist_ok=True)

def download_file(url, file_path, verbose = False, dry_run = False):
    if verbose:
        if dry_run:
            dry_run_str = '[Dry-run] ' 
        else:
            dry_run_str = ''
        print(f'{dry_run_str}Downloading file \n        `{url}`\n     to `{file_path}`')
    if not dry_run:
        urllib.request.urlretrieve(url, file_path)
        

def main(argv=None):

    if argv is None:
        raise ValueError("Missing argument `argv`")

    try:
        parser = ArgumentParser(description="", formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument(dest="csv_file_path", action="store", help="the CSV file to get the file names from")
        parser.add_argument("-o", "--output-prefix", dest="output_prefix", action="store", default='.', help="The destination directory and file name prefix for the downloaded files [default: %(default)s]")
        parser.add_argument("-n", "--dry-run", dest="dry_run", action="store_true", default=False, help="skip all renaming actions [default: %(default)s]")
        parser.add_argument("-v", "--verbose", dest="verbose", action="count", help="set verbosity level [default: %(default)s]")

        args = parser.parse_args()

        if args.verbose > 0:
            print("Verbose mode on")

        download_files(args.csv_file_path, args.output_prefix, verbose = args.verbose, dry_run = args.dry_run)
        
        return 0
    except KeyboardInterrupt:
        ### handle keyboard interrupt ###
        return 0
    except Exception as e:
        if DEBUG:
            raise e
        sys.stderr.write(repr(e) + "\n")
        return 2

if __name__ == "__main__":
    sys.exit(main(sys.argv))
