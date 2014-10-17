# vim: fdm=marker
'''
author:     Fabio Zanini
date:       19/05/14
content:    Calculate and plot the propagator of allele frequencies.
'''
# Modules
import os
import sys
import argparse
from operator import itemgetter
import numpy as np
from matplotlib import cm
import matplotlib.pyplot as plt

from hivwholeseq.patients.patients import load_patients, filter_patients_n_times, Patient
from hivwholeseq.patients.filenames import get_initial_reference_filename
from hivwholeseq.patients.one_site_statistics import get_allele_count_trajectories



# Classes
class Propagator(object):

    def __init__(self, n_binsx, n_binsy=None, binsy=None, use_logit=False):
        '''Prepare bins, the histogram, and other data structures'''
        if (binsy is None) and (n_binsy is None):
            n_binsy = n_binsx

        if not use_logit:
            binsx = np.logspace(np.log10(0.002), np.log10(0.998), n_binsx)
            binsxc = np.sqrt(binsx[1:] * binsx[:-1])

            # The final frequencies include 0 and 1
            if binsy is None:
                binsy = np.logspace(np.log10(0.002), np.log10(0.998), n_binsy)
                binsy = np.concatenate([[0], binsy, [1]])
                binsyc = np.concatenate([[0], np.sqrt(binsy[2:-1] * binsy[1:-2]), [1]])
            else:
                # FIXME: The center of the bin is the arithmetic mean, for now
                binsy = np.asarray(binsy)
                binsyc = np.concatenate([[0], 0.5 * (binsy[2:-1] + binsy[1:-2]), [1]])
        else:
            self.trfun = trfun = lambda x: np.log10(x / (1 - x))
            self.trfuni = trfuni = lambda y: 1.0 / (1 + 10**(-y))

            binsx = trfun(np.linspace(trfuni(2e-3), trfuni(1.0 - 2e-3), n_binsx))
            binsxc = trfun(0.5 * (trfuni(binsx)[1:] + trfuni(binsx)[:-1]))

            # The final frequencies include 0 and 1
            if binsy is None:
                binsy = trfun(np.linspace(trfuni(2e-3), trfuni(1.0 - 2e-3), n_binsy))
                binsy = np.concatenate([[0], binsy, [1]])
                binsyc = np.concatenate([[0],
                            trfun(0.5 * (trfuni(binsy)[2:-1] + trfuni(binsy)[1:-2])),
                                         [1]])
            else:
                # FIXME: The center of the bin is the arithmetic mean, for now
                binsy = np.asarray(binsy)
                binsyc = np.concatenate([[0], 0.5 * (binsy[2:-1] + binsy[1:-2]), [1]])

        binsxw = binsx[1:] - binsx[:-1]
        binsyw = binsy[1:] - binsy[:-1]

        self.binsx = binsx
        self.binsy = binsy
        self.binsxc = binsxc
        self.binsyc = binsyc
        self.binsxw = binsxw
        self.binsyw = binsyw

        self.use_logit = use_logit

        self.histogram = np.zeros((len(binsx) - 1, len(binsy) - 1), float)


    def plot(self, figaxs=None, title='', heatmap=True):
        '''Plot the propagator'''
        import matplotlib.pyplot as plt

        plt.ioff()

        if figaxs is None:
            if heatmap:
                fig, axs = plt.subplots(1, 2, figsize=(16, 8))
            else:
                fig, axs = plt.subplots(1, 1, figsize=(12, 8))
                axs = [axs]

        else:
            (fig, axs) = figaxs
            if not heatmap:
                axs = [axs]

        # Normalize histogram
        z = self.histogram
        z = (1.0 * z.T / z.sum(axis=1)).T
        z /=  self.binsyw

        # Plot with lines
        ax = axs[0]
        for iz, zi in enumerate(z):
            xi = self.binsxc[iz]

            # Do not take the first and last final frequency bins, they include the
            # extremes (loss and fixation) and behave specially
            xf = self.binsyc[1:-1]
            y = zi[1:-1]
            xf0 = 1.2e-3
            xf1 = 1.0 - 1.2e-3

            if use_logit:
                (xf, xf0, xf1) = map(self.trfun, (xf, xf0, xf1))
                xi = self.trfun(xi)

            ax.plot(xf, y, lw=2, c=cm.jet(1.0 * iz / z.shape[0]),
                    label='$x_i = '+'{:1.1e}'.format(xi)+'$')
            ax.scatter(xf0, zi[0], s=80, facecolor='none', lw=2,
                       edgecolor=cm.jet(1.0 * iz / z.shape[0]))
            ax.scatter(xf1, zi[-1], s=80, facecolor='none', lw=2,
                       edgecolor=cm.jet(1.0 * iz / z.shape[0]))
            ax.axvline(xi, color=cm.jet(1.0 * iz / z.shape[0]), lw=0.5,
                       alpha=0.5, ls='-')

        if use_logit:
            ax.set_xlim(*map(self.trfun, (1e-3, 1 - 1e-3)))
            tickloc = np.array([0.001, 0.01, 0.1, 0.5, 0.9, 0.99, 0.999])
            ax.set_xticks(self.trfun(tickloc))
            ax.set_xticklabels(map(str, tickloc))
            from matplotlib.ticker import FixedLocator
            ticklocminor = np.concatenate([[10**po * x for x in xrange(2 , 10)]
                                           for po in xrange(-4, -1)] + \
                                          [[0.1 * x for x in xrange(2 , 9)]] + \
                                          [[1 - 10**po * (10 - x) for x in xrange(2, 10)]
                                           for po in xrange(-2, -5, -1)])
            ax.xaxis.set_minor_locator(FixedLocator(self.trfun(ticklocminor)))

        else:
            ax.set_xscale('log')
            ax.set_xlim(1e-3, 1.5)
        
        ax.grid(True)
        ax.set_ylabel('P(x1 | x0)')
        ax.set_xlabel('Final frequency')
        ax.set_yscale('log')
        #ax.legend(loc=3, fontsize=10, title='Initial frequency:', ncol=2)

        # Plot with heatmap
        if heatmap:
            ax = axs[1]

            # Do not take the first and last final frequency bins, they include the
            # extremes (loss and fixation) and behave specially
            z1 = np.log10(z[:, 1:-1])

            im = ax.imshow(z1.T, interpolation='nearest')
            ax.set_xlabel('Initial freq')
            ax.set_ylabel('Final freq')
            ax.set_xticks(np.arange(len(self.binsx)) - 0.5)
            ax.set_xticklabels(map('{:1.2e}'.format, self.binsx),
                               rotation=45, fontsize=10)
            ax.set_yticks(np.arange(len(self.binsy) - 2) - 0.5)
            ax.set_yticklabels(map('{:1.2e}'.format, self.binsy[1:-1]),
                               rotation=45, fontsize=10)

            # Reverse the y axis (by default image y coordinates are top to bottom)
            ax.set_ylim(*(ax.get_ylim()[::-1]))

            cb = plt.colorbar(im)
            cb.set_label('log10 P(x1 | x0)', labelpad=30, rotation=270, fontsize=12)

        if title:
            if heatmap:
                fig.suptitle(title, fontsize=16)
            else:
                axs[0].set_title(title, fontsize=16)
        plt.tight_layout(rect=(0, 0, 1, 0.94))


def plot_propagator_BSC(xis, t, xlim=[0.03, 0.93], ax=None, logit=False):
    '''Make and plot BSC propagators for some initial frequencies'''
    from itertools import izip
    from hivwholeseq.theory.propagators import propagator_BSC

    # Make the propagators
    xis = pp.binsxc
    xfs = []
    rhos = []
    for i, xi in enumerate(xis): 
        (xf, rho) = propagator_BSC(xi, t)
        xfs.append(xf)
        rhos.append(rho)

    # Plot
    if ax is None:
        ax_was_none = True
        fig, ax = plt.subplots(figsize=(12, 8))
    else:
        ax_was_none = False

    if logit:
        trfun = trfun = lambda x: np.log10(x / (1 - x))
        trfuni = trfuni = lambda y: 1.0 / (1 + 10**(-y))

    for i, (xi, xf, rho) in enumerate(izip(xis, xfs, rhos)):
        ind_out1 = (xf < xlim[0])
        ind_in = (xf >= xlim[0]) & (xf <= xlim[1])
        ind_out2 = (xf > xlim[1])
        if logit:
            xf = trfun(xf)
        ax.plot(xf[ind_in], rho[ind_in],
                color=cm.jet(1.0 * i / len(xis)),
                lw=2,
                label='$x_i = '+'{:1.1f}'.format(xi)+'$')
        ax.plot(xf[ind_out1], rho[ind_out1],
                color=cm.jet(1.0 * i / len(xis)),
                lw=2, ls='--', alpha=0.6)
        ax.plot(xf[ind_out2], rho[ind_out2],
                color=cm.jet(1.0 * i / len(xis)),
                lw=2, ls='--', alpha=0.6)

    if ax_was_none:
        ax.set_xlabel('Final frequency')

        if logit:
            ax.set_xlim(-3.1, 3.1)
            tickloc = np.array([0.001, 0.01, 0.1, 0.5, 0.9, 0.99, 0.999])
            ax.set_xticks(trfun(tickloc))
            ax.set_xticklabels(map(str, tickloc))
            from matplotlib.ticker import FixedLocator
            ticklocminor = np.concatenate([[10**po * x for x in xrange(2 , 10)]
                                           for po in xrange(-4, -1)] + \
                                          [[0.1 * x for x in xrange(2 , 9)]] + \
                                          [[1 - 10**po * (10 - x) for x in xrange(2, 10)]
                                           for po in xrange(-2, -5, -1)])
            ax.xaxis.set_minor_locator(FixedLocator(trfun(ticklocminor)))
        else:
            ax.set_xscale('log')

        ax.set_yscale('log')
        ax.set_ylabel('P(x1 | x0)')
        ax.set_title('BSC propagator, t = '+'{:1.1e}'.format(t))
        ax.grid(True)



# Script
if __name__ == '__main__': 

    # Parse input args
    parser = argparse.ArgumentParser(description='Propagator for allele frequencies',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)    
    parser.add_argument('--patients', nargs='+',
                        help='Patients to analyze')
    parser.add_argument('--fragments', nargs='*',
                        help='Fragments to analyze (e.g. F1 F6)')
    parser.add_argument('--verbose', type=int, default=0,
                        help='Verbosity level [0-4]')
    parser.add_argument('--save', action='store_true',
                        help='Save the propagator to file')
    parser.add_argument('--plot', nargs='?', default=None, const='2D',
                        help='Plot the propagator')
    parser.add_argument('--deltat', type=int, nargs=2, default=[100, 300],
                        help='Time in days between final and initial (range)')
    parser.add_argument('--logit', action='store_true',
                        help='use logit scale (log(x/(1-x)) in the plots')
    parser.add_argument('--min-depth', type=int, default=100, dest='min_depth',
                        help='Minimal depth to consider the site')


    args = parser.parse_args()
    pnames = args.patients
    fragments = args.fragments
    VERBOSE = args.verbose
    save_to_file = args.save
    plot = args.plot
    dt = args.deltat
    use_logit = args.logit
    depth_min = args.min_depth

    patients = load_patients()
    if pnames is not None:
        patients = patients.loc[pnames]

    # Prepare output structures
    n_bins = 14
    binsy = [0.,
             0.002,
             0.005, 0.009, 0.013, 0.025,
             0.04136464,  0.08089993,  0.12077255,
             0.16115779,  0.2022444 ,  0.24424043,  0.28738044,  0.33193475,
             0.37822187,  0.42662549,  0.4776187 ,  0.53179937,  0.58994409,
             0.65309361,  0.72269518,  0.80085467,  0.89081905,
             0.95, 0.975, 0.987, 0.991, 0.994,
             0.998,
             1.]
    pp = Propagator(n_bins, binsy=binsy, use_logit=use_logit)

    binsd = np.array([-0.5, -0.4, -0.3, -0.2, -0.1, -0.05, -0.02, -0.01, -0.003,
                      0.003, 0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5])
    binsdc = 0.5 * (binsd[1:] + binsd[:-1])
    binsdw = binsd[1:] - binsd[:-1]

    histr = pp.histogram
    histd = np.zeros((len(pp.binsx) - 1, len(binsd) - 1), float)

    for pname, patient in patients.iterrows():
        patient = Patient(patient)
        samplenames = patient.samples.index

        # If the script is called with no fragment, iterate over all
        if not fragments:
            fragments = ['F'+str(i) for i in xrange(1, 7)]
        if VERBOSE >= 2:
            print 'fragments', fragments
    
        # Iterate over samples and fragments
        for fragment in fragments:
            if VERBOSE >= 1:
                print pname, fragment
    
            aft, ind = patient.get_allele_frequency_trajectories(fragment,
                                                                 cov_min=depth_min)

            n_templates = np.array(patient.n_templates[ind])
            indd = n_templates >= depth_min
            aft = aft[indd]
            ind = ind[indd]
            n_templates = n_templates[indd]

            ts = patient.times[ind]
    
            # Collect counts
            for i in xrange(aft.shape[0] - 1):
                for j in xrange(i + 1, aft.shape[0]):
                    dij = j - i
                    if ((ts[j] - ts[i]) > dt[1]) or ((ts[j] - ts[i]) < dt[0]):
                        continue

                    histr += np.histogram2d(aft[i].ravel(),
                                            aft[j].ravel(),
                                            bins=[pp.binsx, pp.binsy])[0]

                    histd += np.histogram2d(aft[i].ravel(),
                                            aft[j].ravel() - aft[i].ravel(),
                                            bins=[pp.binsx, binsd])[0]

    if plot:
        title = 'Propagator for allele frequencies\n'+\
                '$\Delta t = '+str(dt)+'$ days, '+str(fragments)
        pp.plot(title=title, heatmap=False)

        # BSC propagators
        t = 1.0 * np.mean(dt) / 500
        xis = pp.binsxc
        plot_propagator_BSC(xis, t, logit=use_logit, xlim=[pp.binsyc[0], pp.binsyc[-1]])
        
        plt.ion()
        plt.show()

        sys.exit()

        ## Plot difference
        #fig, axs = plt.subplots(1, 2, figsize=(16, 8))
        #z = histd
        #z = 1.0 * (z.T / z.sum(axis=1)).T
        #z /= binsdw

        #ax = axs[0]
        #for iz, zi in enumerate(z):
        #    xi = binsxc[iz]
        #    dx = binsdc[1:-1]
        #    y = zi[1:-1]

        #    ax.plot(dx, y, lw=2, c=cm.jet(1.0 * iz / z.shape[0]),
        #            label='$x_i = '+'{:1.1e}'.format(xi)+'$')

        #ax.set_ylabel('P(x1 - x0 | x0)')
        #ax.set_xlabel('x1 - x0')
        #ax.set_yscale('log')
        #ax.legend(loc=1, fontsize=10, title='Initial\nfrequency:', ncol=2)

        #ax = axs[1]
        #z1 = np.log10(z)
        #z1 = np.maximum(z1, z1[z1 != (-np.inf)].min() - 1)
        #im = ax.imshow(z1.T, interpolation='nearest', aspect='auto')
        #ax.set_xlabel('Initial freq')
        #ax.set_ylabel('Freq diff')
        #ax.set_xticks(np.arange(len(binsx)) - 0.5)
        #ax.set_xticklabels(map('{:1.1e}'.format, binsx),
        #                   rotation=45, fontsize=10)
        #ax.set_yticks(np.arange(len(binsd)) - 0.5)
        #ax.set_yticklabels(map('{:1.2e}'.format, binsd),
        #                   rotation=45, fontsize=10)
        #ax.set_ylim(*(ax.get_ylim()[::-1]))
        #cb = plt.colorbar(im)
        #cb.set_label('log10 P(x1 - x0 | x0)', labelpad=30, rotation=270, fontsize=12)

        #fig.suptitle('Propagator for allele frequencies\n'+\
        #             '$\Delta t = '+str(dt)+'$, '+str(fragments),
        #             fontsize=16)
        #plt.tight_layout(rect=(0, 0, 1, 0.94))

        ## Plot normalized (Kosheleva et Desai 2013)
        ## rho(x_k | x_k-1) = x_k-1 (1 - x_k-1) / (q * dx^2) -- q = 8 in HIV
        #fig, ax = plt.subplots(1)
        #z = histr
        #z = (1.0 * z.T / z.sum(axis=1)).T
        #z /=  binsyw

        #for iz, zi in enumerate(z):
        #    xi = binsxc[iz]
        #    xf = binsyc[1:-1]
        #    y = zi[1:-1] / (xi * (1 - xi)) * ((xf - xi)**2)

        #    if use_logit:
        #        (xf, xf0, xf1) = map(trfun, (xf, xf0, xf1))

        #    ax.plot(xf, y, lw=2, c=cm.jet(1.0 * iz / z.shape[0]),
        #            label='$x_i = '+'{:1.1e}'.format(xi)+'$')

        #if use_logit:
        #    ax.set_xlim(*map(trfun, (2e-3, 1 - 2e-3)))
        #else:
        #    ax.set_xscale('log')
        #    ax.set_xlim(1e-3, 1.5)

        #ax.set_ylabel('P(x1 | x0) / (x0 * (1 - x0)) * dx^2')
        #ax.set_xlabel('Final frequency')
        #ax.set_yscale('log')
        #ax.legend(loc=3, fontsize=10, title='Initial\nfrequency:', ncol=2)

        #ax.set_title('Propagator (normalized )for allele frequencies\n'+\
        #             '$\Delta t = '+str(dt)+'$, '+str(fragments),
        #             fontsize=16)
        #plt.tight_layout()


        #plt.ion()
        #plt.show()
