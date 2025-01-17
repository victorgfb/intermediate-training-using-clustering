# © Copyright IBM Corporation 2022.
#
# LICENSE: Apache License 2.0 (Apache-2.0)
# http://www.apache.org/licenses/LICENSE-2.0
import logging
import html
import os
import re
import urllib.request
import tarfile
import zipfile
import pandas as pd
from sklearn.datasets import fetch_20newsgroups
from sklearn.model_selection import train_test_split

OUT_DIR = './datasets'
RAW_DIR = os.path.join(OUT_DIR, 'raw')
MAX_SIZE = 15000


def split_and_save(df, dataset):
    logging.info(f'splitting {dataset} data into train/dev/test')
    out_dir = os.path.join(OUT_DIR, dataset)
    os.makedirs(out_dir, exist_ok=True)
    # split into train/dev/test by 7:1:2 ratio
    train_dev, test = train_test_split(df, test_size=0.2, random_state=11)
    train, dev = train_test_split(train_dev, test_size=0.125, random_state=11)
    # save csv files
    train.to_csv(os.path.join(out_dir, 'train.csv'), index=False)
    dev.to_csv(os.path.join(out_dir, 'dev.csv'), index=False)
    test.to_csv(os.path.join(out_dir, 'test.csv'), index=False)

def load_ag_news_dbpedia_yahoo():
    def clean_text(x):
        x = re.sub('#\S+;', '&\g<0>', x)
        x = re.sub('(\w+)\\\(\w+)', '\g<1> \g<2>', x)
        x = x.replace('quot;', '&quot;')
        x = x.replace('amp;', '&amp;')
        x = x.replace('\$', '$')
        while x.endswith("\\"):
            x = x[:-1]
        return html.unescape(x)

    dataset_to_columns = {'yahoo_answers': ['label', 'question_title', 'question_content', 'answer']}

    for dataset, column_names in dataset_to_columns.items():
        logging.info(f'processing {dataset} csv files')
        raw_path = os.path.join(RAW_DIR, dataset, f'{dataset}_csv')
        with open(os.path.join(raw_path, 'classes.txt'), 'r') as f:
            idx_to_class_name = dict(enumerate([row.strip() for row in f.readlines()]))

        dataset_out_dir = os.path.join(OUT_DIR, dataset)
        os.makedirs(dataset_out_dir, exist_ok=True)

        for dataset_part in ["train", "test"]:
            part_file = os.path.join(raw_path, f'{dataset_part}.csv')
            part_df = pd.read_csv(part_file, header=None)
            part_df.columns = column_names

            if dataset == 'yahoo_answers':
                part_df = part_df[~part_df['answer'].isna()]
                part_df['text'] = part_df.apply(lambda x:
                                                f"{x['question_title']} {x['question_content']} {x['answer']}", axis=1)

            part_df = part_df[~part_df['text'].isna()]
            part_df['text'] = part_df['text'].apply(lambda x: clean_text(x))
            part_df['label'] = part_df['label'].apply(lambda x: idx_to_class_name[x - 1])
            if dataset_part == 'test':
                part_df.to_csv(os.path.join(dataset_out_dir, f'{dataset_part}.csv'), index=False)
            else:
                # we limit the maximum train to MAX_SIZE
                if len(part_df) > MAX_SIZE/(1-0.125):
                    part_df = part_df.sample(n=int(MAX_SIZE/(1-0.125)), random_state=0)
                train, dev = train_test_split(part_df, test_size=0.125, random_state=42)
                train.to_csv(os.path.join(dataset_out_dir, 'train.csv'), index=False)
                dev.to_csv(os.path.join(dataset_out_dir, 'dev.csv'), index=False)

def load_polarity():
    polarity_raw_dir = os.path.join(RAW_DIR, 'polarity', 'rt-polaritydata')
    examples = []
    for label in ['pos', 'neg']:
        with open(os.path.join(polarity_raw_dir, f'rt-polarity.{label}'), 'r', encoding="iso-8859-1") as f:
            examples.extend([{'text': line.rstrip(), 'label': label} for line in f])
    df = pd.DataFrame(examples)

    split_and_save(df, 'polarity')


def load_subjectivity():
    polarity_raw_dir = os.path.join(RAW_DIR, 'subjectivity')
    label_to_filename = {'objective': 'plot.tok.gt9.5000',
                         'subjective': 'quote.tok.gt9.5000'}
    examples = []
    for label, filename in label_to_filename.items():
        with open(os.path.join(polarity_raw_dir, filename), 'r', encoding="iso-8859-1") as f:
            examples.extend([{'text': line.rstrip(), 'label': label} for line in f])
    df = pd.DataFrame(examples)

    split_and_save(df, 'subjectivity')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s')
    dataset_to_download_url = \
        {
            'polarity': 'http://www.cs.cornell.edu/people/pabo/movie-review-data/rt-polaritydata.tar.gz',
            'yahoo_answers': 'https://docs.google.com/uc?export=download&id=0Bz8a_Dbh9Qhbd2JNdDBsQUdocVU&confirm=t',
        }

    for dataset, url in dataset_to_download_url.items():
        out_dir = os.path.join(RAW_DIR, dataset)
        os.makedirs(out_dir, exist_ok=True)
        logging.info(f'downloading {dataset} raw files')
        extension = '.'.join(url.split(os.sep)[-1].split('.')[1:])
        if len(extension) == 0:
            extension = 'tar.gz'
        target_file = os.path.join(out_dir, f'{dataset}.{extension}')
        urllib.request.urlretrieve(url, target_file)
        if extension == 'tar.gz':
            file = tarfile.open(target_file)
            file.extractall(out_dir)
            file.close()
        elif extension == 'zip':
            with zipfile.ZipFile(target_file, 'r') as zip_ref:
                zip_ref.extractall(out_dir)

    load_polarity()
    load_ag_news_dbpedia_yahoo()
