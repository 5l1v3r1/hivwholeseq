# vim: fdm=indent
'''
author:     Fabio Zanini
date:       04/05/15
content:    Describe substitutions away from and to subtype consensus and
            whether or not they are within CTL epitopes.
'''
# Modules
import os
import sys
import argparse
from itertools import izip
from collections import defaultdict, Counter
import numpy as np
import pandas as pd
from matplotlib import cm
import matplotlib.pyplot as plt
from Bio.Seq import translate

from hivwholeseq.utils.miseq import alpha, alphal
from hivwholeseq.patients.patients import load_patients, iterpatient
from hivwholeseq.utils.sequence import translate_with_gaps
import hivwholeseq.utils.plot
from hivwholeseq.analysis.explore_entropy_patsubtype import (
    get_subtype_reference_alignment, get_ali_entropy)
from hivwholeseq.cross_sectional.get_subtype_entropy import (
    get_subtype_reference_alignment_entropy)
from hivwholeseq.cross_sectional.get_subtype_consensus import (
    get_subtype_reference_alignment_consensus)
from hivwholeseq.patients.one_site_statistics import get_codons_n_polymorphic
from hivwholeseq.analysis.mutation_rate.explore_divergence_synonymous import translate_masked
from hivwholeseq.utils.argparse import PatientsAction


# Globals



# Functions
def collect_data(pnames, region='genomewide', VERBOSE=0, ctl_kind='mhci=80'):
    '''Collect data for sweep call'''
    data = []
    data_ctl = []
    patients = load_patients()
    if pnames is not None:
        patients = patients.loc[pnames]
    patients = patients.loc[-patients.code.isin(['p4'])]

    if VERBOSE >= 1:
        print region

    if VERBOSE >= 2:
        print 'Get subtype consensus'
    conssub = get_subtype_reference_alignment_consensus(region, VERBOSE=VERBOSE)

    for ipat, (pname, patient) in enumerate(iterpatient(patients)):
        pcode = patient.code
        if VERBOSE >= 2:
            print pname, pcode

        aft, ind = patient.get_allele_frequency_trajectories(region,
                                                             cov_min=100,
                                                             depth_min=10,
                                                             VERBOSE=VERBOSE)
        if len(ind) == 0:
            if VERBOSE >= 2:
                print 'No time points: skip'
            continue

        times = patient.times[ind]

        if VERBOSE >= 2:
            print 'Get CTL epitopes'
        ctl_table = patient.get_ctl_epitopes(kind=ctl_kind)
        ctl_table['pcode'] = patient.code
        data_ctl.append(ctl_table)

        if VERBOSE >= 2:
            print 'Get coordinate map'
        coomap = patient.get_map_coordinates_reference(region, refname=('HXB2', region))

        icons = patient.get_initial_consensus_noinsertions(aft, VERBOSE=VERBOSE,
                                                           return_ind=True)
        consm = alpha[icons]

        # Get the map as a dictionary from patient to subtype
        coomapd = {'pat_to_subtype': dict(coomap[:, ::-1]),
                   'subtype_to_pat': dict(coomap)}

        if VERBOSE >= 2:
            print 'Look for substitutions'
        for posdna in xrange(aft.shape[-1]):
            # Get the position in reference coordinates
            if posdna not in coomapd['pat_to_subtype']:
                continue
            pos_sub = coomapd['pat_to_subtype'][posdna]

            # Get allele frequency trajectory
            aftpos = aft[:, :, posdna].T

            # Get only non-masked time points
            indpost = -aftpos[0].mask
            if indpost.sum() < 2:
                continue
            timespos = times[indpost]
            aftpos = aftpos[:, indpost].T

            anc = consm[posdna]
            ianc = icons[posdna]

            # Ignore indels
            if ianc >= 4:
                continue

            # Check for fixation
            if (aftpos[0, ianc] < 0.95) or (aftpos[-1, ianc] > 0.05):
                continue

            # Check which allele (if any) is fixing
            for inuc, nuc in enumerate(alpha[:4]):
                if nuc == anc:
                    continue
                
                if aftpos[-1, inuc] < 0.95:
                    continue

                # NOTE: OK, it's a substitution

                # Assign a time to the substitution
                ist = (aftpos[:, inuc] > 0.5).nonzero()[0]
                tsubst = 0.5 * (timespos[ist - 1] + timespos[ist])

                nuc = alpha[inuc]
                mut = anc+'->'+nuc

                # Define transition/transversion
                if frozenset(nuc+anc) in (frozenset('CT'), frozenset('AG')):
                    trclass = 'ts'
                else:
                    trclass = 'tv'

                # Check to/away subtype consensus
                conspos_sub = conssub[pos_sub]
                if (anc == conspos_sub):
                    away_conssub = 'away'
                elif (nuc == conspos_sub):
                    away_conssub = 'to'
                else:
                    away_conssub = 'neither'

                # Find whether it is within an epitope
                is_epitope = ((pos_sub >= np.array(ctl_table['start_HXB2'])) &
                              (pos_sub < np.array(ctl_table['end_HXB2']))).any()

                datum = {'pcode': patient.code,
                         'region': region,
                         'pos_patient': posdna,
                         'pos_ref': pos_sub,
                         'mut': mut,
                         'trclass': trclass,
                         'epitope': is_epitope,
                         'awayto': away_conssub,
                         'time': tsubst,
                        }

                data.append(datum)

                # There is only one fixation per site
                break

    data = pd.DataFrame(data)
    data_ctl = pd.concat(data_ctl)
    return {'substitutions': data,
            'ctl': data_ctl,
           }


def correlate_away_to_epitope(data):
    d = data['substitutions']
    M = d.groupby(['epitope', 'awayto']).size().unstack()[['away', 'to']]
    print M
    from scipy.stats import fisher_exact
    print fisher_exact(M)


def correlate_epitope_substitution(data):
    '''Correlate presence of a substitution with epitope'''
    from hivwholeseq.data.primers import primers_coordinates_HXB2_outer
    start_F1 = primers_coordinates_HXB2_outer['F1'][0][1]
    end_F6 = primers_coordinates_HXB2_outer['F6'][1][0]

    dg = []
    for pcode, datum in data['ctl'].groupby('pcode'):
        a = np.arange(start_F1, end_F6)
        b = np.zeros(len(a), bool)
        for _, epi in datum.iterrows():
            b[(a >= epi['start_HXB2']) & (a < epi['end_HXB2'])] = True
        c = np.zeros(len(a), bool)
        datum = data['substitutions']
        datum = datum.loc[datum['pcode'] == pcode]
        c[datum['pos_ref'] - a[0]] = True
        dat = {'pos': a,
               'epitope': b,
               'substitution': c,
               }
        dat = pd.DataFrame(dat)
        dat['pcode'] = pcode
        dg.append(dat)
    dg = pd.concat(dg)

    # Exclude env because it has antibody-related substitutions
    from hivwholeseq.reference import load_custom_reference
    from hivwholeseq.utils.sequence import find_annotation
    ref = load_custom_reference('HXB2', 'gb')
    start_env = find_annotation(ref, 'gp120').location.nofuzzy_start
    end_env = find_annotation(ref, 'gp41').location.nofuzzy_end
    dg = dg.loc[(dg['pos'] < start_env) | (dg['pos'] >= end_env)]

    M = dg.groupby(['epitope', 'substitution']).size().unstack()
    print M
    from scipy.stats import fisher_exact
    print 'Fisher\'s exact P value:', fisher_exact(np.array(M))[1]

    pos_epi = dg.loc[dg['epitope'] == True]['pos'].unique()
    dg2 = dg.loc[dg['pos'].isin(pos_epi)].copy()
    M2 = dg2.groupby(['epitope', 'substitution']).size().unstack()
    print M2
    print 'Fisher\'s exact P value:', fisher_exact(np.array(M2))[1]

    return {'dg': dg,
            'dg2': dg2,
           }


def plot_sweeps(data):
    '''Plot sweeps of all patients'''
    import seaborn as sns

    sns.set_style('darkgrid')
    colormap = cm.jet
    fs = 16

    data_sub = data['substitutions']
    data_ctl = data['ctl']

    fig, ax = plt.subplots(figsize=(6, 3))
    pnames = data_sub['pcode'].unique().tolist()
    Lp = len(pnames)

    # Plot the substitutions
    for pname, datum in data_sub.groupby('pcode'):
        x = np.array(datum['pos_ref'])
        y = np.repeat(pnames.index(pname), len(x))

        # Divide by epitope/nonepitope
        for ind, marker, s in [(datum['epitope'], 'o', 50),
                               (-datum['epitope'], 'x', 30)]:
            ind = np.array(ind)

            ax.scatter(x[ind], y[ind], s=s,
                       marker=marker,
                       color=colormap(1.0 * pnames.index(pname) / Lp),
                       label=pname,
                      )

    # Plot CTL epitopes
    for pname, datum in data_ctl.groupby('pcode'):
        y = pnames.index(pname) + 0.2
        for _, datump in datum.iterrows():
            x_left = datump['start_HXB2']
            x_right = datump['end_HXB2']
            width = x_right - x_left
            ax.plot([x_left, x_right], [y] * 2,
                    color=colormap(1.0 * pnames.index(pname) / Lp),
                    lw=3,
                   )


    ax.set_xlim(-50, data_sub['pos_ref'].max() + 200)
    ax.set_ylim(Lp - 0.5, -0.5)
    ax.set_xlabel('Position in HXB2', fontsize=fs)
    ax.set_yticks(np.arange(Lp))
    ax.set_yticklabels(pnames, fontsize=fs)
    ax.xaxis.set_tick_params(labelsize=fs)
    ax.grid(True)

    plt.tight_layout()




# Script
if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description='Study accumulation of minor alleles for different kinds of mutations',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)    
    parser.add_argument('--patients', action=PatientsAction,
                        help='Patient to analyze')
    parser.add_argument('--region', default='genomewide',
                        help='Region to analyze (e.g. F1 p17)')
    parser.add_argument('--ctl-kind', default='mhci=80',
                        help='Kind of CTL data to use')
    parser.add_argument('--verbose', type=int, default=2,
                        help='Verbosity level [0-4]')
    parser.add_argument('--plot', nargs='?', default=None, const='2D',
                        help='Plot results')

    args = parser.parse_args()
    pnames = args.patients
    region = args.region
    ctl_kind = args.ctl_kind
    VERBOSE = args.verbose
    plot = args.plot

    data = collect_data(pnames, region, VERBOSE=VERBOSE, ctl_kind=ctl_kind)

    correlate_away_to_epitope(data)

    correlate_epitope_substitution(data)


    if plot:
        plot_sweeps(data)

        plt.ion()
        plt.show()

