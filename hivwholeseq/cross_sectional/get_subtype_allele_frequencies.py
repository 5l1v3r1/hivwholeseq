# vim: fdm=indent
'''
author:     Fabio Zanini
date:       04/02/15
content:    Calculate the allele frequencies in a reference alignment of a subtype,
            to load them faster for single-site analyses.
'''
# Modules
import os
import argparse
import numpy as np

from hivwholeseq.utils.sequence import alpha, alphaa
from hivwholeseq.cross_sectional.filenames import (
    get_subtype_reference_alignment_filename,
    get_subtype_reference_alignment_allele_frequencies_filename)
from hivwholeseq.cross_sectional.get_subtype_reference_alignment import get_subtype_reference_alignment



# Functions
def get_ali_allele_frequencies(ali, positions=None, alpha=alpha, VERBOSE=0):
    '''Get allele frequencies of alignment at some positions
    
    Parameters:
       - alpha: alphabet for the sequences, defaults to ACGT-N.
    '''
    if positions is None:
        positions = np.arange(len(ali[0]))

    afs = np.zeros((len(alpha), len(positions)))
    for i, pos in enumerate(positions):
        af = np.zeros(len(alpha))
        col = np.fromstring(ali[:, pos], 'S1')
        for ia, nuc in enumerate(alpha):
            af[ia] = (col == nuc).sum()
        af /= af.sum()
        afs[:, i] = af

    return afs


def get_subtype_reference_alignment_allele_frequencies(region, subtype='B', VERBOSE=0,
                                                       refname='HXB2',
                                                       type='nuc'):
    '''Get the entropy of a large subtype reference alignment'''
    import numpy as np

    fn = get_subtype_reference_alignment_allele_frequencies_filename(region,
                                                                     subtype=subtype,
                                                                     refname=refname,
                                                                     type=type,
                                                                     VERBOSE=VERBOSE)

    return np.load(fn)



# Script
if __name__ == '__main__':

    # Parse input args
    parser = argparse.ArgumentParser(
        description='Calculate allele frequencies of subtype alignment',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)    
    parser.add_argument('--regions', nargs='+', required=True,
                        help='Regions to analyze (e.g. F1 p17)')
    parser.add_argument('--verbose', type=int, default=0,
                        help='Verbosity level [0-4]')
    parser.add_argument('--subtype', default='B',
                        help='Subtype of the alignment')
    parser.add_argument('--reference', default='HXB2',
                        help='Reference of the alignment')
    parser.add_argument('--type', default='nuc',
                        help='nuc/aa nucleic or amino acid seqs')
    parser.add_argument('--save', action='store_true',
                        help='Save to file')

    args = parser.parse_args()
    regions = args.regions
    VERBOSE = args.verbose
    subtype = args.subtype
    refname = args.reference
    alitype = args.type
    use_save = args.save


    afss = {}
    for region in regions:
        if VERBOSE >= 1:
            print region

        if use_save:

            if VERBOSE >= 2:
                print 'Get alignment'
            ali = get_subtype_reference_alignment(region, subtype=subtype,
                                                  refname=refname,
                                                  type=alitype,
                                                  VERBOSE=VERBOSE)

            if VERBOSE >= 2:
                print 'Compute allele frequencies'
            if alitype == 'nuc':
                alphabet = alpha
            else:
                alphabet = alphaa

            afs = get_ali_allele_frequencies(ali, alpha=alphabet, VERBOSE=VERBOSE)

            if VERBOSE >= 2:
                print 'Store to file'
            fn_out = get_subtype_reference_alignment_allele_frequencies_filename(region,
                                                                      subtype=subtype,
                                                                      refname=refname,
                                                                      type=alitype,
                                                                      VERBOSE=VERBOSE)
            afs.dump(fn_out)

        else:
            if VERBOSE >= 2:
                print 'Get entropy from file'
            afs = get_subtype_reference_alignment_allele_frequencies(region,
                                                        subtype=subtype,
                                                        refname=refname,
                                                        type=alitype,
                                                        VERBOSE=VERBOSE)

        afss[region] = afs


