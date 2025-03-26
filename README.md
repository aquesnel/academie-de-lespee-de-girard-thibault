"Academie de l'espee" by Girard Thibault
========================================

"Academie de l'espee" by Girard Thibault is a fencing manual written in French in 1628. This project is a transcription of the book into text so that it is more accessible than the physical or scanned copies of the book.

Sources
-------

* KU Leuven - Libraries Special Collections, high resolution scans of the book: https://kuleuven.limo.libis.be/discovery/fulldisplay?docid=alma9983150410101488&context=L&vid=32KUL_KUL:KULeuven&search_scope=All_Content&tab=all_content_tab&lang=en


Performing the OCR
------------------

### Prerequisites

* [Docker](https://www.docker.com/) installed
* [ScanTailor](https://scantailor.org/) installed


### Starting the docker containers

#### [OCR4all](https://www.ocr4all.org/)

OCR4all is OCR software which allows for training an OCR model based on a specific book and the font in it.

```
docker compose -f ./docker/docker-compose-ocr4all.yaml -p thibault up -d
```


#### [Optional] [Kraken](https://kraken.re/main/ketos.html)

Kraken is the OCR software under the hood of OCR4all, while it is available in the OCR4all docker container, it is not configured for using CUDA GPU accelerated model training. This kraken container is configured to use available GPUs for model training.

This container is only needed if the model training in the ocr4all container is too slow or if custom training configurations are required.

```
docker compose -f ./docker/docker-compose-kraken-cuda.yaml -p thibault up -d
```


### Downloading the source images from KU Leuven

* Start the ocr4all container
* From inside the ocr4all container, run:

```
python3 /var/ocr4all/Thibault-scripts/download-thibault-kuleuven.py -v -o /var/ocr4all/data/Thibault/KU-Leuven-raw/ /var/ocr4all/data/Thibault/KU-Leuven-images.csv
```


### Pre-process the images with ScanTailor

The goal is to create images that are easier for the OCR to process. This means that the images are cropped to the text, rotated so the text is correctly oriented, de-scewed, grey-scaled, and reduced file size.

This is a manual process and there is a copy of the manually pre-processed KU Leuven images (and converted to PNG) in the `ocr4all-data/input` directory.


### Convert the images to PNG

Convert the TIFF images output from ScanTailor to PNG

**Note:** the `convert_to_png.py` script uses the same OpenCV library that OCR4all uses to convert files to PNG

* Start the ocr4all container
* From inside the ocr4all container, run:

```
pip3 install pypng
find /var/ocr4all/data/Thibault/ScanTailor-out -type f -name "*.tif" | xargs -I {} python3 /var/ocr4all/Thibault-scripts/convert_to_png.py -v {}
mv /var/ocr4all/data/Thibault/ScanTailor-out/*.png /var/ocr4all/data/Thibault/input
```


### OCR the images with OCR4all

**SKIP** this step if using the provided PAGE xml files in the `ocr4all-data/processing` directory. If you want to add to the ground truth in the PAGE xml files, then the `Preprocessing` and `Noise Removal` steps will need to be run since those images are not committed in this repository.

* start the ocr4all container
* go to the Overview page http://localhost:1476/ocr4all/
* load the project `Thibault`
* go to the Process Flow page http://localhost:1476/ocr4all/ProcessFlow
* run the following steps on all of the images:
  * Preprocessing
  * Noise Removal
  * Segmentation (Kraken)
* wait for the processing to finish
* open the LAREX review tool http://localhost:1476/ocr4all/SegmentationLarex
* manually review that the paragraph segmentation on all pages is correct, and correct as needed
* go to the Line Segmentation page http://localhost:1476/ocr4all/LineSegmentation
* run the line segmentation on all pages with the following arguments:
  * `Number of parallel threads for program execution` = 1
    * this is because there is a race condition in the line segmentation code that can cause a deadlock
* wait for the processing to finish
* open the LAREX review tool http://localhost:1476/ocr4all/SegmentationLarex
* manually review that the line segmentation on all pages is correct, and correct as needed
* go to the Recognition page http://localhost:1476/ocr4all/Recognition
* run the recognition on all pages with the following arguments:
  * `Line recognition models` = all of the `Thibault/historial_french_thibault/#` models
* wait for the processing to finish
* open the LAREX review tool http://localhost:1476/ocr4all/SegmentationLarex
* manually review that the recognition on all pages is correct, and correct as needed


### Segmentation training

* start the Kraken container
* Create the manifest file:

```
find /var/kraken/data/processing -type f -name "*.xml" > /var/kraken/data/manifest.txt
```

* run the training:

```
ketos segtrain -f page -t /var/kraken/data/manifest.txt -N 100 -q early --min-epochs 30 --resize both --schedule cosine --load-hyper-parameters --baseline -i /usr/local/lib/python3.7/dist-packages/kraken/blla.mlmodel -o /var/kraken/models/custom/blla-thibault.mlmodel 
```


#### References

* https://kraken.re/main/ketos.html
* https://digitalorientalist.com/2023/11/03/11400/


### File fixup

#### fixup the PAGE xml imageFilename attribute remove absolute path

* start the ocr4all container
* run the following commands

```
cd /var/ocr4all/data/Thibault
mkdir fixed 
cd processing ; find . -name '*.xml' | xargs -I{} sed 's#<Page imageFilename="\(/var.*/\)*\([^/]*\)"#<Page imageFilename="\2"#g; w ../fixed/{}' {} > /dev/null ; cd ..
cd fixed ; find . -name '*.xml' | xargs -I{} diff ../processing/{} {}  | less ; cd ..
```


#### fixup the PAGE xml imageFilename attribute remove .bin suffix

* start the ocr4all container
* run the following commands

```
cd /var/ocr4all/data/Thibault
mkdir fixed 
cd processing ; find . -name '*.xml' | xargs -I{} sed 's#<Page imageFilename="\(.*\)\.bin\(.*\)"#<Page imageFilename="\1\2"#g; w ../fixed/{}' {} > /dev/null ; cd ..
cd fixed ; find . -name '*.xml' | xargs -I{} diff ../processing/{} {} | less ; cd ..
```

#### reduce PNG file size

* start the ocr4all container
* run the following commands

```
pip3 install pypng
find /var/ocr4all/data/Thibault/ScanTailor-out -type f -name "*.tif" | xargs -I {} python3 /var/ocr4all/Thibault-scripts/convert_to_png.py  --verbose --scaling_factor 0.20 --grey_scale --bit_depth 2 --compression_level 9 /var/ocr4all/data/Thibault/input/{}
mkdir /var/ocr4all/data/Thibault/reduced-size
mv /var/ocr4all/data/Thibault/ScanTailor-out/*.png /var/ocr4all/data/Thibault/reduced-size
```


#### rename files

This command is useful for batch renaming files in the case that ocr4all renames files, or to output files with a clearer naming convention.

* start the ocr4all container
* run the following commands

```
python3 /var/ocr4all/Thibault-scripts/rename_files_batch.py --dry-run --verbose /var/ocr4all/data/Thibault/Thibault-rename-ocr4all-to-KULeuven-numbering.csv
```
