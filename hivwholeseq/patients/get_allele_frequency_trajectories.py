#!/usr/bin/env python
# vim: fdm=indent
'''
author:     Fabio Zanini
date:       01/11/13
content:    Collect the allele frequencies of all samples to the initial
            consensus by collecting from matrices of single patient samples.
'''
# Modules
import os
import argparse
from operator import itemgetter
import numpy as np
from Bio import SeqIO

from hivwholeseq.utils.miseq import alpha
from hivwholeseq.patients.patients import load_patient
from hivwholeseq.patients.one_site_statistics import \
        plot_allele_frequency_trajectories as plot_aft
from hivwholeseq.patients.one_site_statistics import \
        plot_allele_frequency_trajectories_3d as plot_aft_3d



# Script
if __name__ == '__main__':

    # Parse input args
    parser = argparse.ArgumentParser(description='Get allele frequency trajectories',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)    
    parser.add_argument('--patient', required=True,
                        help='Patient to analyze')
    parser.add_argument('--regions', nargs='*',
                        help='Regions to analyze (e.g. F1 genomewide V3)')
    parser.add_argument('--verbose', type=int, default=0,
                        help='Verbosity level [0-4]')
    parser.add_argument('--plot', nargs='?', default=None, const='2D',
                        help='Plot the allele frequency trajectories')
    parser.add_argument('--logit', action='store_true',
                        help='use logit scale (log(x/(1-x)) in the plots')
    parser.add_argument('--threshold', type=float, default=0.9,
                        help='Minimal frequency plotted')
    parser.add_argument('--cov-min', type=float, default=200,
                        help='Minimal coverage (lower sites are masked)')
    parser.add_argument('--depth-min', type=float,
                        help='Minimal depth (lower time points are hidden)')

    args = parser.parse_args()
    pname = args.patient
    regions = args.regions
    VERBOSE = args.verbose
    plot = args.plot
    use_logit = args.logit
    threshold = args.threshold
    cov_min = args.cov_min
    depth_min = args.depth_min

    patient = load_patient(pname)
    patient.discard_nonsequenced_samples()

    if not regions:
        regions = ['F'+str(i) for i in xrange(1, 7)]
    if VERBOSE >= 2:
        print 'regions', regions

    for region in regions:
        if VERBOSE >= 1:
            print region

        (aft, ind) = patient.get_allele_frequency_trajectories(region,
                                                               cov_min=cov_min,
                                                               depth_min=depth_min,
                                                               VERBOSE=VERBOSE)
        times = patient.times[ind]
        ntemplates = patient.n_templates[ind]

        if plot is not None:
            import matplotlib.pyplot as plt

            if plot in ('2D', '2d', ''):
                (fig, ax) = plot_aft(times, aft,
                                     title='Patient '+pname+', '+region,
                                     VERBOSE=VERBOSE,
                                     ntemplates=ntemplates,
                                     logit=use_logit,
                                     threshold=threshold)

            elif plot in ('3D', '3d'):
                (fig, ax) = plot_aft_3d(times, aft,
                                        title='Patient '+pname+', '+region,
                                        VERBOSE=VERBOSE,
                                        logit=use_logit,
                                        ntemplates=ntemplates,
                                        threshold=threshold)

    if plot is not None:
        plt.tight_layout()
        plt.ion()
        plt.show()
