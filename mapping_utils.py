# vim: fdm=indent
'''
author:     Fabio Zanini
date:       22/08/13
content:    Settings of stampy used by our mapping scripts.
'''
# Globals
stampy_bin = '/ebio/ag-neher/share/programs/bundles/stampy-1.0.22/stampy.py'
subsrate = '0.05'



# Functions
def get_ind_good_cigars(cigar, match_len_min=30):
    '''Keep only CIGAR blocks between two long matches'''
    from numpy import array

    criterion = lambda x: (x[0] == 0) and (x[1] >= match_len_min)
    good_cigars = array(map(criterion, cigar), bool, ndmin=1)

    # If there are 2+ good CIGARs, keep also stuff in between
    if (good_cigars).sum() >= 2:
        tmp = good_cigars.nonzero()[0]
        first_good_cigar = tmp[0]
        last_good_cigar = tmp[-1]
        good_cigars[first_good_cigar: last_good_cigar + 1] = True

    return good_cigars


def get_trims_from_good_cigars(good_cigars, trim_left=3, trim_right=3):
    '''Set the trimming of cigars'''
    from numpy import zeros

    trims_left_right = zeros((len(good_cigars), 2), int)

    if good_cigars.any():
        tmp = good_cigars.nonzero()[0] 
        first_good_cigar = tmp[0]
        last_good_cigar = tmp[-1]
        if first_good_cigar != 0:
            trims_left_right[first_good_cigar, 0] = trim_left
        if last_good_cigar != len(good_cigars) - 1:
            trims_left_right[last_good_cigar, 1] = trim_right

    return trims_left_right


def convert_sam_to_bam(bamfilename, samfilename=None):
    '''Convert SAM file to BAM file format'''
    import pysam
    if samfilename is None:
        samfilename = bamfilename[:-3]+'sam'

    samfile = pysam.Samfile(samfilename, 'r')
    bamfile = pysam.Samfile(bamfilename, 'wb', template=samfile)
    for s in samfile: bamfile.write(s)
    samfile.close()
    bamfile.close()


def get_fragment_list(data_folder, adaID):
    '''Get the sorted list of fragments as of the BAM file'''
    import pysam
    from mapping.filenames import get_last_mapped
    bamfilename = get_last_mapped(data_folder, adaID)
    bamfile = pysam.Samfile(bamfilename, 'rb')
    chromosomes = bamfile.references
    bamfile.close()
    return chromosomes