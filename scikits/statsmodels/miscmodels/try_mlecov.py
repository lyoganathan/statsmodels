'''Multivariate Normal Model with full covariance matrix


Author: josef-pktd
'''


import numpy as np
#from scipy import special #, stats
from scipy import linalg
from scipy.linalg import norm, toeplitz

import scikits.statsmodels as sm
from scikits.statsmodels.model import GenericLikelihoodModel, LikelihoodModel
from scikits.statsmodels.sandbox.tsa.arima import arma_acovf, ARIMA


def mvn_loglike_sum(x, sigma):
    '''loglike multivariate normal

    copied from GLS and adjusted names
    not sure why this differes from mvn_loglike
    '''
    nobs = len(x)
    nobs2 = nobs / 2.0
    SSR = (x**2).sum()
    llf = -np.log(SSR) * nobs2      # concentrated likelihood
    llf -= (1+np.log(np.pi/nobs2))*nobs2  # with likelihood constant
    if np.any(sigma) and sigma.ndim == 2:
    #FIXME: robust-enough check?  unneeded if _det_sigma gets defined
        llf -= .5*np.log(np.linalg.det(sigma))
    return llf

def mvn_loglike(x, sigma):
    '''loglike multivariate normal

    assumes x is 1d, (nobs,) and sigma is 2d (nobs, nobs)

    brute force from formula
    no checking of correct inputs
    use of inv and log-det should be replace with something more efficient
    '''
    #see numpy thread
    #Sturla: sqmahal = (cx*cho_solve(cho_factor(S),cx.T).T).sum(axis=1)
    sigmainv = linalg.inv(sigma)
    logdetsigma = np.log(np.linalg.det(sigma))
    nobs = len(x)

    llf = - np.dot(x, np.dot(sigmainv, x))
    llf -= nobs * np.log(2 * np.pi)
    llf -= logdetsigma
    llf *= 0.5
    return llf

def invertibleroots(ma):
    import numpy.polynomial as poly
    pr = poly.polyroots(ma)
    insideroots = np.abs(pr)<1
    if insideroots.any():
        pr[np.abs(pr)<1] = 1./pr[np.abs(pr)<1]
        pnew = poly.Polynomial.fromroots(pr)
        mainv = pn.coef/pnew.coef[0]
        wasinvertible = False
    else:
        mainv = ma
        wasinvertible = True
    return mainv, wasinvertible

def getpoly(self, params):
    ar = np.r_[[1], -params[:self.nar]]
    ma = np.r_[[1], params[-self.nma:]]
    import numpy.polynomial as poly
    return poly.Polynomial(ar), poly.Polynomial(ma)

class MLEGLS(GenericLikelihoodModel):
    '''ARMA model with exact loglikelhood for short time series

    Inverts (nobs, nobs) matrix, use only for nobs <= 200 or so.

    This class is a pattern for small sample GLS-like models. Intended use
    for loglikelihood of initial observations for ARMA.



    TODO:
    This might be missing the error variance. Does it assume error is
       distributed N(0,1)
    Maybe extend to mean handling, or assume it is already removed.
    '''


    def _params2cov(self, params, nobs):
        '''get autocovariance matrix from ARMA regression parameter

        ar parameters are assumed to have rhs parameterization

        '''
        ar = np.r_[[1], -params[:self.nar]]
        ma = np.r_[[1], params[-self.nma:]]
        #print 'ar', ar
        #print 'ma', ma
        #print 'nobs', nobs
        autocov = arma_acovf(ar, ma, nobs=nobs)
        #print 'arma_acovf(%r, %r, nobs=%d)' % (ar, ma, nobs)
        #print autocov.shape
        #something is strange  fixed in aram_acovf
        autocov = autocov[:nobs]
        sigma = toeplitz(autocov)
        return sigma

    def loglike(self, params):
        sig = self._params2cov(params[:-1], self.nobs)
        sig = sig * params[-1]**2
        loglik = mvn_loglike(self.endog, sig)
        return loglik

    def fit_invertible(self, *args, **kwds):
        res = self.fit(*args, **kwds)
        ma = np.r_[[1], res.params[self.nar: self.nar+self.nma]]
        mainv, wasinvertible = invertibleroots(ma)
        if not wasinvertible:
            start_params = res.params.copy()
            start_params[self.nar: self.nar+self.nma] = mainv[1:]
            #need to add args kwds
            res = self.fit(start_params=start_params)
        return res



if __name__ == '__main__':
    nobs = 100
    ar = [1.0, -0.5, 0.1]
    ma = [1.0,  0.6,  0.2]
    #ma = [1]
    y = ARIMA.generate_sample(ar,ma,nobs,0.2)
    y -= y.mean() #I haven't checked treatment of mean yet, so remove
    mod = MLEGLS(y)
    mod.nar, mod.nma = 2, 2   #needs to be added, no init method
    mod.nobs = len(y)
    res = mod.fit(start_params=[0.1,0,0.2,0, 0.5])
    print 'DGP', ar, ma
    print res.params
    from scikits.statsmodels.regression import yule_walker
    print yule_walker(y, 2)
    #resi = mod.fit_invertible(start_params=[0.1,0,0.2,0, 0.5])
    #print resi.params

    arpoly, mapoly = getpoly(mod, res.params[:-1])

    data = sm.datasets.sunspots.load()
    #ys = data.endog[-100:]
##    ys = data.endog[12:]-data.endog[:-12]
##    ys -= ys.mean()
##    mods = MLEGLS(ys)
##    mods.nar, mods.nma = 13, 1   #needs to be added, no init method
##    mods.nobs = len(ys)
##    ress = mods.fit(start_params=np.r_[0.4, np.zeros(12), [0.2, 5.]],maxiter=200)
##    print ress.params
##    #from scikits.statsmodels.sandbox.tsa import arima as tsaa
##    #tsaa
##    import matplotlib.pyplot as plt
##    plt.plot(data.endog[1])
##    #plt.show()



