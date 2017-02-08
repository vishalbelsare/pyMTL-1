#!/usr/bin/env python

import numpy as np
from pymtl.interfaces.mtl_bayesian_prior_models import BayesPriorTL
from pymtl.interfaces.mtl_priors import GaussianParams, SKGaussianParams
from sklearn import metrics

__author__ = "Vinay Jayaram, Karl-Heinz Fiebig"
__copyright__ = "Copyright 2017"


class BayesRegression(BayesPriorTL):
    """
    Implements standard L2-loss linear regression with optional prior learning.
    """

    def __init__(self, max_prior_iter=1000, prior_conv_tol=1e-4, lam=1, lam_style='ML'):
        """
        max_prior_iter: see mtl_bayesian_prior_models
        prior_conv_tol: see mtl_bayesian_prior_models
        lam:            see mtl_bayesian_prior_models
        lam_style:      see mtl_bayesian_prior_models
        """
        super(BayesRegression, self).__init__(max_prior_iter, prior_conv_tol, lam, lam_style)
        self._classes = None
        self._prior = None
        self._weights = None

    def fit(self, features, targets):
        """
        Computes standard linear regression solution given current prior. 
        """
        # data safety
        if features.shape[0] != targets.shape[0]:
            raise ValueError('Number of samples in data set ({}) does not match number of \
                             samples ({}) in the target vector'.format(features.shape[0],
                                                                       targets.shape[0]))
        X_train = features

        y_train = targets.reshape(len(targets), 1)

        # Setup prior if not already done
        if self._prior is None:
            self.init_model(X_train.shape, y_train.shape)
        covX = self._prior.Sigma.dot(X_train.T)
        self._weights = np.linalg.lstsq(1.0/self.lam*covX.dot(X_train) + np.eye(X_train.shape[1]),
                                        (1.0/self.lam*covX.dot(y_train)) + self._prior.mu)[0]
        return self


    def predict(self, features):
        """
        Returns predicted values given features
        """
        # TODO arg checks
        if self._weights is None:
            w = self._prior.mu
        else:
            w = self._weights
        pred = features.dot(w)
        return pred

    def score(self, features, targets):
        """
        If classifier, returns accuracy score on given samples and labels. If not, returns loss
        """
        score = self.loss(features, targets)
        return score

    def loss(self, features, targets):
        """
        Specifies squared loss for this particular model
        """
        X = features
        y = targets.reshape(len(targets), 1)
        if self._weights is None:
            w = self._prior.mu
        else:
            w = self._weights
        pred = X.dot(w)
        err = np.sum(np.power(y-pred, 2)) #/ len(y)
        return err

    def init_model(self, dim, dim_targets, init_val=0, norm_style='OAS'):
        """
        Initialize the prior given an initial value
        """
        prior = SKGaussianParams(dim[1], estimator='OAS', init_mean_val=init_val, init_var_val=1)
        self.set_prior(prior)
        self._weights = np.copy(self._prior.mu)

    def get_weights(self):
        """
        TODO
        """
        if self._weights is not None:
            return self._weights
        else:
            return self._prior.mu

    def set_weights(self, weights):
        """
        TODO
        """
        if weights is None:
            self._weights = None
        else:
            self._weights = np.copy(weights)

    def get_prior(self):
        """
        TODO
        """
        return self._prior

    def set_prior(self, prior):
        """
        TODO
        """
        self._prior = prior

class BayesRegressionClassifier(BayesRegression):

    def __init__(self, max_prior_iter=1000, prior_conv_tol=1e-4, lam=1, lam_style='ML'):
        """
        is_classifier:  converts to internal label representation if true
        max_prior_iter: see mtl_bayesian_prior_models
        prior_conv_tol: see mtl_bayesian_prior_models
        lam:            see mtl_bayesian_prior_models
        lam_style:      see mtl_bayesian_prior_models
        TODO: Allow for non {-1,1} internal labelling
        """
        self._set_internal_classes([-1,1])
        super(BayesRegressionClassifier, self).__init__(max_prior_iter, prior_conv_tol, lam, lam_style)


    def fit(self, features, targets):
        """
        Computes standard linear regression solution given current prior. Switches labels
        to allow for classification
        """
        y_train, self._classes = self._convert_classes(targets)
        super(BayesRegressionClassifier, self).fit(features, y_train)
        return self

    def _convert_classes(self, targets):
        # Exract classes and save them as {0, 1} targets
        classes, inv = np.unique(targets, return_inverse=True)
        if len(classes) != 2:
            raise ValueError('Expected exactly two classes for binary classification, but got {}'.format(len(classes)))
        # Convert to {0, 1} targets
        y = inv.reshape(len(inv), 1)
        for ind in range(2):
            y[inv==ind] = self._internal_classes[ind]

        return y, classes

    def _set_internal_classes(self, classes):
        self._internal_classes = classes

    def _recover_classes(self, targets):
        # Cast class labels back to the original classes
        y = np.copy(targets)
        class_inds = []
        for ind in range(2):
            class_inds.append(np.where(targets == self._internal_classes[ind]))
        for ind in range(2):
            y[class_inds[ind]] = ind
        return np.array([self._classes[int(i)] for i in y])

    def loss(self, features, targets):
        """
        Specifies squared loss for this particular model
        """
        y = self._convert_classes(targets)[0]
        return super(BayesRegressionClassifier,self).loss(features, y)

    def predict(self, features):
        """
        Returns predicted values given features
        """
        pred = super(BayesRegressionClassifier,self).predict(features)
        pred = self._recover_classes(np.sign(pred))
        return pred

    def score(self, features, targets):
        """
        If classifier, returns accuracy score on given samples and labels. If not, returns loss
        """
        
        return metrics.accuracy_score(self.predict(features), targets.flatten())
