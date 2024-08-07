import requests
import pandas as pd
import json
import subprocess
import os
import urllib.request
from tqdm import tqdm

def list_subfolders(directory):
    subfolders = [f.path for f in os.scandir(directory) if f.is_dir()]
    return subfolders

def delete_file(file_path):
    try:
        # Check if file exists
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"File {file_path} has been deleted.")
        else:
            print(f"File {file_path} does not exist.")
    except Exception as e:
        print(f"Error occurred while trying to delete the file: {e}")

def download_ftp_file(ftp_url, local_directory):
    # Parse the filename from the FTP URL
    filename = os.path.basename(ftp_url)
    
    # Ensure the local directory exists
    if not os.path.exists(local_directory):
        os.makedirs(local_directory) 
    
    # Define the local file path
    local_file_path = os.path.join(local_directory, filename)
    
    # Check if the file already exists
    if os.path.exists(local_file_path):
        print(f"File {local_file_path} already exists. Skipping download.")
    else:
        # Download the file
        urllib.request.urlretrieve(ftp_url, local_file_path)

def get_project_samples_data(bio_project_id):
    try:
        r = requests.get("https://www.ebi.ac.uk/ena/portal/api/filereport?result=read_run&accession={bio_project_id}&limit=1000&format=json&fields=study_accession,secondary_study_accession,sample_accession,secondary_sample_accession,experiment_accession,run_accession,submission_accession,tax_id,scientific_name,instrument_platform,instrument_model,library_name,nominal_length,library_layout,library_strategy,library_source,library_selection,read_count,base_count,center_name,first_public,last_updated,experiment_title,study_title,study_alias,experiment_alias,run_alias,fastq_bytes,fastq_md5,fastq_ftp,fastq_aspera,fastq_galaxy,submitted_bytes,submitted_md5,submitted_ftp,submitted_aspera,submitted_galaxy,submitted_format,sra_bytes,sra_md5,sra_ftp,sra_aspera,sra_galaxy,sample_alias,broker_name,sample_title,nominal_sdev,first_created,bam_ftp,bam_bytes,bam_md5".format(bio_project_id = bio_project_id))
        response_dict = json.loads(r.text)
        return response_dict
    except Exception as e:
        print("Error fetching project sample data:", e)
        raise RuntimeError()

def download_and_quantify_bioproject_fastqs(project_id):
    project_data = get_project_samples_data(project_id)
    
    # download FASTQ files
    local_directory = './downloaded_files'

    for sample in tqdm(project_data):
        file_path_1 = None
        file_path_2 = None

        sample_name = sample['run_accession']

        # Check if the sample has already been quantified
        output_path = "./" + project_id + "/" + sample_name
        file_exists = os.path.exists(output_path + "/quant.sf")
        if file_exists:
            print("Sample already processed, skipping")
            continue

        # Download FASTQs for a sample
        ftp_address = sample['fastq_ftp']
        files = ftp_address.split(";")

        try:
            for file in files:
                if "ftp://" not in file:
                    file = 'ftp://' + file
                
                download_ftp_file(file, local_directory)
        except Exception as e:
            print("Error downloading files, skipping sample:", sample_name)
            print("Error:", e)
            continue

        if len(files) == 1:
            # handle single paired reads
            file_path_1 = local_directory + "/" + os.path.basename(files[0])

            command = [
                "salmon", "quant", 
                "-i", "gencode_index", 
                "-l", "A", 
                "-r", file_path_1, 
                "-o", output_path
            ]
    
        elif len(files) == 2:

            # After downloading them, quantify them with Salmon
            file_path_1 = local_directory + "/" + os.path.basename(files[0])
            file_path_2 = local_directory + "/" + os.path.basename(files[1])


            command = [
                "salmon", "quant", 
                "-i", "gencode_index", 
                "-l", "A", 
                "-1", file_path_1, 
                "-2", file_path_2, 
                "-o", output_path
            ]
        else:
            raise ValueError("Unexpected: > 2 FASTQ files for sample detected, sample:", sample_name)

        try:
            # Execute command
            result = subprocess.run(command, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            print(f"Error quantifying files: {e}")
            print("Sample:", sample_name)

        # clean up the FASTQ files so we save space
        if file_path_1 is not None:
            delete_file(file_path_1)

        if file_path_2 is not None:
            delete_file(file_path_2)

    # combine all quant.sf files into one file and output it
    print("Combining TPMs into single file...")
    dfs = []
    sample_directories = list_subfolders("./" + project_id)
    for sample_directory in sample_directories:
        sample_id = sample_directory.split("/")
        sample_id = sample_id[len(sample_id)-1]

        try:
            # load the sample counts
            df = pd.read_csv(sample_directory + "/quant.sf", sep = "\t")

            # rename TPM to the sample name
            #df[sample_id] = df['TPM']

            # (Custom Code - convert to GEO accession)
            geo_code = None
            for sample_data in project_data:
                if sample_id == sample_data['run_accession']:
                    geo_code = sample_data['sample_alias']
    
            df[geo_code] = df['TPM']


            # remove columns
            df = df.drop(columns=['Length', 'EffectiveLength', 'NumReads', 'TPM'])

            # combine dataframes
            dfs.append(df)

        except Exception as e:
            print("Could not load sample quantification data for sample:", sample_id)

    # Merge DataFrames iteratively on 'Name'
    result = dfs[0]
    for df in dfs[1:]:
        result = pd.merge(result, df, on='Name', how='outer')

    # Save the file
    result.to_csv(project_id + "_TPMs.csv")




