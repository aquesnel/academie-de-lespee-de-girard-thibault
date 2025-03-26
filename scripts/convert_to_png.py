#!python3
# encoding: utf-8

import os
import sys
import cv2 as cv
import numpy as np
import png

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

DEBUG = False

def convert_file(img_file_path, scaling_factor, grey_scale, bit_depth, compression_level, verbose = False, dry_run = False):
    img_file_prefix, img_file_suffix = img_file_path.rsplit('.', 1)
    img_final_png = f'{img_file_prefix}.png'
    
    if verbose:
        if dry_run:
            dry_run_str = '[Dry-run] ' 
        else:
            dry_run_str = ''
        print(f'Conversion parameters:\n\tscaling factor = {scaling_factor}\n\tgrey_scale = {grey_scale}\n\tbit_depth = {bit_depth}\n\tcompression_level = {compression_level}')
        print(f'{dry_run_str}Converting file:\n        `{img_file_path}`\n     to `{img_final_png}`')

    write_args = [
    #     cv.IMWRITE_PNG_STRATEGY, cv.IMWRITE_PNG_STRATEGY_HUFFMAN_ONLY, 
        cv.IMWRITE_PNG_COMPRESSION, compression_level]

    img = cv.imread(img_file_path)
    if grey_scale:
        img = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
        img = img.astype(np.uint8)
        # Reduce bit-depth by scaling the value to the new range, assumes that values are 8-bit
        img = np.floor(img / 256 * 2**bit_depth)
        img = img.astype(np.uint8)
    img = cv.resize(img, None, fx=scaling_factor, fy=scaling_factor, interpolation=cv.INTER_AREA)
    
    if not dry_run:
        # opencv dosen't support writing as bit depth = 2 (which is best for the thibault grey scale images).
        # Therefore we use pypng to have full control over the serialization arguments
        if grey_scale:
            with open(img_final_png, 'wb') as f:
                png_writer = png.Writer(
                    width = img.shape[1], 
                    height = img.shape[0], 
                    bitdepth = bit_depth,
                    greyscale = True,
                    compression = compression_level)
                png_writer.write(f, img)
        else:
            cv.imwrite(img_final_png, img, write_args)

def main(argv=None):

    if argv is None:
        raise ValueError("Missing argument `argv`")

    try:
        parser = ArgumentParser(description="", formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument(dest="img_file_path", action="store", help="the image file to convert to PNG")
        parser.add_argument("-s", "--scaling_factor", dest="scaling_factor", action="store", default='1', help="Scale the image by the given factor [default: %(default)s]")
        parser.add_argument("-g", "--grey_scale", dest="grey_scale", action="store_true", default=False, help="Output the image as grey scale [default: %(default)s]")
        parser.add_argument("-b", "--bit_depth", dest="bit_depth", action="store", default='8', help="Output the image with the given bit depth [default: %(default)s]")
        parser.add_argument("-c", "--compression_level", dest="compression_level", action="store", default='-1', help="Output the image with the given zlib compression level [-1 .. 9]. '-1' means the zlib default compression level. [default: %(default)s]")
        parser.add_argument("-n", "--dry-run", dest="dry_run", action="store_true", default=False, help="skip all renaming actions [default: %(default)s]")
        parser.add_argument("-v", "--verbose", dest="verbose", action="count", help="set verbosity level [default: %(default)s]")

        args = parser.parse_args()

        if args.verbose > 0:
            print("Verbose mode on")

        convert_file(args.img_file_path, 
                     float(args.scaling_factor), 
                     args.grey_scale, 
                     int(args.bit_depth), 
                     int(args.compression_level),
                     verbose = args.verbose, 
                     dry_run = args.dry_run)
        
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
