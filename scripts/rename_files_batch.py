#!/usr/local/bin/python3
# encoding: utf-8

import collections
import csv
import dataclasses
import os
import re
import sys

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
import xml.etree.ElementTree as XmlElementTree

DEBUG = False

@dataclasses.dataclass
class CsvRenameConfig:
    old_prefix: str
    new_prefix: str
    row_index: int
    expected_number_of_files: int = 1
    update_page_xml: bool = True
    
    CSV_FIELDS = ['old_prefix', 'new_prefix', 'update_page_xml', 'expected_number_of_files']
    
    def __post_init__(self):
        try:
            self.expected_number_of_files = int(self.expected_number_of_files)
        except ValueError:
            self.expected_number_of_files = 1
    
    def old_file_prefix(self):
        return os.path.basename(self.old_prefix)
    def new_file_prefix(self):
        return os.path.basename(self.new_prefix)
    
    def old_rel_dir(self, root):
        return self._rel_dir(root, self.old_prefix)
    def new_rel_dir(self, root):
        return self._rel_dir(root, self.new_prefix)
    
    def _rel_dir(self, root, prefix):
        if not os.path.isabs(os.path.dirname(prefix)):
            return os.path.dirname(prefix)
        elif not os.path.isabs(root):
            root = os.path.abspath(root)
        return os.path.relpath(os.path.dirname(prefix), start=root)
            
    
    def old_abs_dir(self, root):
        return self._abs_dir(root, self.old_prefix)
    def new_abs_dir(self, root):
        return self._abs_dir(root, self.new_prefix)
    
    def _abs_dir(self, root, prefix_path):
        if os.path.isabs(prefix_path):
            return prefix_path
        else:
            return os.path.abspath(os.path.join(root, os.path.dirname(prefix_path)))
    
@dataclasses.dataclass
class RenameConfig:
    suffix: str
    unique_tmp_suffix: str
    csv_rename_config: CsvRenameConfig
    page_xml_referenced_old_file_name: str
    update_page_xml: bool = True
    
    def old_abs_path(self, root):
        return os.path.join(self.csv_rename_config.old_abs_dir(root), self.csv_rename_config.old_file_prefix() + self.suffix)
    def new_abs_path(self, root):
        return os.path.join(self.csv_rename_config.new_abs_dir(root), self.csv_rename_config.new_file_prefix() + self.suffix)
    def temp_abs_path(self, root):
        return self.old_abs_path(root) + self.unique_tmp_suffix
    
    def old_file_name(self):
        return os.path.basename(self.csv_rename_config.old_file_prefix() + self.suffix)
    def new_file_name(self):
        return os.path.basename(self.csv_rename_config.new_file_prefix() + self.suffix)
    def temp_file_name(self):
        return os.path.basename(self.csv_rename_config.old_file_prefix() + self.unique_tmp_suffix)
    
    def old_abs_dir(self, root):
        return os.path.dirname(self.old_abs_path(root))
    def new_abs_dir(self, root):
        return os.path.dirname(self.new_abs_path(root))
    def temp_abs_dir(self, root):
        return os.path.dirname(self.temp_abs_path(root))
    
    def page_xml_referenced_new_file_name(self, renames_by_old_file_name):
        
        # Why only file names in the imageFilename attribute?
        # Because neither ocr4all, LAREX, nor calamari actually use the attribute for loading the 
        # image. So just go with the simplist solution of using just the finename.
        # research notes in `TODO.org` file under "imageFilename attribute of the PAGE XML file format" 
          
        all_renames = renames_by_old_file_name[self.page_xml_referenced_old_file_name]
        if len(all_renames) == 0:
            # the target file is not being renamed, therefore use the old file name
            return self.page_xml_referenced_old_file_name
        elif len(all_renames) == 1:
            return all_renames[0].new_file_name()
        else:
            raise ValueError(f'Ambiguous rename target for the XML PAGE referenced image file: {self.page_xml_referenced_old_file_name} all possible targets: {all_renames}')

class XMLSkipError(Exception):
    '''Exception to signal that an xml parsing error occurred and xml parsing should be skipped.'''
    def __init__(self, msg):
        super(XMLSkipError).__init__(type(self))
        self.msg = msg
    def __str__(self):
        return self.msg
    def __unicode__(self):
        return self.msg
    
def main(argv=None):

    if argv is None:
        raise ValueError("Missing argument `argv`")

    try:
        parser = ArgumentParser(description="", formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument(dest="csv_file_path", action="store", help="the CSV file to get the file names from")
        parser.add_argument("-n", "--dry-run", dest="dry_run", action="store_true", default=False, help="skip all renaming actions [default: %(default)s]")
        parser.add_argument("-v", "--verbose", dest="verbose", action="count", help="set verbosity level [default: %(default)s]")

        args = parser.parse_args()

        if args.verbose > 0:
            print("Verbose mode on")

        rename_files(args.csv_file_path, verbose = args.verbose, dry_run = args.dry_run)
        
        return 0
    except KeyboardInterrupt:
        ### handle keyboard interrupt ###
        return 0
    except Exception as e:
        if DEBUG:
            raise e
        sys.stderr.write(repr(e) + "\n")
        return 2

def rename_files(csv_file_path, verbose = False, dry_run = False):
    
    root = os.path.dirname(csv_file_path)
    if root == '':
        root = '.'
    csv_renames_by_old_prefix = {}
    csv_renames_by_new_prefix = {}

    # read CSV file
    with open(csv_file_path) as csvfile:
        reader = csv.DictReader(csvfile)#, fieldnames = CsvRenameConfig.CSV_FIELDS) # supplying the fieldnames argument means that the first row is not used as the header
        i = 0
        for row in reader:
            csv_rename_config = CsvRenameConfig(row_index=i, **row)
            if (csv_rename_config.old_prefix == '' 
                    or csv_rename_config.new_prefix == ''):
                if verbose:
                    print(f'Skipping empty row (line {i}): {row}')
                continue
            if csv_rename_config.old_prefix in csv_renames_by_old_prefix:
                raise ValueError(f'Duplicate entry in the CSV file for the same source file: first occurance: {csv_renames_by_old_prefix[csv_rename_config.old_prefix]}, second occurance: {csv_rename_config}')
            if csv_rename_config.new_prefix in csv_renames_by_new_prefix:
                raise ValueError(f'Duplicate entry in the CSV file for the same destination file: first occurance: {csv_renames_by_new_prefix[csv_rename_config.new_prefix]}, second occurance: {csv_rename_config}')
            
            csv_renames_by_old_prefix[csv_rename_config.old_prefix] = csv_rename_config
            csv_renames_by_new_prefix[csv_rename_config.new_prefix] = csv_rename_config
            i+=1

    if verbose:
        print(f"Root dir: {root}")
        print(f"Read rename config from csv file: {csv_file_path}")
        for csv_rename_config in csv_renames_by_old_prefix.values():
            print(f"{csv_rename_config}")

    # get all directory names
    old_abs_dirs = collections.defaultdict(list)
    new_abs_dirs = collections.defaultdict(list)
    for csv_rename_config in csv_renames_by_old_prefix.values():
        old_abs_dirs[csv_rename_config.old_abs_dir(root)].append(csv_rename_config)
        new_abs_dirs[csv_rename_config.new_abs_dir(root)].append(csv_rename_config)


    # cache all directory contents
    cache_abs_dirs = {}
    sim_cache_old_removed_abs_dirs = {}
    for abs_dir in set(old_abs_dirs.keys()).union(new_abs_dirs.keys()):
        cache_abs_dirs[abs_dir] = {entry.name: entry for entry in os.scandir(abs_dir)}
        sim_cache_old_removed_abs_dirs[abs_dir] = set(cache_abs_dirs[abs_dir].keys())
    
    if verbose:
        print(f"Old directories ({len(old_abs_dirs)}) in rename paths: {old_abs_dirs.keys()}")
        print(f"New directories ({len(new_abs_dirs)}) in rename paths: {new_abs_dirs.keys()}")
        print(f"Directories cache ({len(cache_abs_dirs)}): {cache_abs_dirs.keys()}")

    # get all real files to be renamed
    renames_by_old_abs_path = {}
    renames_by_old_file_name = collections.defaultdict(list)
    renames_by_new_abs_path = {}
    i = 0
    for old_abs_dir, csv_rename_configs in old_abs_dirs.items():
        for csv_rename_config in csv_rename_configs:
            files_matched = []
            for abs_dir_entry in cache_abs_dirs[old_abs_dir].values():
                if abs_dir_entry.name.startswith(csv_rename_config.old_file_prefix()):
                    unique_tmp_suffix = '.tmp-%d' % i
                    i += 1
                    suffix = abs_dir_entry.name[len(csv_rename_config.old_file_prefix()):]
                    
                    page_xml_referenced_old_file_name = None
                    update_page_xml = csv_rename_config.update_page_xml
                    if update_page_xml:
                        try:
                            page_xml_referenced_old_file_name = parse_referenced_file_name_from_page_xml(abs_dir_entry.path)

                        except XMLSkipError:
                            update_page_xml = False
                            
                        except Exception as e:
                            if verbose:
                                print(f'SKIPPING update for non-PAGE xml file `{abs_dir_entry.path}` because of error: {e}')
                            update_page_xml = False

                    rename_config = RenameConfig(
                            suffix = suffix,
                            update_page_xml = update_page_xml,
                            page_xml_referenced_old_file_name = page_xml_referenced_old_file_name,
                            unique_tmp_suffix = unique_tmp_suffix,
                            csv_rename_config = csv_rename_config)
                    
                    if rename_config.old_abs_path(root) in renames_by_old_abs_path:
                        raise ValueError(f'Duplicate rename for the same source file: first occurance: {renames_by_old_abs_path[rename_config.old_abs_path(root)]}, second occurance: {rename_config}')
                    if rename_config.new_abs_path(root) in renames_by_new_abs_path:
                        raise ValueError(f'Duplicate rename for the same destination file: first occurance: {renames_by_new_abs_path[rename_config.new_abs_path(root)]}, second occurance: {rename_config}')
                    if abs_dir_entry.name not in sim_cache_old_removed_abs_dirs[old_abs_dir]:
                        raise ValueError(f'When simulating the contents of the filesystem after the rename, the file {os.path.join(old_abs_dir, abs_dir_entry.name)} has already been renamed when trying to apply the rename {rename_config}')
                    
                    if verbose:
                        print(f'Rename config `{rename_config}` moves file \n        {rename_config.old_abs_path(root)}\n     to {rename_config.new_abs_path(root)}')
                    files_matched.append(rename_config)
                    renames_by_old_abs_path[rename_config.old_abs_path(root)] = rename_config
                    renames_by_old_file_name[rename_config.old_file_name()].append(rename_config)
                    renames_by_new_abs_path[rename_config.new_abs_path(root)] = rename_config
                    sim_cache_old_removed_abs_dirs[old_abs_dir].remove(abs_dir_entry.name)
            if csv_rename_config.expected_number_of_files != len(files_matched):
                raise ValueError(f'Unexpected number of file matches. Expected {csv_rename_config.expected_number_of_files} but found {len(files_matched)}. Config {csv_rename_config} matched on the following files: {files_matched}')
    
    sim_cache_final_abs_dirs = sim_cache_old_removed_abs_dirs
    del sim_cache_old_removed_abs_dirs
    
    # validate renames
    for rename_config in renames_by_old_abs_path.values():        
        if verbose and DEBUG:
            print(f"Validating rule 1 for: {rename_config}")
        
        # rule 1: all new files must not exist
        if rename_config.new_file_name() in sim_cache_final_abs_dirs[rename_config.new_abs_dir(root)]:
            raise ValueError(f'When simulating the contents of the filesystem after the rename, the file {os.path.join(rename_config.new_abs_dir(root), rename_config.new_file_name())} would be over-written by the rename {rename_config}')
        
        if verbose and DEBUG:
            print(f'Filesystem simulation adding file: {os.path.join(rename_config.new_abs_dir(root), rename_config.new_file_name())}')
        sim_cache_final_abs_dirs[rename_config.new_abs_dir(root)].add(rename_config.new_file_name())
    
    for rename_config in renames_by_old_abs_path.values():
        if verbose and DEBUG:
            print(f"Validating rename: {rename_config}")
        
        # rule 2: all temp files must not exist before the rename
        if rename_config.temp_file_name() in cache_abs_dirs[rename_config.temp_abs_dir(root)]:
            raise ValueError(f'File `{rename_config.temp_file_name()}` already exist, but it would be over-written by rename entry: {rename_config}')
    
        # rule 3: all temp files must not exist after the rename
        if rename_config.temp_file_name() in sim_cache_final_abs_dirs[rename_config.temp_abs_dir(root)]:
            raise ValueError(f'File `{rename_config.temp_file_name()}` already exist, but it would be over-written by rename entry: {rename_config}')
    
        # rule 4: all referenced renames must be unambiguous by file name only
        if (rename_config.page_xml_referenced_old_file_name is not None
                and rename_config.page_xml_referenced_old_file_name in renames_by_old_file_name
                and len(renames_by_old_file_name[rename_config.page_xml_referenced_old_file_name]) != 1):
            raise ValueError(f'Ambiguous referenced file: `{rename_config.page_xml_referenced_old_file_name}` could reference any of the following: {renames_by_old_file_name[rename_config.page_xml_referenced_old_file_name]}')
                        
    
    # move files: old -> tmp
    for rename_config in renames_by_old_abs_path.values():
        rename_file(rename_config.old_abs_path(root), rename_config.temp_abs_path(root), verbose = verbose, dry_run = dry_run)
        
        # update PAGE xml files
        if rename_config.update_page_xml:
            do_update_page_xml(rename_config.temp_abs_path(root), rename_config.page_xml_referenced_old_file_name, rename_config.page_xml_referenced_new_file_name(renames_by_old_file_name), verbose = verbose, dry_run = dry_run)
    
    # move files: tmp -> new
    for rename_config in renames_by_old_abs_path.values():
        rename_file(rename_config.temp_abs_path(root), rename_config.new_abs_path(root), verbose = verbose, dry_run = dry_run)


def rename_file(old_path, new_path, dry_run, verbose):
    if verbose:
        if dry_run:
            dry_run_str = '[Dry-run] ' 
        else:
            dry_run_str = ''
        print(f'{dry_run_str}Moving file \n        `{old_path}`\n      > `{new_path}`')
    if not dry_run:
        os.rename(old_path, new_path)

def parse_referenced_file_name_from_page_xml(page_xml_path):
    if page_xml_path[-4:] != '.xml':
        raise XMLSkipError(f'File `{page_xml_path}` does not have the `.xml` file extension')

    # manual api exploration:
    #import xml.etree.ElementTree as XmlElementTree ; tree = XmlElementTree.parse('/var/ocr4all/data/Thibault/processing/0276.xml') ; print(f"{tree.getroot().tag}: {tree.getroot().attrib} {list(tree.getroot())}")
    
    tree = XmlElementTree.parse(page_xml_path)
    # print(f"{tree.getroot().tag}: {tree.getroot().attrib} {list(tree.getroot())}")
    referenced_old_file_name = tree.getroot().find('{http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15}Page').get('imageFilename')

    if (referenced_old_file_name is not None 
            and os.path.dirname(referenced_old_file_name) != ''):
        raise ValueError(f'Referenced image files from PAGE XML files must be filenames only. Referenced field = {referenced_old_file_name}')

    return referenced_old_file_name

def do_update_page_xml(xml_path, referenced_old_file_name, referenced_new_file_name, dry_run, verbose):
    if verbose:
        if dry_run:
            dry_run_str = '[Dry-run] ' 
        else:
            dry_run_str = ''
        print(f'{dry_run_str}Updating PAGE xml file `{xml_path}`: updating image reference from `{referenced_old_file_name}` to `{referenced_new_file_name}`')
    if referenced_old_file_name == referenced_new_file_name:
        # no-op since the file names are the same
        return
    
    if not dry_run:    
        with open(xml_path, 'r') as file:
            file_contents = file.read()

        (modified_contents, number_of_subs_made) = re.subn(pattern=referenced_old_file_name, repl=referenced_new_file_name, string=file_contents)
        
        if number_of_subs_made != 1:
            raise ValueError(f'Expected exactly 1 match of `{referenced_old_file_name}` in the file, but found {number_of_subs_made}')
        
        with open(xml_path, 'w') as file:
            file.write(modified_contents)
           
if __name__ == "__main__":
    sys.exit(main(sys.argv))
