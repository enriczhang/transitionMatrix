# -*- coding: utf-8 -*-

# (c) 2017-2020 Open Risk, all rights reserved
#
# TransitionMatrix is licensed under the Apache 2.0 license a copy of which is included
# in the source distribution of TransitionMatrix. This is notwithstanding any licenses of
# third-party software included in this distribution. You may not use this file except in
# compliance with the License.
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function
import numpy as np

from transitionMatrix.estimators import BaseEstimator
import statsmodels.stats.proportion as st


class SimpleEstimator(BaseEstimator):

    """
    Class for implementing a simple estimator suitable for single period transitions

    """

    def __init__(self, cohort_intervals=None, states=None, ci=None):
        BaseEstimator.__init__(self)
        # self.cohort_intervals = cohort_intervals
        if states is not None:
            self.states = states
        if ci is not None:
            assert (ci['method'] in ['goodman', 'sison-glaz', 'binomial'])
            self.ci_method = ci['method']
            self.ci_alpha = ci['alpha']

    def fit(self, data):
        '''
        Parameters
        ----------
        data : array-like
            The data to use for the estimation

        Returns
        -------
        matrix : estimated transition matrix
        confint_lower: lower confidence interval
        confint_upper: upper confidence interval

        Notes
        ------
        '''

        # loop over data (id, state_in, state_out)
        # calculate population count N^i_k per state i
        # calculate migrations count N^{ij}_{kl} from i to j
        # calculate transition matrix as ratio T^{ij}_{kl} = N^{ij}_{kl} / N^i_k

        # In the simple estimator all events are part of the same cohort
        state_count = self.states.cardinality
        state_list = self.states.get_states()

        # storage of counts
        tm_count = np.ndarray(state_count)
        tmn_count = np.ndarray((state_count, state_count))
        tm_count.fill(0.0)
        tmn_count.fill(0.0)

        i = 0
        for row in data.itertuples():
            state_in = state_list.index(row[2])
            state_out = state_list.index(row[3])
            # print(row[2], row[3])
            # print(state_in, state_out)
            tm_count[state_in] += 1
            tmn_count[state_in, state_out] += 1
            i += 1

        self.counts = int(tm_count.sum())

        '''Confidence intervals for multinomial proportions. See statsmodels URL
        http://www.statsmodels.org/devel/_modules/statsmodels/stats/proportion.html

        Parameters
        ----------
        counts : array_like of int, 1-D
            Number of observations in each category.
        alpha : float in (0, 1), optional
            Significance level, defaults to 0.05.
        method : {'goodman', 'sison-glaz'}, optional
            Method to use to compute the confidence intervals; available methods
            are:

             - `goodman`: based on a chi-squared approximation, valid if all
               values in `counts` are greater or equal to 5 [2]_
             - `sison-glaz`: less conservative than `goodman`, but only valid if
               `counts` has 7 or more categories (``len(counts) >= 7``) [3]_

        Returns
        -------
        confint : ndarray, 2-D
            Array of [lower, upper] confidence levels for each category, such that
            overall coverage is (approximately) `1-alpha`.
        '''

        confint_lower = np.ndarray((state_count, state_count, 1))
        confint_upper = np.ndarray((state_count, state_count, 1))
        for s1 in range(state_count):
            intervals = st.multinomial_proportions_confint(tmn_count[s1, :], alpha=self.ci_alpha, method=self.ci_method)
            for s2 in range(state_count):
                confint_lower[s1, s2, 0] = intervals[s2][0]
                confint_upper[s1, s2, 0] = intervals[s2][1]
        self.confint_lower = confint_lower
        self.confint_upper = confint_upper

        # Normalization of counts to produce family of probability matrices
        for s1 in range(state_count):
            for s2 in range(state_count):
                if tm_count[s1] > 0:
                    tmn_count[(s1, s2)] = tmn_count[(s1, s2)] / tm_count[s1]

        # for s1 in range(state_count):
        #     for s2 in range(state_count):
        #         print(confint_lower[s1, s2], tmn_count[(s1, s2)], confint_upper[s1, s2])

        self.matrix_set.append(tmn_count)

        return self.matrix_set
