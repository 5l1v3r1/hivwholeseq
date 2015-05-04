# vim: fdm=indent
'''
author:     Fabio Zanini
date:       24/03/15
content:    Make three panels with allele frequencies in a short genomic region.
'''
# Modules
import os
import numpy as np

from hivwholeseq.utils.generic import mkdirs
from hivwholeseq.patients.patients import load_patient
from hivwholeseq.paper_figures.filenames import get_figure_folder
from hivwholeseq.paper_figures.plots import plot_allele_freq_example



# Functions
def compress_data(aft, times, pcode, region):
    '''Compress data for plots, discarding useless info'''
    data = []
    datum = {'aft': aft,
             'times': times,
             'pcode': pcode,
             'region': region}
    data.append(datum)

    return data


def store_data(data, fn):
    '''Store data to file for the plots'''
    import cPickle as pickle
    with open(fn, 'wb') as f:
        pickle.dump(data, f, protocol=-1)


def load_data(fn):
    '''Load the data for the plots'''
    import cPickle as pickle
    with open(fn, 'rb') as f:
        return pickle.load(f)



# Script
if __name__ == '__main__':

    VERBOSE = 2

    username = os.path.split(os.getenv('HOME'))[-1]
    foldername = get_figure_folder(username, 'first')
    fn_data = foldername+'data/'
    mkdirs(fn_data)
    fn_data = fn_data + 'allele_freqs_panels.pickle'

    if not os.path.isfile(fn_data):
        pcode = 'p3'
        region = 'p17'
        cutoff = 0.01

        patient = load_patient(pcode)

        aft, ind = patient.get_allele_frequency_trajectories(region,
                                                             depth_min=cutoff)
        times = patient.times[ind]

        data = compress_data(aft, times, pcode, region)
        store_data(data, fn_data)
    else:
        data = load_data(fn_data)
        
    pcode = data[0]['pcode']
    region = data[0]['region']
    filename = foldername+'_'.join(['allele_freq_example', pcode, region])
    for ext in ['png', 'pdf', 'svg']:
        plot_allele_freq_example(data,
                                    VERBOSE=VERBOSE,
                                    savefig=filename+'.'+ext)

    plot_allele_freq_example(data,
                             VERBOSE=VERBOSE)