# vim: fdm=indent
'''
author:     Fabio Zanini
date:       12/03/15
content:    Support functions for pandas.
'''
# Modules
from __future__ import absolute_import
import numpy as np
import pandas as pd



# Functions
def add_binned_column(data, name, column, bins=10, clip=False):
    '''Bin the contents of a column and add it as an additional column
    
    Parameters:
       data (pd.DataFrame): dataframe to modify in inplace
       name (str): name of the new column
       column (str): name of the extant column to bin
       bins (int or sequence): bins, if a number takes quantiles of the data
       clip (bool): if True, clips the data within the bins
    '''
    if np.isscalar(bins):
        bins = np.unique(np.array(data.loc[:, column].quantile(q=np.linspace(0, 1, bins + 1))))
    data[name] = pd.cut(data.loc[:, column], bins=bins, include_lowest=True, labels=False)
    if clip:
        data[name] = data[name].clip(0, len(bins) - 2)

    binsc = 0.5 * (bins[1:] + bins[:-1])
    return bins, binsc
