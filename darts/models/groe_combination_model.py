"""
GROE combination model
-------------------------
"""

from ..timeseries import TimeSeries
from ..logging import get_logger, raise_log
from ..models.forecasting_model import ForecastingModel
from ..models.combination_model import CombinationModel
from ..metrics import smape
from typing import List, Callable
import numpy as np

from ..utils.cross_validation import generalized_rolling_origin_evaluation as groe

logger = get_logger(__name__)


class GROECombinationModel(CombinationModel):
    def __init__(self, models: List[ForecastingModel], metrics: Callable[[TimeSeries, TimeSeries], float] = smape,
                 n_evaluations: int = 6, **groe_kwargs):
        """
        Implementation of a Combination Model using GROE to compute its weights.

        The weights are a function of the loss function of the GROE cross-validation scheme.
        The weights for each constituent model's output are computed as the inverse of the
        value of the loss function obtained by applying GROE on that model, normalized such
        that all weights add up to 1.

        Disclaimer: This model constitutes an experimental attempt at implementing ensembling using
        generalized rolling window evaluation.

        Parameters
        ----------
        models
            List of forecasting models, whose predictions to combine.
        metrics
            Metrics function used for the GROE cross-validation function.
        n_evaluations
            Number of evaluation performed by the GROE function.
        groe_args
            Any additional args passed to the GROE function
        """
        super(GROECombinationModel, self).__init__(models)
        self.metrics = metrics
        self.n_evaluations = n_evaluations
        self.groe_kwargs = groe_kwargs
        self.criterion = None

    def update_groe_params(self, **groe_kwargs):
        if "n_evaluations" in groe_kwargs:
            self.n_evaluations = groe_kwargs.pop("n_evaluations")
        self.groe_kwargs = groe_kwargs

    def fit(self, train_ts: TimeSeries):
        super().fit(train_ts)
        self.criterion = []
        for model in self.models:
            self.criterion.append(groe(self.train_ts, model, self.metrics,
                                       n_evaluations=self.n_evaluations, **self.groe_kwargs))
        if np.inf in self.criterion:
            raise_log(ValueError("Impossible to evaluate one of the models on this TimeSeries. "
                                 "Choose another fallback method"), logger)
        if 0. in self.criterion:
            self.weights = np.zeros(len(self.criterion))
            self.weights[self.criterion.index(0.)] = 1.
        else:
            score = 1 / np.array(self.criterion)
            self.weights = score / score.sum()

    def combination_function(self):
        return sum(map(lambda ts, weight: ts * weight, self.predictions, self.weights))