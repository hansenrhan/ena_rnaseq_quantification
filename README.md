# ENA (European Nucleotide Archive) RNAseq Quantification Pipeline
Given a BioProject ID, download and quantify all FASTQ files using Salmon for analysis. 

### Background
I created this pipeline so that I could easily download and quantify transcriptomic data from the ENA. One of the annoying things I ran into when doing this manually was storage where for a given project you could have to download > 200Gb of files. To deal with this, I set up the logic so that it would download a pair of files at a time, process them, then delete the files before moving on, thereby reducing the overall amount of storage needed at any given time.

### Requirements & Setup
***Set up a conda environment and install dependencies***
```
conda config --add channels conda-forge --add channels bioconda
conda create -n salmon python=3.10 salmon
conda activate salmon
pip install requests pandas tqdm
```

***Download human transcriptome reference file***
```
wget ftp://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_39/gencode.v39.transcripts.fa.gz
```

***Build index with salmon***
```
salmon index -t gencode.v39.transcripts.fa.gz --gencode -i gencode_index
```

### Usage

Given some BioProject IDs (ie: PRJNA494155, PRJNA494156, PRJNA494157), run the following python script while in the conda environment. Can handle any number of project IDs to queue up. 

```
run_pipeline.py PRJNA494155 PRJNA494156 PRJNA494157
```

